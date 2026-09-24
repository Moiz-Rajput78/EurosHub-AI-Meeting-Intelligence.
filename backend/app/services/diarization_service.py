import logging
import wave
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import numpy as np
import requests
import torch
from pyannote.audio import Pipeline

from app.core.config import settings


logger = logging.getLogger(
    __name__
)


@dataclass
class SpeakerTurn:
    start_time: float
    end_time: float
    speaker_label: str


@dataclass
class DiarizationResult:
    turns: list[SpeakerTurn]
    speaker_labels: list[str]


def _configure_torch_cpu_threads() -> None:
    """
    Configure PyTorch CPU inference for the current machine.

    Pyannote is CPU-heavy on systems without CUDA. Limiting the
    thread pool to a sensible configurable value helps avoid
    excessive thread contention while keeping all CPU cores busy.
    """

    thread_count = max(
        1,
        settings.pyannote_cpu_threads,
    )

    torch.set_num_threads(
        thread_count
    )

    try:
        torch.set_num_interop_threads(
            1
        )
    except RuntimeError:
        # PyTorch allows the inter-op thread count to be set only
        # before parallel work starts. If another library already
        # initialized it, keeping the existing value is safe.
        pass


@lru_cache(maxsize=1)
def get_diarization_pipeline() -> Pipeline:
    """
    Load and cache the configured pyannote diarization pipeline.

    The accurate community-1 model is preserved. CPU execution is
    tuned instead of replacing diarization with a lower-quality
    shortcut.
    """

    if not settings.huggingface_token:
        raise RuntimeError(
            "HUGGINGFACE_TOKEN is not configured."
        )

    pipeline = Pipeline.from_pretrained(
        settings.pyannote_model,
        token=settings.huggingface_token,
    )

    device_name = (
        settings
        .pyannote_device
        .strip()
        .lower()
    )

    if device_name == "cuda":
        if not torch.cuda.is_available():
            raise RuntimeError(
                "PYANNOTE_DEVICE is configured as CUDA, "
                "but CUDA is not available."
            )

        pipeline.to(
            torch.device(
                "cuda"
            )
        )

    else:
        _configure_torch_cpu_threads()

        pipeline.to(
            torch.device(
                "cpu"
            )
        )

    return pipeline


def load_pcm_wav_for_pyannote(
    audio_path: str | Path,
) -> dict[
    str,
    torch.Tensor | int,
]:
    """
    Load normalized PCM WAV audio directly into memory.

    The application already generates 16-bit PCM WAV audio using
    FFmpeg. Passing waveform data directly to pyannote avoids
    TorchCodec's Windows FFmpeg shared-DLL dependency.

    The conversion avoids one unnecessary full-waveform copy,
    which reduces memory traffic for long meetings.
    """

    source = Path(
        audio_path
    ).resolve()

    if not source.exists():
        raise FileNotFoundError(
            "Normalized meeting audio does not exist."
        )

    if not source.is_file():
        raise ValueError(
            "The diarization source is not a valid file."
        )

    if source.stat().st_size == 0:
        raise ValueError(
            "The diarization source is empty."
        )

    try:
        with wave.open(
            str(source),
            "rb",
        ) as wav_file:
            channel_count = (
                wav_file.getnchannels()
            )

            sample_width = (
                wav_file.getsampwidth()
            )

            sample_rate = (
                wav_file.getframerate()
            )

            frame_count = (
                wav_file.getnframes()
            )

            compression_type = (
                wav_file.getcomptype()
            )

            if compression_type != "NONE":
                raise ValueError(
                    "The normalized WAV must "
                    "be uncompressed PCM audio."
                )

            if sample_width != 2:
                raise ValueError(
                    "The normalized WAV must "
                    "use 16-bit PCM samples."
                )

            if channel_count < 1:
                raise ValueError(
                    "The normalized WAV contains "
                    "no audio channels."
                )

            if frame_count <= 0:
                raise ValueError(
                    "The normalized WAV contains "
                    "no audio samples."
                )

            raw_audio = (
                wav_file.readframes(
                    frame_count
                )
            )

    except wave.Error as exc:
        raise ValueError(
            "The normalized audio is not "
            "a valid PCM WAV file."
        ) from exc

    samples = np.frombuffer(
        raw_audio,
        dtype=np.int16,
    )

    if samples.size == 0:
        raise ValueError(
            "The normalized WAV contains "
            "no audio samples."
        )

    if channel_count > 1:
        if (
            samples.size
            % channel_count
            != 0
        ):
            raise ValueError(
                "The WAV channel data "
                "is malformed."
            )

        samples = (
            samples
            .reshape(
                -1,
                channel_count,
            )
            .astype(
                np.float32,
                copy=False,
            )
            .mean(
                axis=1
            )
        )

    else:
        samples = samples.astype(
            np.float32,
            copy=False,
        )

    waveform = (
        samples
        / 32768.0
    )

    waveform_tensor = (
        torch.from_numpy(
            waveform
        )
        .unsqueeze(0)
        .contiguous()
        .float()
    )

    return {
        "waveform": waveform_tensor,
        "sample_rate": sample_rate,
    }


