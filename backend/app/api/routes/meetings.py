import logging
from pathlib import Path

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    UploadFile,
    status,
)
from sqlalchemy import delete, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.meeting import (
    Meeting,
    MeetingStatus,
)
from app.models.speaker import Speaker
from app.models.transcript import (
    TranscriptSegment,
)
from app.schemas.meeting import (
    MeetingProcessingResponse,
    MeetingUploadResponse,
)
from app.schemas.speaker import (
    DiarizationResponse,
    SpeakerResponse,
)
from app.schemas.transcript import (
    MeetingTranscriptResponse,
    TranscriptSegmentResponse,
    TranscriptionResponse,
)
from app.services.audio_service import (
    delete_processed_audio,
    extract_and_normalize_audio,
    probe_media,
)
from app.services.diarization_service import (
    diarize_audio,
    find_best_speaker_label,
)
from app.services.file_service import (
    delete_saved_file,
    save_upload_file,
    sanitize_filename,
)
from app.services.transcription_service import (
    transcribe_audio,
)


logger = logging.getLogger(
    __name__
)


router = APIRouter(
    prefix="/meetings",
    tags=["Meetings"],
)


@router.post(
    "/upload",
    response_model=MeetingUploadResponse,
    status_code=status.HTTP_201_CREATED,
)
async def upload_meeting(
    file: UploadFile = File(...),
    title: str | None = Form(
        default=None
    ),
    db: Session = Depends(
        get_db
    ),
) -> MeetingUploadResponse:
    stored_file_path: str | None = None

    if not file.filename:
        raise HTTPException(
            status_code=(
                status.HTTP_400_BAD_REQUEST
            ),
            detail=(
                "No meeting recording "
                "was selected."
            ),
        )

    safe_original_filename = (
        sanitize_filename(
            file.filename
        )
    )

    cleaned_title = (
        title.strip()
        if title and title.strip()
        else Path(
            safe_original_filename
        ).stem
    )

    if not cleaned_title:
        cleaned_title = (
            "Untitled Meeting"
        )

    if len(cleaned_title) > 255:
        raise HTTPException(
            status_code=(
                status.HTTP_422_UNPROCESSABLE_CONTENT
            ),
            detail=(
                "Meeting title cannot exceed "
                "255 characters."
            ),
        )

    try:
        (
            stored_filename,
            stored_file_path,
            file_size,
        ) = await save_upload_file(
            file
        )

        meeting = Meeting(
            title=cleaned_title,
            original_filename=(
                safe_original_filename
            ),
            stored_filename=(
                stored_filename
            ),
            file_path=(
                stored_file_path
            ),
            status=(
                MeetingStatus.UPLOADED
            ),
        )

        db.add(
            meeting
        )

        db.commit()

        db.refresh(
            meeting
        )

        return MeetingUploadResponse(
            id=meeting.id,
            title=meeting.title,
            original_filename=(
                meeting.original_filename
            ),
            stored_filename=(
                meeting.stored_filename
            ),
            status=meeting.status,
            created_at=meeting.created_at,
            message=(
                "Meeting uploaded successfully. "
                f"Stored {file_size} bytes."
            ),
        )

    except HTTPException:
        if stored_file_path:
            delete_saved_file(
                stored_file_path
            )

        db.rollback()

        raise

    except SQLAlchemyError as exc:
        db.rollback()

        if stored_file_path:
            delete_saved_file(
                stored_file_path
            )

        logger.exception(
            "Failed to create meeting "
            "database record."
        )

        raise HTTPException(
            status_code=(
                status.HTTP_500_INTERNAL_SERVER_ERROR
            ),
            detail=(
                "The meeting was uploaded, "
                "but its database record "
                "could not be created."
            ),
        ) from exc

    except Exception as exc:
        db.rollback()

        if stored_file_path:
            delete_saved_file(
                stored_file_path
            )

        logger.exception(
            "Unexpected meeting upload failure."
        )

        raise HTTPException(
            status_code=(
                status.HTTP_500_INTERNAL_SERVER_ERROR
            ),
            detail=(
                "An unexpected error occurred "
                "while uploading the meeting."
            ),
        ) from exc


