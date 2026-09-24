import json
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Callable
from uuid import uuid4

from fastapi import HTTPException, status

from app.core.config import settings


ProgressCallback = Callable[[int], None]


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


def _parse_duration_value(
    value: object,
) -> float | None:
    """
    Convert a numeric FFprobe duration value into seconds.
    """

    if value is None:
        return None

    try:
        duration = float(value)
    except (TypeError, ValueError):
        return None

    if duration <= 0:
        return None

    return duration


def _parse_duration_tag(
    value: object,
) -> float | None:
    """
    Parse WebM/Matroska duration tags such as:

    00:14:23.456000000

    Some WebM recordings do not expose format.duration or
    stream.duration but do contain a DURATION metadata tag.
    """

    if not isinstance(value, str):
        return None

    cleaned = value.strip()

    if not cleaned:
        return None

    parts = cleaned.split(":")

    if len(parts) != 3:
        return None

    try:
        hours = float(parts[0])
        minutes = float(parts[1])
        seconds = float(parts[2])
    except ValueError:
        return None

    total = (
        hours * 3600
        + minutes * 60
        + seconds
    )

    if total <= 0:
        return None

    return total


def _duration_from_metadata(
    metadata: dict,
) -> float | None:
    """
    Attempt to determine media duration from normal FFprobe
    metadata before using slower fallbacks.
    """

    format_info = metadata.get(
        "format",
        {},
    )

    duration = _parse_duration_value(
        format_info.get(
            "duration"
        )
    )

    if duration is not None:
        return duration

    streams = metadata.get(
        "streams",
        [],
    )

    for stream in streams:
        duration = _parse_duration_value(
            stream.get(
                "duration"
            )
        )

        if duration is not None:
            return duration

    format_tags = format_info.get(
        "tags",
        {},
    )

    if isinstance(
        format_tags,
        dict,
    ):
        duration = _parse_duration_tag(
            format_tags.get(
                "DURATION"
            )
            or format_tags.get(
                "duration"
            )
        )

        if duration is not None:
            return duration

    for stream in streams:
        tags = stream.get(
            "tags",
            {},
        )

        if not isinstance(
            tags,
            dict,
        ):
            continue

        duration = _parse_duration_tag(
            tags.get(
                "DURATION"
            )
            or tags.get(
                "duration"
            )
        )

        if duration is not None:
            return duration

    return None


def _probe_duration_from_packets(
    source: Path,
) -> float | None:
    """
    Fallback for valid WebM/Matroska recordings where FFprobe
    does not expose a normal duration field.

    Reads packet timestamps and uses the last valid audio/video
    timestamp as the approximate duration.
    """

    command = [
        "ffprobe",
        "-v",
        "error",
        "-select_streams",
        "a:0",
        "-show_entries",
        (
            "packet=pts_time,dts_time,"
            "duration_time"
        ),
        "-of",
        "json",
        str(source),
    ]

    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=False,
            timeout=120,
        )

    except (
        subprocess.TimeoutExpired,
        OSError,
    ):
        return None

    if result.returncode != 0:
        return None

    try:
        payload = json.loads(
            result.stdout
        )
    except json.JSONDecodeError:
        return None

    packets = payload.get(
        "packets",
        [],
    )

    if not packets:
        return None

    last_end = 0.0

    for packet in packets:
        timestamp = (
            _parse_duration_value(
                packet.get(
                    "pts_time"
                )
            )
            or _parse_duration_value(
                packet.get(
                    "dts_time"
                )
            )
        )

        if timestamp is None:
            continue

        packet_duration = (
            _parse_duration_value(
                packet.get(
                    "duration_time"
                )
            )
            or 0.0
        )

        packet_end = (
            timestamp
            + packet_duration
        )

        if packet_end > last_end:
            last_end = packet_end

    if last_end <= 0:
        return None

    return last_end


