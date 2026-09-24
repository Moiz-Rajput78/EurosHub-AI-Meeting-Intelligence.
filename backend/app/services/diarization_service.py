import logging
import wave
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import numpy as np
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


def diarize_audio(
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
