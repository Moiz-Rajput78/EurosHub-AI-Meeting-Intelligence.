import logging
import mimetypes
from pathlib import Path

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    status,
)
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.models.meeting import Meeting
from app.services.audio_service import (
    ensure_browser_playback_media,
)


logger = logging.getLogger(
    __name__
)


router = APIRouter(
    prefix="/meetings",
    tags=["Meeting Media"],
)


def _resolve_safe_media_path(
    file_path: str,
) -> Path:
    """
    Resolve a stored meeting media path while ensuring
    that the file remains inside the configured upload
    directory.

    This prevents arbitrary filesystem access.
    """

    media_path = Path(
        file_path
    ).resolve()

    upload_root = (
        settings
        .upload_path
        .resolve()
    )

    try:
        media_path.relative_to(
            upload_root
        )
    except ValueError as exc:
        logger.warning(
            "Rejected unsafe meeting media path: %s",
            media_path,
        )

        raise HTTPException(
            status_code=(
                status.HTTP_403_FORBIDDEN
            ),
            detail=(
                "The meeting media path "
                "is not allowed."
            ),
        ) from exc

    return media_path


def _get_playback_media_path(
    meeting: Meeting,
    source_path: Path,
) -> Path:
    """
    Return the best file for browser playback.

    WebM recordings are converted to a cached browser-safe
    MP4. This fixes Chrome/MediaRecorder files that have no
    usable duration metadata and would otherwise show an
    incorrect duration in the HTML media player.

    Other supported formats are served directly.
    """

    if (
        source_path.suffix.lower()
        != ".webm"
    ):
        return source_path

    try:
        playback_path = Path(
            ensure_browser_playback_media(
                source_path
            )
        ).resolve()
    except HTTPException:
        logger.exception(
            "Could not prepare browser playback "
            "media for meeting %s.",
            meeting.id,
        )
        raise

    return _resolve_safe_media_path(
        str(playback_path)
    )


@router.get(
    "/{meeting_id}/media",
    response_class=FileResponse,
)
def get_meeting_media(
    meeting_id: int,
    db: Session = Depends(
        get_db
    ),
) -> FileResponse:
    """
    Stream the meeting recording.

    For problematic WebM recordings, a browser-safe MP4
    playback copy is generated once and then cached. This
    allows the browser to read the full duration and seek
    correctly while preserving the original uploaded file.

    FileResponse supports browser media playback and
    byte-range requests.
    """

    meeting = db.get(
        Meeting,
        meeting_id,
    )

    if meeting is None:
        raise HTTPException(
            status_code=(
                status.HTTP_404_NOT_FOUND
            ),
            detail="Meeting not found.",
        )

    if not meeting.file_path:
        raise HTTPException(
            status_code=(
                status.HTTP_404_NOT_FOUND
            ),
            detail=(
                "This meeting does not "
                "have a stored recording."
            ),
        )

    source_path = (
        _resolve_safe_media_path(
            meeting.file_path
        )
    )

    if (
        not source_path.exists()
        or not source_path.is_file()
    ):
        raise HTTPException(
            status_code=(
                status.HTTP_404_NOT_FOUND
            ),
            detail=(
                "The meeting recording "
                "could not be found."
            ),
        )

    media_path = (
        _get_playback_media_path(
            meeting,
            source_path,
        )
    )

    if (
        not media_path.exists()
        or not media_path.is_file()
    ):
        raise HTTPException(
            status_code=(
                status.HTTP_404_NOT_FOUND
            ),
            detail=(
                "The browser playback file "
                "could not be found."
            ),
        )

    using_browser_mp4 = (
        media_path.suffix.lower()
        == ".mp4"
        and source_path.suffix.lower()
        == ".webm"
    )

    if using_browser_mp4:
        media_type = "video/mp4"

        original_stem = Path(
            meeting.original_filename
        ).stem

        download_filename = (
            f"{original_stem}.mp4"
        )
    else:
        media_type, _ = (
            mimetypes.guess_type(
                meeting.original_filename
            )
        )

        if not media_type:
            media_type = (
                "application/octet-stream"
            )

        download_filename = (
            meeting.original_filename
        )

    return FileResponse(
        path=media_path,
        media_type=media_type,
        filename=download_filename,
        content_disposition_type=(
            "inline"
        ),
    )