@router.post(
    "/{meeting_id}/process-audio",
    response_model=MeetingProcessingResponse,
)
def process_meeting_audio(
    meeting_id: int,
    db: Session = Depends(
        get_db
    ),
) -> MeetingProcessingResponse:
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
                status.HTTP_409_CONFLICT
            ),
            detail=(
                "The meeting does not have "
                "an uploaded recording "
                "to process."
            ),
        )

    previous_audio_path = (
        meeting.normalized_audio_path
    )

    meeting.status = (
        MeetingStatus.PROCESSING_AUDIO
    )

    meeting.error_message = None

    db.commit()

    db.refresh(
        meeting
    )

    try:
        media_info = probe_media(
            meeting.file_path
        )

        new_audio_path = (
            extract_and_normalize_audio(
                meeting.file_path
            )
        )

        if (
            previous_audio_path
            and previous_audio_path
            != new_audio_path
        ):
            delete_processed_audio(
                previous_audio_path
            )

        meeting.duration = (
            media_info.duration
        )

        meeting.normalized_audio_path = (
            new_audio_path
        )

        meeting.status = (
            MeetingStatus.UPLOADED
        )

        db.commit()

        db.refresh(
            meeting
        )

        return MeetingProcessingResponse(
            id=meeting.id,
            title=meeting.title,
            status=meeting.status,
            duration=meeting.duration,
            message=(
                "Recording validated and "
                "audio normalized successfully."
            ),
        )

    except HTTPException as exc:
        db.rollback()

        meeting = db.get(
            Meeting,
            meeting_id,
        )

        if meeting is not None:
            meeting.status = (
                MeetingStatus.FAILED
            )

            meeting.error_message = str(
                exc.detail
            )

            db.commit()

        raise

    except Exception as exc:
        db.rollback()

        logger.exception(
            "Unexpected audio processing "
            "failure for meeting %s.",
            meeting_id,
        )

        meeting = db.get(
            Meeting,
            meeting_id,
        )

        if meeting is not None:
            meeting.status = (
                MeetingStatus.FAILED
            )

            meeting.error_message = (
                "Unexpected audio "
                "processing failure."
            )

            db.commit()

        raise HTTPException(
            status_code=(
                status.HTTP_500_INTERNAL_SERVER_ERROR
            ),
            detail=(
                "An unexpected error occurred "
                "while processing the recording."
            ),
        ) from exc


@router.post(
    "/{meeting_id}/transcribe",
    response_model=TranscriptionResponse,
)
def transcribe_meeting(
    meeting_id: int,
    db: Session = Depends(
        get_db
    ),
) -> TranscriptionResponse:
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

    if not meeting.normalized_audio_path:
        raise HTTPException(
            status_code=(
                status.HTTP_409_CONFLICT
            ),
            detail=(
                "The meeting audio has "
                "not been processed yet."
            ),
        )

    audio_path = Path(
        meeting.normalized_audio_path
    )

    if not audio_path.exists():
        raise HTTPException(
            status_code=(
                status.HTTP_409_CONFLICT
            ),
            detail=(
                "The normalized meeting "
                "audio could not be found."
            ),
        )

    meeting.status = (
        MeetingStatus.TRANSCRIBING
    )

    meeting.error_message = None

    db.commit()

    db.refresh(
        meeting
    )

    try:
        result = transcribe_audio(
            audio_path
        )

        db.execute(
            delete(
                TranscriptSegment
            ).where(
                TranscriptSegment.meeting_id
                == meeting.id
            )
        )

        for segment in result.segments:
            db.add(
                TranscriptSegment(
                    meeting_id=(
                        meeting.id
                    ),
                    speaker_id=None,
                    start_time=(
                        segment.start_time
                    ),
                    end_time=(
                        segment.end_time
                    ),
                    original_text=(
                        segment.text
                    ),
                    edited_text=None,
                )
            )

        meeting.language = (
            result.language
        )

        if result.duration:
            meeting.duration = (
                result.duration
            )

        meeting.status = (
            MeetingStatus.UPLOADED
        )

        db.commit()

        db.refresh(
            meeting
        )

        return TranscriptionResponse(
            meeting_id=meeting.id,
            title=meeting.title,
            language=meeting.language,
            duration=meeting.duration,
            segment_count=len(
                result.segments
            ),
            status=(
                meeting.status.value
            ),
            message=(
                "Meeting transcription "
                "completed successfully."
            ),
        )

    except (
        FileNotFoundError,
        ValueError,
    ) as exc:
        db.rollback()

        meeting = db.get(
            Meeting,
            meeting_id,
        )

        if meeting is not None:
            meeting.status = (
                MeetingStatus.FAILED
            )

            meeting.error_message = str(
                exc
            )

            db.commit()

        raise HTTPException(
            status_code=(
                status.HTTP_422_UNPROCESSABLE_CONTENT
            ),
            detail=str(
                exc
            ),
        ) from exc

    except Exception as exc:
        db.rollback()

        logger.exception(
            "Transcription failed "
            "for meeting %s.",
            meeting_id,
        )

        meeting = db.get(
            Meeting,
            meeting_id,
        )

        if meeting is not None:
            meeting.status = (
                MeetingStatus.FAILED
            )

            meeting.error_message = (
                "Transcription failed."
            )

            db.commit()

        raise HTTPException(
            status_code=(
                status.HTTP_500_INTERNAL_SERVER_ERROR
            ),
            detail=(
                "The meeting could "
                "not be transcribed."
            ),
        ) from exc


