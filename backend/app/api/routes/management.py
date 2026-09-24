import logging
from pathlib import Path

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    status,
)
from sqlalchemy import (
    delete,
    func,
    select,
)
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.analysis import (
    ActionItem,
    Decision,
    MeetingAnalysis,
    MeetingRequirement,
    OpenIssue,
)
from app.models.meeting import (
    Meeting,
    MeetingStatus,
)
from app.models.speaker import Speaker
from app.models.transcript import (
    TranscriptSegment,
)
from app.schemas.management import (
    MeetingDeleteResponse,
    MeetingDetailResponse,
    MeetingListItemResponse,
    MeetingListResponse,
    MeetingStatusResponse,
    TranscriptSegmentUpdateRequest,
    TranscriptSegmentUpdateResponse,
)


logger = logging.getLogger(
    __name__
)


router = APIRouter(
    tags=[
        "Meeting Management"
    ],
)


def _count_transcript_segments(
    db: Session,
    meeting_id: int,
) -> int:
    statement = (
        select(
            func.count(
                TranscriptSegment.id
            )
        )
        .where(
            TranscriptSegment.meeting_id
            == meeting_id
        )
    )

    return int(
        db.scalar(
            statement
        )
        or 0
    )


def _count_speakers(
    db: Session,
    meeting_id: int,
) -> int:
    statement = (
        select(
            func.count(
                Speaker.id
            )
        )
        .where(
            Speaker.meeting_id
            == meeting_id
        )
    )

    return int(
        db.scalar(
            statement
        )
        or 0
    )


def _meeting_has_notes(
    db: Session,
    meeting_id: int,
) -> bool:
    statement = (
        select(
            MeetingAnalysis.id
        )
        .where(
            MeetingAnalysis.meeting_id
            == meeting_id
        )
        .limit(
            1
        )
    )

    return (
        db.scalar(
            statement
        )
        is not None
    )


def _delete_analysis_records(
    db: Session,
    meeting_id: int,
) -> bool:
    """
    Delete all AI-generated meeting intelligence
    associated with one meeting.

    Returns True when an analysis record existed.
    """

    had_notes = (
        _meeting_has_notes(
            db,
            meeting_id,
        )
    )

    db.execute(
        delete(
            Decision
        ).where(
            Decision.meeting_id
            == meeting_id
        )
    )

    db.execute(
        delete(
            ActionItem
        ).where(
            ActionItem.meeting_id
            == meeting_id
        )
    )

    db.execute(
        delete(
            OpenIssue
        ).where(
            OpenIssue.meeting_id
            == meeting_id
        )
    )

    db.execute(
        delete(
            MeetingRequirement
        ).where(
            MeetingRequirement.meeting_id
            == meeting_id
        )
    )

    db.execute(
        delete(
            MeetingAnalysis
        ).where(
            MeetingAnalysis.meeting_id
            == meeting_id
        )
    )

    return had_notes


def _safe_delete_file(
    file_path: str | None,
) -> None:
    """
    Best-effort deletion for meeting media files.

    Database deletion should not fail merely because
    a previously stored file no longer exists.
    """

    if not file_path:
        return

    try:
        path = Path(
            file_path
        )

        if path.exists():
            path.unlink()

    except OSError:
        logger.exception(
            "Unable to delete meeting file: %s",
            file_path,
        )


@router.get(
    "/meetings",
    response_model=MeetingListResponse,
)
def list_meetings(
    db: Session = Depends(
        get_db
    ),
) -> MeetingListResponse:
    """
    Return meeting history ordered newest first.
    """

    meetings = list(
        db.scalars(
            select(
                Meeting
            )
            .order_by(
                Meeting.created_at.desc()
            )
        ).all()
    )

    results: list[
        MeetingListItemResponse
    ] = []

    for meeting in meetings:
        transcript_count = (
            _count_transcript_segments(
                db,
                meeting.id,
            )
        )

        speaker_count = (
            _count_speakers(
                db,
                meeting.id,
            )
        )

        results.append(
            MeetingListItemResponse(
                id=meeting.id,
                title=meeting.title,
                original_filename=(
                    meeting.original_filename
                ),
                status=(
                    meeting.status.value
                ),
                duration=(
                    meeting.duration
                ),
                language=(
                    meeting.language
                ),
                transcript_segment_count=(
                    transcript_count
                ),
                speaker_count=(
                    speaker_count
                ),
                created_at=(
                    meeting.created_at
                ),
                updated_at=(
                    meeting.updated_at
                ),
            )
        )

    return MeetingListResponse(
        count=len(
            results
        ),
        meetings=results,
    )