def probe_media(
    file_path: str | Path,
) -> MediaInfo:
    """
    Inspect a media file using FFprobe.

    Supports normal duration fields as well as WebM/Matroska
    duration tags and packet-timestamp fallback.
    """

    ensure_ffmpeg_available()

    source = Path(
        file_path
    ).resolve()

    if (
        not source.exists()
        or not source.is_file()
    ):
        raise HTTPException(
            status_code=(
                status.HTTP_404_NOT_FOUND
            ),
            detail=(
                "The uploaded meeting recording "
                "could not be found."
            ),
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
            status_code=(
                status.HTTP_422_UNPROCESSABLE_CONTENT
            ),
            detail=(
                "The recording could not be inspected "
                "because media validation timed out."
            ),
        ) from exc

    except OSError as exc:
        raise HTTPException(
            status_code=(
                status.HTTP_500_INTERNAL_SERVER_ERROR
            ),
            detail=(
                "The media inspection process "
                "could not be started."
            ),
        ) from exc

    if result.returncode != 0:
        raise HTTPException(
            status_code=(
                status.HTTP_422_UNPROCESSABLE_CONTENT
            ),
            detail=(
                "The uploaded recording is corrupted "
                "or is not a valid supported media file."
            ),
        )

    try:
        metadata = json.loads(
            result.stdout
        )

    except json.JSONDecodeError as exc:
        raise HTTPException(
            status_code=(
                status.HTTP_422_UNPROCESSABLE_CONTENT
            ),
            detail=(
                "The recording metadata "
                "could not be read."
            ),
        ) from exc

    streams = metadata.get(
        "streams",
        [],
    )

    has_audio = any(
        stream.get(
            "codec_type"
        )
        == "audio"
        for stream in streams
    )

    has_video = any(
        stream.get(
            "codec_type"
        )
        == "video"
        for stream in streams
    )

    if not has_audio:
        raise HTTPException(
            status_code=(
                status.HTTP_422_UNPROCESSABLE_CONTENT
            ),
            detail=(
                "The uploaded recording does not "
                "contain an audio stream."
            ),
        )

    duration = (
        _duration_from_metadata(
            metadata
        )
    )

    if duration is None:
        duration = (
            _probe_duration_from_packets(
                source
            )
        )

    if (
        duration is None
        or duration <= 0
    ):
        raise HTTPException(
            status_code=(
                status.HTTP_422_UNPROCESSABLE_CONTENT
            ),
            detail=(
                "The recording appears valid, "
                "but its duration could not be determined."
            ),
        )

    format_info = metadata.get(
        "format",
        {},
    )

    return MediaInfo(
        duration=duration,
        has_audio=has_audio,
        has_video=has_video,
        format_name=(
            format_info.get(
                "format_name"
            )
        ),
    )



def build_browser_playback_path(
    source_path: str | Path,
) -> Path:
    """
    Build a deterministic, safe MP4 path used only for browser playback.

    The original uploaded recording is preserved. The generated MP4 lives
    under uploads/browser_media and can be reused on later media requests.
    """

    source = Path(
        source_path
    ).resolve()

    browser_directory = (
        settings.upload_path
        / "browser_media"
    ).resolve()

    browser_directory.mkdir(
        parents=True,
        exist_ok=True,
    )

    destination = (
        browser_directory
        / f"{source.stem}.mp4"
    ).resolve()

    try:
        destination.relative_to(
            browser_directory
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=(
                status.HTTP_400_BAD_REQUEST
            ),
            detail=(
                "Invalid browser playback path."
            ),
        ) from exc

    return destination


def _run_browser_playback_command(
    command: list[str],
    destination: Path,
) -> tuple[int, str]:
    """
    Execute an FFmpeg browser-playback conversion command.
    """

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
            status_code=(
                status.HTTP_500_INTERNAL_SERVER_ERROR
            ),
            detail=(
                "FFmpeg could not be started while preparing "
                "browser playback."
            ),
        ) from exc

    return (
        result.returncode,
        result.stderr or "",
    )