@router.post(
    "/{meeting_id}/diarize",
    response_model=DiarizationResponse,
)
def diarize_meeting(
    meeting_id: int,
    db: Session = Depends(
        get_db
    ),
) -> DiarizationResponse:
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

    if not meeting.normalized_audio_path:
        raise HTTPException(
            status_code=(
                status.HTTP_409_CONFLICT
            ),
            detail=(
                "The meeting audio has "
                "not been processed yet."
            ),
        )

    transcript_segments = list(
        db.scalars(
            select(
                TranscriptSegment
            )
            .where(
                TranscriptSegment.meeting_id
                == meeting_id
            )
            .order_by(
                TranscriptSegment.start_time
            )
        ).all()
    )

    if not transcript_segments:
        raise HTTPException(
            status_code=(
                status.HTTP_409_CONFLICT
            ),
            detail=(
                "Generate the transcript "
                "before running "
                "speaker diarization."
            ),
        )

    audio_path = Path(
        meeting.normalized_audio_path
    )

    if not audio_path.exists():
        raise HTTPException(
            status_code=(
                status.HTTP_409_CONFLICT
            ),
            detail=(
                "The normalized meeting "
                "audio could not be found."
            ),
        )

    meeting.status = (
        MeetingStatus.DIARIZING
    )

    meeting.error_message = None

    db.commit()

    db.refresh(
        meeting
    )

    try:
        diarization_result = (
            diarize_audio(
                audio_path
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

        for transcript_segment in (
            transcript_segments
        ):
            transcript_segment.speaker_id = (
                None
            )

        db.flush()

        speakers_by_label: dict[
            str,
            Speaker,
        ] = {}

        for label in (
            diarization_result.speaker_labels
        ):
            speaker = Speaker(
                meeting_id=(
                    meeting_id
                ),
                speaker_label=(
                    label
                ),
                display_name=None,
            )

            db.add(
                speaker
            )

            db.flush()

            speakers_by_label[
                label
            ] = speaker

        assigned_count = 0

        unassigned_count = 0

        for transcript_segment in (
            transcript_segments
        ):
            best_label = (
                find_best_speaker_label(
                    segment_start=(
                        transcript_segment.start_time
                    ),
                    segment_end=(
                        transcript_segment.end_time
                    ),
                    speaker_turns=(
                        diarization_result.turns
                    ),
                )
            )

            if best_label is None:
                unassigned_count += 1

                continue

            speaker = (
                speakers_by_label.get(
                    best_label
                )
            )

            if speaker is None:
                unassigned_count += 1

                continue

            transcript_segment.speaker_id = (
                speaker.id
            )

            assigned_count += 1

        meeting.status = (
            MeetingStatus.UPLOADED
        )

        meeting.error_message = None

        db.commit()

        saved_speakers = list(
            db.scalars(
                select(
                    Speaker
                )
                .where(
                    Speaker.meeting_id
                    == meeting_id
                )
                .order_by(
                    Speaker.id
                )
            ).all()
        )

        return DiarizationResponse(
            meeting_id=meeting_id,
            speaker_count=len(
                saved_speakers
            ),
            assigned_segment_count=(
                assigned_count
            ),
            unassigned_segment_count=(
                unassigned_count
            ),
            speakers=[
                SpeakerResponse.model_validate(
                    speaker
                )
                for speaker in saved_speakers
            ],
            message=(
                "Speaker diarization "
                "completed successfully."
            ),
        )

    except (
        FileNotFoundError,
        ValueError,
        RuntimeError,
    ) as exc:
        db.rollback()

        logger.exception(
            "Speaker diarization unavailable "
            "for meeting %s.",
            meeting_id,
        )

        meeting = db.get(
            Meeting,
            meeting_id,
        )

        if meeting is not None:
            meeting.status = (
                MeetingStatus.UPLOADED
            )

            meeting.error_message = (
                "Speaker diarization "
                f"unavailable: {exc}"
            )

            db.commit()

        raise HTTPException(
            status_code=(
                status.HTTP_422_UNPROCESSABLE_CONTENT
            ),
            detail=(
                "Speaker diarization could "
                "not be completed. "
                "The transcript remains "
                "available without "
                "speaker labels."
            ),
        ) from exc

    except Exception as exc:
        db.rollback()

        logger.exception(
            "Unexpected speaker diarization "
            "failure for meeting %s.",
            meeting_id,
        )

        meeting = db.get(
            Meeting,
            meeting_id,
        )

        if meeting is not None:
            meeting.status = (
                MeetingStatus.UPLOADED
            )

            meeting.error_message = (
                "Speaker diarization failed."
            )

            db.commit()

        raise HTTPException(
            status_code=(
                status.HTTP_500_INTERNAL_SERVER_ERROR
            ),
            detail=(
                "Speaker diarization failed. "
                "The transcript remains available."
            ),
        ) from exc


@router.get(
    "/{meeting_id}/transcript",
    response_model=MeetingTranscriptResponse,
)
def get_meeting_transcript(
    meeting_id: int,
    db: Session = Depends(
        get_db
    ),
) -> MeetingTranscriptResponse:
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

    transcript_segments = list(
        db.scalars(
            select(
                TranscriptSegment
            )
            .where(
                TranscriptSegment.meeting_id
                == meeting_id
            )
            .order_by(
                TranscriptSegment.start_time
            )
        ).all()
    )

    if not transcript_segments:
        raise HTTPException(
            status_code=(
                status.HTTP_404_NOT_FOUND
            ),
            detail=(
                "No transcript has been "
                "generated for this "
                "meeting yet."
            ),
        )

    speakers = list(
        db.scalars(
            select(
                Speaker
            )
            .where(
                Speaker.meeting_id
                == meeting_id
            )
        ).all()
    )

    speakers_by_id = {
        speaker.id: speaker
        for speaker in speakers
    }

    response_segments: list[
        TranscriptSegmentResponse
    ] = []

    for segment in (
        transcript_segments
    ):
        speaker = None

        if segment.speaker_id:
            speaker = (
                speakers_by_id.get(
                    segment.speaker_id
                )
            )

        response_segments.append(
            TranscriptSegmentResponse(
                id=segment.id,
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
                speaker_label=(
                    speaker.speaker_label
                    if speaker
                    else None
                ),
                speaker_display_name=(
                    speaker.display_name
                    if speaker
                    else None
                ),
            )
        )

    return MeetingTranscriptResponse(
        meeting_id=meeting.id,
        title=meeting.title,
        language=meeting.language,
        duration=meeting.duration,
        segment_count=len(
            response_segments
        ),
        segments=response_segments,
    )