@router.get(
    "/meetings/{meeting_id}",
    response_model=MeetingDetailResponse,
)
def get_meeting(
    meeting_id: int,
    db: Session = Depends(
        get_db
    ),
) -> MeetingDetailResponse:
    """
    Return high-level information about one meeting.
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

    transcript_count = (
        _count_transcript_segments(
            db,
            meeting_id,
        )
    )

    speaker_count = (
        _count_speakers(
            db,
            meeting_id,
        )
    )

    has_notes = (
        _meeting_has_notes(
            db,
            meeting_id,
        )
    )

    return MeetingDetailResponse(
        id=meeting.id,
        title=meeting.title,
        original_filename=(
            meeting.original_filename
        ),
        stored_filename=(
            meeting.stored_filename
        ),
        status=(
            meeting.status.value
        ),
        duration=(
            meeting.duration
        ),
        language=(
            meeting.language
        ),
        transcript_segment_count=(
            transcript_count
        ),
        speaker_count=(
            speaker_count
        ),
        has_transcript=(
            transcript_count > 0
        ),
        has_speakers=(
            speaker_count > 0
        ),
        has_notes=(
            has_notes
        ),
        error_message=(
            meeting.error_message
        ),
        created_at=(
            meeting.created_at
        ),
        updated_at=(
            meeting.updated_at
        ),
    )


@router.get(
    "/meetings/{meeting_id}/status",
    response_model=MeetingStatusResponse,
)
def get_meeting_status(
    meeting_id: int,
    db: Session = Depends(
        get_db
    ),
) -> MeetingStatusResponse:
    """
    Return the current processing state of a meeting.
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

    transcript_count = (
        _count_transcript_segments(
            db,
            meeting_id,
        )
    )

    speaker_count = (
        _count_speakers(
            db,
            meeting_id,
        )
    )

    has_notes = (
        _meeting_has_notes(
            db,
            meeting_id,
        )
    )

    status_messages = {
        MeetingStatus.UPLOADED: (
            "Meeting is uploaded and ready "
            "for the next processing stage."
        ),
        MeetingStatus.PROCESSING_AUDIO: (
            "Meeting audio is being processed."
        ),
        MeetingStatus.TRANSCRIBING: (
            "Meeting transcription is in progress."
        ),
        MeetingStatus.DIARIZING: (
            "Speaker diarization is in progress."
        ),
        MeetingStatus.GENERATING_NOTES: (
            "AI meeting notes are being generated."
        ),
        MeetingStatus.COMPLETED: (
            "Meeting processing is complete."
        ),
        MeetingStatus.FAILED: (
            "Meeting processing encountered an error."
        ),
    }

    return MeetingStatusResponse(
        meeting_id=meeting.id,
        status=(
            meeting.status.value
        ),
        error_message=(
            meeting.error_message
        ),
        has_transcript=(
            transcript_count > 0
        ),
        has_speakers=(
            speaker_count > 0
        ),
        has_notes=(
            has_notes
        ),
        transcript_segment_count=(
            transcript_count
        ),
        message=(
            status_messages.get(
                meeting.status,
                "Meeting status is available.",
            )
        ),
    )


