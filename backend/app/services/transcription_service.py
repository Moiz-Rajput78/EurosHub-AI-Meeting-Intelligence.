from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Callable

from faster_whisper import WhisperModel

from app.core.config import settings


ProgressCallback = Callable[[int], None]


@dataclass
class TranscriptionSegmentData:
    start_time: float
    end_time: float
    text: str


@dataclass
class TranscriptionResult:
    language: str | None
    language_probability: float | None
    duration: float | None
    segments: list[TranscriptionSegmentData]


@lru_cache(maxsize=1)
def get_whisper_model() -> WhisperModel:
    """
    Load and cache the configured faster-whisper model.

    The model is loaded once per backend process instead of
    loading it again for every transcription request.

    CPU thread and worker settings are configurable so the
    application can use the available CPU efficiently without
    hard-coding machine-specific behavior.
    """

    return WhisperModel(
        settings.whisper_model,
        device=settings.whisper_device,
        compute_type=settings.whisper_compute_type,
        cpu_threads=settings.whisper_cpu_threads,
        num_workers=settings.whisper_num_workers,
    )


def transcribe_audio(
    audio_path: str | Path,
    *,
    progress_callback: ProgressCallback | None = None,
) -> TranscriptionResult:
    """
    Transcribe normalized meeting audio using faster-whisper.

    Accuracy remains the priority. The defaults use a moderate
    beam size and VAD so CPU processing is faster than the
    previous beam_size=5 configuration without switching to a
    low-accuracy model.

    Progress is calculated from the latest emitted segment end
    timestamp divided by Whisper's detected audio duration.
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
            "The transcription source is not a valid file."
        )

    if source.stat().st_size == 0:
        raise ValueError(
            "The transcription source is empty."
        )

    model = get_whisper_model()

    configured_language = (
        settings.whisper_language.strip()
        if settings.whisper_language
        else ""
    )

    segments_generator, info = model.transcribe(
        str(source),
        language=(
            configured_language
            or None
        ),
        beam_size=settings.whisper_beam_size,
        vad_filter=settings.whisper_vad_filter,
        condition_on_previous_text=(
            settings
            .whisper_condition_on_previous_text
        ),
    )

    duration_value = getattr(
        info,
        "duration",
        None,
    )

    duration = (
        float(duration_value)
        if duration_value is not None
        else None
    )

    last_reported = -1

    def report(
        value: int,
    ) -> None:
        nonlocal last_reported

        if progress_callback is None:
            return

        bounded = max(
            0,
            min(
                100,
                int(value),
            ),
        )

        if bounded == last_reported:
            return

        last_reported = bounded

        progress_callback(
            bounded
        )

    report(0)

    transcript_segments: list[
        TranscriptionSegmentData
    ] = []

    for segment in segments_generator:
        cleaned_text = (
            segment.text.strip()
        )

        if (
            duration
            and duration > 0
        ):
            report(
                round(
                    float(
                        segment.end
                    )
                    / duration
                    * 100
                )
            )

        if not cleaned_text:
            continue

        transcript_segments.append(
            TranscriptionSegmentData(
                start_time=float(
                    segment.start
                ),
                end_time=float(
                    segment.end
                ),
                text=cleaned_text,
            )
        )

    if not transcript_segments:
        raise ValueError(
            "Whisper did not detect any speech "
            "in the recording."
        )

    language = getattr(
        info,
        "language",
        None,
    )

    language_probability = getattr(
        info,
        "language_probability",
        None,
    )

    if language_probability is not None:
        language_probability = float(
            language_probability
        )

    report(100)

    return TranscriptionResult(
        language=language,
        language_probability=(
            language_probability
        ),
        duration=duration,
        segments=transcript_segments,
    )