def ensure_browser_playback_media(
    source_path: str | Path,
) -> str:
    """
    Return a browser-safe media path.

    Chrome/MediaRecorder WebM files can contain H.264 video while exposing
    no duration metadata. Browsers may then display an incorrect duration
    and seeking can behave incorrectly.

    For WebM video, create and cache an MP4 playback copy:
    - H.264 is copied when possible, making the conversion very fast.
    - Opus audio is converted to AAC for MP4 compatibility.
    - If stream-copying the video fails, FFmpeg retries with H.264 encoding.
    - The original upload is never overwritten.

    Non-WebM files are returned unchanged.
    """

    ensure_ffmpeg_available()

    source = Path(
        source_path
    ).resolve()

    if (
        not source.exists()
        or not source.is_file()
    ):
        raise HTTPException(
            status_code=(
                status.HTTP_404_NOT_FOUND
            ),
            detail=(
                "The source recording could not be found."
            ),
        )

    if source.suffix.lower() != ".webm":
        return str(source)

    destination = (
        build_browser_playback_path(
            source
        )
    )

    # Reuse an existing valid cached copy unless the source has changed.
    if (
        destination.exists()
        and destination.is_file()
        and destination.stat().st_size > 0
        and destination.stat().st_mtime
        >= source.stat().st_mtime
    ):
        return str(destination)

    if destination.exists():
        destination.unlink()

    # First try the fast path that succeeded for Chrome-created H.264 WebM:
    # copy video, transcode Opus -> AAC, rebuild timestamps and MP4 metadata.
    copy_command = [
        "ffmpeg",
        "-y",
        "-fflags",
        "+genpts",
        "-i",
        str(source),
        "-map",
        "0:v:0?",
        "-map",
        "0:a:0?",
        "-c:v",
        "copy",
        "-c:a",
        "aac",
        "-b:a",
        "128k",
        "-movflags",
        "+faststart",
        "-avoid_negative_ts",
        "make_zero",
        str(destination),
    ]

    return_code, stderr = (
        _run_browser_playback_command(
            copy_command,
            destination,
        )
    )

    if (
        return_code == 0
        and destination.exists()
        and destination.stat().st_size > 0
    ):
        return str(destination)

    if destination.exists():
        destination.unlink()

    # Fallback for WebM video codecs that cannot be copied into MP4.
    transcode_command = [
        "ffmpeg",
        "-y",
        "-fflags",
        "+genpts",
        "-i",
        str(source),
        "-map",
        "0:v:0?",
        "-map",
        "0:a:0?",
        "-c:v",
        "libx264",
        "-preset",
        "veryfast",
        "-crf",
        "23",
        "-c:a",
        "aac",
        "-b:a",
        "128k",
        "-movflags",
        "+faststart",
        "-avoid_negative_ts",
        "make_zero",
        str(destination),
    ]

    fallback_code, fallback_stderr = (
        _run_browser_playback_command(
            transcode_command,
            destination,
        )
    )

    if (
        fallback_code != 0
        or not destination.exists()
        or destination.stat().st_size == 0
    ):
        if destination.exists():
            destination.unlink()

        ffmpeg_error = (
            fallback_stderr.strip()
            or stderr.strip()
        )

        detail = (
            "The recording could not be prepared for "
            "browser-safe playback."
        )

        if ffmpeg_error:
            detail += (
                f" FFmpeg: {ffmpeg_error}"
            )

        raise HTTPException(
            status_code=(
                status.HTTP_422_UNPROCESSABLE_CONTENT
            ),
            detail=detail,
        )

    return str(destination)


def delete_browser_playback_media(
    source_path: str | Path | None,
) -> None:
    """
    Delete the cached browser-safe MP4 generated for a source recording.

    This helper is safe to call from the meeting-deletion flow.
    """

    if not source_path:
        return

    try:
        destination = (
            build_browser_playback_path(
                source_path
            )
        )
    except HTTPException:
        return

    if (
        destination.exists()
        and destination.is_file()
    ):
        destination.unlink()