@router.delete(
    "/meetings/{meeting_id}",
    response_model=MeetingDeleteResponse,
)
def delete_meeting(
    meeting_id: int,
    db: Session = Depends(
        get_db
    ),
) -> MeetingDeleteResponse:
    """
    Permanently delete a meeting and all of its
    transcript, speakers and generated intelligence.
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

    uploaded_file_path = (
        meeting.file_path
    )

    normalized_audio_path = (
        meeting.normalized_audio_path
    )

    try:
        _delete_analysis_records(
            db,
            meeting_id,
        )

        db.execute(
            delete(
                TranscriptSegment
            ).where(
                TranscriptSegment.meeting_id
                == meeting_id
            )
        )

        db.execute(
            delete(
                Speaker
            ).where(
                Speaker.meeting_id
                == meeting_id
            )
        )

        db.delete(
            meeting
        )

        db.commit()

    except SQLAlchemyError as exc:
        db.rollback()

        logger.exception(
            "Failed to delete meeting %s.",
            meeting_id,
        )

        raise HTTPException(
            status_code=(
                status.HTTP_500_INTERNAL_SERVER_ERROR
            ),
            detail=(
                "The meeting could not be deleted."
            ),
        ) from exc

    _safe_delete_file(
        uploaded_file_path
    )

    if (
        normalized_audio_path
        and normalized_audio_path
        != uploaded_file_path
    ):
        _safe_delete_file(
            normalized_audio_path
        )

    return MeetingDeleteResponse(
        meeting_id=meeting_id,
        deleted=True,
        message=(
            "Meeting and associated data "
            "deleted successfully."
        ),
    )


@router.put(
    "/transcript-segments/{segment_id}",
    response_model=(
        TranscriptSegmentUpdateResponse
    ),
)
def update_transcript_segment(
    segment_id: int,
    payload: TranscriptSegmentUpdateRequest,
    db: Session = Depends(
        get_db
    ),
) -> TranscriptSegmentUpdateResponse:
    """
    Edit a transcript segment.

    Generated AI notes are invalidated because they were
    created from the previous transcript contents.
    """

    segment = db.get(
        TranscriptSegment,
        segment_id,
    )

    if segment is None:
        raise HTTPException(
            status_code=(
                status.HTTP_404_NOT_FOUND
            ),
            detail=(
                "Transcript segment not found."
            ),
        )

    cleaned_text = (
        payload.text.strip()
    )

    if not cleaned_text:
        raise HTTPException(
            status_code=(
                status.HTTP_422_UNPROCESSABLE_CONTENT
            ),
            detail=(
                "Transcript text cannot be empty."
            ),
        )

    meeting = db.get(
        Meeting,
        segment.meeting_id,
    )

    if meeting is None:
        raise HTTPException(
            status_code=(
                status.HTTP_404_NOT_FOUND
            ),
            detail=(
                "The meeting associated with this "
                "transcript segment no longer exists."
            ),
        )

    try:
        segment.edited_text = (
            cleaned_text
        )

        notes_invalidated = (
            _delete_analysis_records(
                db,
                meeting.id,
            )
        )

        if notes_invalidated:
            meeting.status = (
                MeetingStatus.UPLOADED
            )

            meeting.error_message = None

        db.commit()

        db.refresh(
            segment
        )

        return (
            TranscriptSegmentUpdateResponse(
                id=segment.id,
                meeting_id=(
                    segment.meeting_id
                ),
                start_time=(
                    segment.start_time
                ),
                end_time=(
                    segment.end_time
                ),
                original_text=(
                    segment.original_text
                ),
                edited_text=(
                    segment.edited_text
                ),
                speaker_id=(
                    segment.speaker_id
                ),
                notes_invalidated=(
                    notes_invalidated
                ),
                message=(
                    "Transcript segment updated "
                    "successfully."
                    + (
                        " Existing AI notes were "
                        "invalidated and should be "
                        "generated again."
                        if notes_invalidated
                        else ""
                    )
                ),
            )
        )

    except SQLAlchemyError as exc:
        db.rollback()

        logger.exception(
            "Failed to update transcript "
            "segment %s.",
            segment_id,
        )

        raise HTTPException(
            status_code=(
                status.HTTP_500_INTERNAL_SERVER_ERROR
            ),
            detail=(
                "Transcript segment could "
                "not be updated."
            ),
        ) from exc