def _diarize_audio_local(
    audio_path: str | Path,
) -> DiarizationResult:
    """
    Run speaker diarization on normalized meeting audio.

    Audio is supplied to pyannote as an in-memory waveform rather
    than a filename, bypassing TorchCodec decoding on Windows.

    torch.inference_mode() disables gradient bookkeeping, which is
    unnecessary for inference and reduces CPU/memory overhead while
    preserving diarization behavior.
    """

    audio_input = (
        load_pcm_wav_for_pyannote(
            audio_path
        )
    )

    pipeline = (
        get_diarization_pipeline()
    )

    try:
        with torch.inference_mode():
            output = pipeline(
                audio_input
            )

    except Exception:
        logger.exception(
            "pyannote diarization pipeline failed."
        )
        raise

    diarization = getattr(
        output,
        "exclusive_speaker_diarization",
        None,
    )

    if diarization is None:
        diarization = getattr(
            output,
            "speaker_diarization",
            None,
        )

    if diarization is None:
        raise RuntimeError(
            "Speaker diarization did not return "
            "a usable diarization result."
        )

    raw_turns: list[
        tuple[
            float,
            float,
            str,
        ]
    ] = []

    detected_labels: list[
        str
    ] = []

    for turn, _, speaker in (
        diarization.itertracks(
            yield_label=True
        )
    ):
        start_time = float(
            turn.start
        )

        end_time = float(
            turn.end
        )

        speaker_value = str(
            speaker
        )

        if end_time <= start_time:
            continue

        raw_turns.append(
            (
                start_time,
                end_time,
                speaker_value,
            )
        )

        if (
            speaker_value
            not in detected_labels
        ):
            detected_labels.append(
                speaker_value
            )

    if not raw_turns:
        raise ValueError(
            "No speakers were detected "
            "in the recording."
        )

    canonical_mapping: dict[
        str,
        str,
    ] = {}

    for index, label in enumerate(
        detected_labels
    ):
        canonical_mapping[
            label
        ] = (
            f"Speaker {index + 1}"
        )

    turns: list[
        SpeakerTurn
    ] = []

    for (
        start_time,
        end_time,
        original_label,
    ) in raw_turns:
        turns.append(
            SpeakerTurn(
                start_time=(
                    start_time
                ),
                end_time=(
                    end_time
                ),
                speaker_label=(
                    canonical_mapping[
                        original_label
                    ]
                ),
            )
        )

    speaker_labels = [
        canonical_mapping[
            label
        ]
        for label in detected_labels
    ]

    return DiarizationResult(
        turns=turns,
        speaker_labels=(
            speaker_labels
        ),
    )



def _validate_deepgram_settings() -> None:
    """
    Validate the settings required for Deepgram cloud diarization.

    The API key itself is never included in logs or exceptions.
    """

    if not settings.deepgram_api_key.strip():
        raise RuntimeError(
            "DEEPGRAM_API_KEY is not configured."
        )

    if not settings.deepgram_api_url.strip():
        raise RuntimeError(
            "DEEPGRAM_API_URL is not configured."
        )

    if not settings.deepgram_model.strip():
        raise RuntimeError(
            "DEEPGRAM_MODEL is not configured."
        )

    if not settings.deepgram_diarize_model.strip():
        raise RuntimeError(
            "DEEPGRAM_DIARIZE_MODEL is not configured."
        )

    if settings.deepgram_timeout_seconds <= 0:
        raise ValueError(
            "DEEPGRAM_TIMEOUT_SECONDS must be greater than 0."
        )


