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
    Stream the original uploaded meeting recording.

    FileResponse supports browser media playback and
    byte-range requests, allowing users to seek within
    audio/video recordings.
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

    media_path = (
        _resolve_safe_media_path(
            meeting.file_path
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
                "The meeting recording "
                "could not be found."
            ),
        )

    media_type, _ = (
        mimetypes.guess_type(
            meeting.original_filename
        )
    )

    if not media_type:
        media_type = (
            "application/octet-stream"
        )

    return FileResponse(
        path=media_path,
        media_type=media_type,
        filename=(
            meeting.original_filename
        ),
        content_disposition_type=(
            "inline"
        ),
    )