def build_normalized_audio_path() -> Path:
    """
    Create a safe destination path for normalized
    transcription audio.
    """

    audio_directory = (
        settings.upload_path
        / "processed"
    ).resolve()

    audio_directory.mkdir(
        parents=True,
        exist_ok=True,
    )

    filename = (
        f"{uuid4().hex}.wav"
    )

    destination = (
        audio_directory
        / filename
    ).resolve()

    try:
        destination.relative_to(
            audio_directory
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=(
                status.HTTP_400_BAD_REQUEST
            ),
            detail=(
                "Invalid processed-audio path."
            ),
        ) from exc

    return destination


def extract_and_normalize_audio(
    source_path: str | Path,
    *,
    duration: float | None = None,
    progress_callback: (
        ProgressCallback | None
    ) = None,
) -> str:
    """
    Extract and normalize audio using FFmpeg.

    Output:
    - WAV
    - mono
    - 16 kHz
    - PCM 16-bit

    When duration and progress_callback are provided,
    FFmpeg's real processed timestamp is converted into
    a real 0-100 percentage.

    Returns the absolute normalized audio path.
    """

    ensure_ffmpeg_available()

    source = Path(
        source_path
    ).resolve()

    if (
        not source.exists()
        or not source.is_file()
    ):
        raise HTTPException(
            status_code=(
                status.HTTP_404_NOT_FOUND
            ),
            detail=(
                "The source recording "
                "could not be found."
            ),
        )

    destination = (
        build_normalized_audio_path()
    )

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
        "-progress",
        "pipe:1",
        "-nostats",
        str(destination),
    ]

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

    try:
        process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
        )

        if process.stdout is not None:
            for raw_line in (
                process.stdout
            ):
                line = (
                    raw_line.strip()
                )

                if (
                    not duration
                    or duration <= 0
                ):
                    continue

                processed_seconds: (
                    float | None
                ) = None

                if line.startswith(
                    "out_time_us="
                ):
                    try:
                        processed_seconds = (
                            int(
                                line.split(
                                    "=",
                                    1,
                                )[1]
                            )
                            / 1_000_000
                        )
                    except ValueError:
                        processed_seconds = (
                            None
                        )

                elif line.startswith(
                    "out_time_ms="
                ):
                    try:
                        processed_seconds = (
                            int(
                                line.split(
                                    "=",
                                    1,
                                )[1]
                            )
                            / 1_000_000
                        )
                    except ValueError:
                        processed_seconds = (
                            None
                        )

                if (
                    processed_seconds
                    is not None
                ):
                    progress = round(
                        processed_seconds
                        / duration
                        * 100
                    )

                    report(
                        progress
                    )

        stderr = (
            process.stderr.read()
            if process.stderr
            is not None
            else ""
        )

        return_code = (
            process.wait()
        )

    except OSError as exc:
        if destination.exists():
            destination.unlink()

        raise HTTPException(
            status_code=(
                status.HTTP_500_INTERNAL_SERVER_ERROR
            ),
            detail=(
                "FFmpeg could not be started."
            ),
        ) from exc

    if return_code != 0:
        if destination.exists():
            destination.unlink()

        detail = (
            "Audio extraction failed. "
            "The uploaded recording may be "
            "corrupted or unsupported."
        )

        if stderr.strip():
            detail += (
                f" FFmpeg: "
                f"{stderr.strip()}"
            )

        raise HTTPException(
            status_code=(
                status.HTTP_422_UNPROCESSABLE_CONTENT
            ),
            detail=detail,
        )

    if not destination.exists():
        raise HTTPException(
            status_code=(
                status.HTTP_500_INTERNAL_SERVER_ERROR
            ),
            detail=(
                "The normalized audio file "
                "was not created."
            ),
        )

    if (
        destination.stat().st_size
        == 0
    ):
        destination.unlink()

        raise HTTPException(
            status_code=(
                status.HTTP_422_UNPROCESSABLE_CONTENT
            ),
            detail=(
                "The extracted audio file "
                "is empty."
            ),
        )

    report(100)

    return str(
        destination
    )


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

    target = Path(
        audio_path
    ).resolve()

    try:
        target.relative_to(
            processed_directory
        )

    except ValueError:
        return

    if (
        target.exists()
        and target.is_file()
    ):
        target.unlink()