def _canonicalize_deepgram_turns(
    raw_turns: list[
        tuple[
            float,
            float,
            int,
        ]
    ],
) -> DiarizationResult:
    """
    Convert Deepgram's zero-based speaker IDs into the same
    Speaker 1 / Speaker 2 labels used by the existing Pyannote
    implementation.

    Adjacent words from the same speaker are merged into compact
    speaker turns. This keeps downstream transcript-to-speaker
    matching efficient without changing the existing API contract.
    """

    if not raw_turns:
        raise ValueError(
            "Deepgram did not return any speaker-labelled speech."
        )

    ordered = sorted(
        raw_turns,
        key=lambda item: (
            item[0],
            item[1],
        ),
    )

    detected_speakers: list[
        int
    ] = []

    for _, _, speaker in ordered:
        if speaker not in detected_speakers:
            detected_speakers.append(
                speaker
            )

    canonical_mapping = {
        speaker: f"Speaker {index + 1}"
        for index, speaker in enumerate(
            detected_speakers
        )
    }

    merged: list[
        tuple[
            float,
            float,
            int,
        ]
    ] = []

    max_merge_gap = max(
        0.0,
        settings.deepgram_turn_merge_gap_seconds,
    )

    for start_time, end_time, speaker in ordered:
        if end_time <= start_time:
            continue

        if not merged:
            merged.append(
                (
                    start_time,
                    end_time,
                    speaker,
                )
            )
            continue

        (
            previous_start,
            previous_end,
            previous_speaker,
        ) = merged[-1]

        gap = max(
            0.0,
            start_time
            - previous_end,
        )

        if (
            speaker == previous_speaker
            and gap <= max_merge_gap
        ):
            merged[-1] = (
                previous_start,
                max(
                    previous_end,
                    end_time,
                ),
                previous_speaker,
            )
        else:
            merged.append(
                (
                    start_time,
                    end_time,
                    speaker,
                )
            )

    turns = [
        SpeakerTurn(
            start_time=start_time,
            end_time=end_time,
            speaker_label=(
                canonical_mapping[
                    speaker
                ]
            ),
        )
        for (
            start_time,
            end_time,
            speaker,
        ) in merged
    ]

    speaker_labels = [
        canonical_mapping[
            speaker
        ]
        for speaker in detected_speakers
    ]

    if not turns:
        raise ValueError(
            "Deepgram did not return usable speaker turns."
        )

    return DiarizationResult(
        turns=turns,
        speaker_labels=speaker_labels,
    )


def _extract_deepgram_word_turns(
    payload: dict,
) -> list[
    tuple[
        float,
        float,
        int,
    ]
]:
    """
    Extract speaker-labelled word timestamps from a Deepgram
    pre-recorded response.

    Deepgram assigns a zero-based `speaker` value to each word
    when diarization is enabled.
    """

    results = payload.get(
        "results"
    )

    if not isinstance(
        results,
        dict,
    ):
        raise RuntimeError(
            "Deepgram response does not contain results."
        )

    channels = results.get(
        "channels"
    )

    if not isinstance(
        channels,
        list,
    ):
        raise RuntimeError(
            "Deepgram response does not contain channels."
        )

    raw_turns: list[
        tuple[
            float,
            float,
            int,
        ]
    ] = []

    for channel in channels:
        if not isinstance(
            channel,
            dict,
        ):
            continue

        alternatives = (
            channel.get(
                "alternatives"
            )
        )

        if not isinstance(
            alternatives,
            list,
        ):
            continue

        for alternative in alternatives:
            if not isinstance(
                alternative,
                dict,
            ):
                continue

            words = alternative.get(
                "words"
            )

            if not isinstance(
                words,
                list,
            ):
                continue

            for word in words:
                if not isinstance(
                    word,
                    dict,
                ):
                    continue

                start_value = (
                    word.get(
                        "start"
                    )
                )

                end_value = (
                    word.get(
                        "end"
                    )
                )

                speaker_value = (
                    word.get(
                        "speaker"
                    )
                )

                if (
                    start_value is None
                    or end_value is None
                    or speaker_value is None
                ):
                    continue

                try:
                    start_time = float(
                        start_value
                    )

                    end_time = float(
                        end_value
                    )

                    speaker = int(
                        speaker_value
                    )

                except (
                    TypeError,
                    ValueError,
                ):
                    continue

                if end_time <= start_time:
                    continue

                raw_turns.append(
                    (
                        start_time,
                        end_time,
                        speaker,
                    )
                )

    return raw_turns


