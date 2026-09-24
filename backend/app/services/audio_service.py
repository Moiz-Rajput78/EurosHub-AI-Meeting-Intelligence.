import json
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from uuid import uuid4

from fastapi import HTTPException, status

from app.core.config import settings


@dataclass
class MediaInfo:
    duration: float
    has_audio: bool
    has_video: bool
    format_name: str | None


def ensure_ffmpeg_available() -> None:
    """
    Ensure FFmpeg and ffprobe are available on the system PATH.
    """

    if shutil.which("ffmpeg") is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                "FFmpeg is not available. "
                "Please install FFmpeg and make sure it is "
                "available in the system PATH."
            ),
        )

    if shutil.which("ffprobe") is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                "ffprobe is not available. "
                "Please install FFmpeg and make sure ffprobe "
                "is available in the system PATH."
            ),
        )


def probe_media(file_path: str | Path) -> MediaInfo:
    """
    Inspect a media file using ffprobe.

    This validates the actual media container and streams rather
    than trusting only the file extension or browser MIME type.
    """

    ensure_ffmpeg_available()

    source = Path(file_path).resolve()

    if not source.exists() or not source.is_file():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="The uploaded meeting recording could not be found.",
        )

    command = [
        "ffprobe",
        "-v",
        "error",
        "-print_format",
        "json",
        "-show_format",
        "-show_streams",
        str(source),
    ]

    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=False,
            timeout=60,
        )

    except subprocess.TimeoutExpired as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=(
                "The recording could not be inspected because "
                "media validation timed out."
            ),
        ) from exc

    except OSError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="The media inspection process could not be started.",
        ) from exc

    if result.returncode != 0:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=(
                "The uploaded recording is corrupted or is not "
                "a valid supported media file."
            ),
        )

    try:
        metadata = json.loads(result.stdout)

    except json.JSONDecodeError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="The recording metadata could not be read.",
        ) from exc

    streams = metadata.get("streams", [])

    has_audio = any(
        stream.get("codec_type") == "audio"
        for stream in streams
    )

    has_video = any(
        stream.get("codec_type") == "video"
        for stream in streams
    )

    if not has_audio:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=(
                "The uploaded recording does not contain "
                "an audio stream."
            ),
        )

    format_info = metadata.get("format", {})

    duration_value = format_info.get("duration")

    if duration_value is None:
        for stream in streams:
            if stream.get("duration"):
                duration_value = stream.get("duration")
                break

    try:
        duration = float(duration_value)

    except (TypeError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=(
                "The duration of the uploaded recording "
                "could not be determined."
            ),
        ) from exc

    if duration <= 0:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="The uploaded recording has an invalid duration.",
        )

    return MediaInfo(
        duration=duration,
        has_audio=has_audio,
        has_video=has_video,
        format_name=format_info.get("format_name"),
    )


def build_normalized_audio_path() -> Path:
    """
    Create a safe destination path for normalized transcription audio.
    """

    audio_directory = (
        settings.upload_path
        / "processed"
    ).resolve()

    audio_directory.mkdir(
        parents=True,
        exist_ok=True,
    )

    filename = f"{uuid4().hex}.wav"

    destination = (
        audio_directory / filename
    ).resolve()

    try:
        destination.relative_to(audio_directory)

    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid processed-audio path.",
        ) from exc

    return destination


def extract_and_normalize_audio(
    source_path: str | Path,
) -> str:
    """
    Extract and normalize audio using FFmpeg.

    Output:
    - WAV
    - mono
    - 16 kHz
    - PCM 16-bit

    Returns the absolute normalized audio path.
    """

    ensure_ffmpeg_available()

    source = Path(source_path).resolve()

    if not source.exists() or not source.is_file():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="The source recording could not be found.",
        )

    destination = build_normalized_audio_path()

    command = [
        "ffmpeg",
        "-y",
        "-v",
        "error",
        "-i",
        str(source),
        "-vn",
        "-ac",
        "1",
        "-ar",
        "16000",
        "-c:a",
        "pcm_s16le",
        str(destination),
    ]

    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=False,
        )

    except OSError as exc:
        if destination.exists():
            destination.unlink()

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="FFmpeg could not be started.",
        ) from exc

    if result.returncode != 0:
        if destination.exists():
            destination.unlink()

        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=(
                "Audio extraction failed. "
                "The uploaded recording may be corrupted "
                "or unsupported."
            ),
        )

    if not destination.exists():
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="The normalized audio file was not created.",
        )

    if destination.stat().st_size == 0:
        destination.unlink()

        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="The extracted audio file is empty.",
        )

    return str(destination)


def delete_processed_audio(
    audio_path: str | Path | None,
) -> None:
    """
    Safely delete a generated processed-audio file.
    """

    if not audio_path:
        return

    processed_directory = (
        settings.upload_path
        / "processed"
    ).resolve()

    target = Path(audio_path).resolve()

    try:
        target.relative_to(processed_directory)

    except ValueError:
        return

    if target.exists() and target.is_file():
        target.unlink()