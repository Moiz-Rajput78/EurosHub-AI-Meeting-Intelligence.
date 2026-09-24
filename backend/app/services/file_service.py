import re
import unicodedata
from pathlib import Path
from uuid import uuid4

from fastapi import HTTPException, UploadFile, status

from app.core.config import settings


ALLOWED_FILE_TYPES: dict[str, set[str]] = {
    ".mp3": {
        "audio/mpeg",
        "audio/mp3",
        "application/octet-stream",
    },
    ".wav": {
        "audio/wav",
        "audio/x-wav",
        "audio/wave",
        "application/octet-stream",
    },
    ".m4a": {
        "audio/mp4",
        "audio/x-m4a",
        "audio/m4a",
        "video/mp4",
        "application/octet-stream",
    },
    ".mp4": {
        "video/mp4",
        "audio/mp4",
        "application/mp4",
        "application/octet-stream",
    },
    ".webm": {
        "video/webm",
        "audio/webm",
        "application/octet-stream",
    },
}


CHUNK_SIZE = 1024 * 1024


def sanitize_filename(filename: str) -> str:
    """
    Remove unsafe and filesystem-unfriendly characters from
    the original filename.

    The original user filename is preserved in sanitized form,
    while the actual stored file receives a UUID filename.
    """

    filename = Path(filename).name

    filename = unicodedata.normalize(
        "NFKC",
        filename,
    )

    filename = re.sub(
        r"[^A-Za-z0-9._()\- ]",
        "_",
        filename,
    )

    filename = filename.strip(" .")

    if not filename:
        filename = "meeting"

    return filename


def validate_file_extension(
    filename: str,
) -> str:
    """
    Validate the recording's extension and return it.
    """

    extension = Path(filename).suffix.lower()

    if extension not in ALLOWED_FILE_TYPES:
        supported = ", ".join(
            sorted(
                ext.replace(".", "").upper()
                for ext in ALLOWED_FILE_TYPES
            )
        )

        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=(
                f"Unsupported file type. "
                f"Supported formats are: {supported}."
            ),
        )

    return extension


def validate_mime_type(
    extension: str,
    content_type: str | None,
) -> None:
    """
    Validate the MIME type supplied with the uploaded file.

    Real media validation using FFmpeg/ffprobe will be added
    during the audio-processing stage.
    """

    if not content_type:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="The uploaded file does not have a valid MIME type.",
        )

    normalized_content_type = (
        content_type
        .split(";")[0]
        .strip()
        .lower()
    )

    allowed_mime_types = ALLOWED_FILE_TYPES[extension]

    if normalized_content_type not in allowed_mime_types:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=(
                f"The MIME type '{normalized_content_type}' "
                f"does not match the uploaded {extension} file."
            ),
        )


def build_safe_upload_path(
    extension: str,
) -> tuple[str, Path]:
    """
    Generate a UUID filename and guarantee that the resulting
    path remains inside the configured upload directory.
    """

    upload_directory = settings.upload_path

    upload_directory.mkdir(
        parents=True,
        exist_ok=True,
    )

    stored_filename = f"{uuid4().hex}{extension}"

    destination = (
        upload_directory / stored_filename
    ).resolve()

    try:
        destination.relative_to(
            upload_directory
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid upload path.",
        ) from exc

    return stored_filename, destination


async def save_upload_file(
    upload_file: UploadFile,
) -> tuple[str, str, int]:
    """
    Validate and safely save an uploaded recording.

    Files are streamed in chunks so large recordings are not
    loaded entirely into memory.

    Returns:
        stored_filename
        absolute_file_path
        file_size_bytes
    """

    if not upload_file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No filename was provided.",
        )

    safe_original_filename = sanitize_filename(
        upload_file.filename
    )

    extension = validate_file_extension(
        safe_original_filename
    )

    validate_mime_type(
        extension=extension,
        content_type=upload_file.content_type,
    )

    stored_filename, destination = (
        build_safe_upload_path(extension)
    )

    maximum_size_bytes = (
        settings.max_upload_size_mb
        * 1024
        * 1024
    )

    total_bytes = 0

    try:
        with destination.open("wb") as output_file:
            while True:
                chunk = await upload_file.read(
                    CHUNK_SIZE
                )

                if not chunk:
                    break

                total_bytes += len(chunk)

                if total_bytes > maximum_size_bytes:
                    output_file.close()

                    if destination.exists():
                        destination.unlink()

                    raise HTTPException(
                        status_code=status.HTTP_413_CONTENT_TOO_LARGE,
                        detail=(
                            "The uploaded file exceeds "
                            f"the maximum size of "
                            f"{settings.max_upload_size_mb} MB."
                        ),
                    )

                output_file.write(chunk)

    except HTTPException:
        raise

    except OSError as exc:
        if destination.exists():
            destination.unlink()

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=(
                "The recording could not be saved."
            ),
        ) from exc

    finally:
        await upload_file.close()

    if total_bytes == 0:
        if destination.exists():
            destination.unlink()

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The uploaded file is empty.",
        )

    return (
        stored_filename,
        str(destination),
        total_bytes,
    )


def delete_saved_file(
    file_path: str | Path | None,
) -> None:
    """
    Safely remove a stored recording.

    Used for cleanup if database creation or another operation
    fails after the file has already been saved.
    """

    if not file_path:
        return

    upload_directory = settings.upload_path

    target = Path(file_path).resolve()

    try:
        target.relative_to(
            upload_directory
        )
    except ValueError:
        return

    if target.exists() and target.is_file():
        target.unlink()