def _diarize_audio_deepgram(
    audio_path: str | Path,
) -> DiarizationResult:
    """
    Run cloud speaker diarization with Deepgram.

    The normalized WAV is sent directly to Deepgram. We use
    Deepgram's current batch diarization model selector instead
    of the deprecated `diarize=true` parameter.

    When DEEPGRAM_LANGUAGE is blank, language detection is
    enabled. This is appropriate because this request is used
    for speaker timing rather than as the source of the saved
    meeting transcript. Cloudflare remains the transcription
    provider.
    """

    _validate_deepgram_settings()

    source = Path(
        audio_path
    ).resolve()

    if not source.exists():
        raise FileNotFoundError(
            "Normalized meeting audio does not exist."
        )

    if not source.is_file():
        raise ValueError(
            "The diarization source is not a valid file."
        )

    if source.stat().st_size == 0:
        raise ValueError(
            "The diarization source is empty."
        )

    params: dict[
        str,
        str,
    ] = {
        "model": (
            settings
            .deepgram_model
            .strip()
        ),
        "diarize_model": (
            settings
            .deepgram_diarize_model
            .strip()
        ),
        "utterances": "true",
        "punctuate": "false",
        "smart_format": "false",
    }

    configured_language = (
        settings
        .deepgram_language
        .strip()
    )

    if configured_language:
        params[
            "language"
        ] = configured_language
    else:
        params[
            "detect_language"
        ] = "true"

    headers = {
        "Authorization": (
            "Token "
            + settings
            .deepgram_api_key
            .strip()
        ),
        "Content-Type": (
            "audio/wav"
        ),
    }

    try:
        with source.open(
            "rb"
        ) as audio_file:
            response = requests.post(
                settings
                .deepgram_api_url
                .strip(),
                params=params,
                headers=headers,
                data=audio_file,
                timeout=(
                    settings
                    .deepgram_timeout_seconds
                ),
            )

    except requests.RequestException as exc:
        raise RuntimeError(
            "Deepgram diarization request failed."
        ) from exc

    if not response.ok:
        detail = (
            response.text
            .strip()
        )

        if len(detail) > 1000:
            detail = (
                detail[:1000]
                + "..."
            )

        raise RuntimeError(
            "Deepgram diarization returned "
            f"HTTP {response.status_code}. "
            f"{detail}"
        )

    try:
        payload = (
            response.json()
        )

    except ValueError as exc:
        raise RuntimeError(
            "Deepgram returned an invalid JSON response."
        ) from exc

    if not isinstance(
        payload,
        dict,
    ):
        raise RuntimeError(
            "Deepgram returned an unexpected response."
        )

    raw_turns = (
        _extract_deepgram_word_turns(
            payload
        )
    )

    return (
        _canonicalize_deepgram_turns(
            raw_turns
        )
    )


def diarize_audio(
    audio_path: str | Path,
) -> DiarizationResult:
    """
    Run speaker diarization using the configured provider.

    Supported providers:
    - deepgram: cloud diarization
    - local: existing Pyannote implementation

    Deepgram can automatically fall back to Pyannote when
    DIARIZATION_FALLBACK_TO_LOCAL=true.
    """

    provider = (
        settings
        .normalized_diarization_provider
    )

    if provider == "local":
        logger.info(
            "Running local Pyannote speaker diarization."
        )

        return (
            _diarize_audio_local(
                audio_path
            )
        )

    logger.info(
        "Running Deepgram cloud speaker diarization."
    )

    try:
        return (
            _diarize_audio_deepgram(
                audio_path
            )
        )

    except Exception as deepgram_exc:
        if not (
            settings
            .diarization_fallback_to_local
        ):
            raise

        logger.warning(
            "Deepgram diarization failed. "
            "Falling back to local Pyannote. "
            "Reason: %s",
            deepgram_exc,
        )

        return (
            _diarize_audio_local(
                audio_path
            )
        )


def calculate_overlap(
    start_a: float,
    end_a: float,
    start_b: float,
    end_b: float,
) -> float:
    """
    Calculate temporal overlap between two intervals.
    """

    overlap_start = max(
        start_a,
        start_b,
    )

    overlap_end = min(
        end_a,
        end_b,
    )

    return max(
        0.0,
        overlap_end
        - overlap_start,
    )


def find_best_speaker_label(
    segment_start: float,
    segment_end: float,
    speaker_turns: list[
        SpeakerTurn
    ],
) -> str | None:
    """
    Assign a transcript segment to the speaker whose diarization
    interval overlaps it for the greatest duration.
    """

    best_label: str | None = (
        None
    )

    best_overlap = 0.0

    for turn in speaker_turns:
        overlap = calculate_overlap(
            segment_start,
            segment_end,
            turn.start_time,
            turn.end_time,
        )

        if overlap > best_overlap:
            best_overlap = overlap

            best_label = (
                turn.speaker_label
            )

    if best_label is not None:
        return best_label

    midpoint = (
        segment_start
        + segment_end
    ) / 2

    for turn in speaker_turns:
        if (
            turn.start_time
            <= midpoint
            <= turn.end_time
        ):
            return (
                turn.speaker_label
            )

    return None
