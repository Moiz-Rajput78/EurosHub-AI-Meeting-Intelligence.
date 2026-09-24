from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    status,
)
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.meeting import Meeting
from app.models.speaker import Speaker
from app.schemas.speaker import (
    MeetingSpeakersResponse,
    SpeakerResponse,
    SpeakerUpdateRequest,
    SpeakerUpdateResponse,
)


router = APIRouter(
    tags=["Speakers"],
)


@router.get(
    "/meetings/{meeting_id}/speakers",
    response_model=MeetingSpeakersResponse,
)
def get_meeting_speakers(
    meeting_id: int,
    db: Session = Depends(get_db),
) -> MeetingSpeakersResponse:
    """
    Return all detected speakers for a meeting.
    """

    meeting = db.get(
        Meeting,
        meeting_id,
    )

    if meeting is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Meeting not found.",
        )

    statement = (
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
    )

    speakers = list(
        db.scalars(
            statement
        ).all()
    )

    return MeetingSpeakersResponse(
        meeting_id=meeting_id,
        speaker_count=len(
            speakers
        ),
        speakers=[
            SpeakerResponse.model_validate(
                speaker
            )
            for speaker in speakers
        ],
    )


@router.put(
    "/speakers/{speaker_id}",
    response_model=SpeakerUpdateResponse,
)
def update_speaker_name(
    speaker_id: int,
    payload: SpeakerUpdateRequest,
    db: Session = Depends(get_db),
) -> SpeakerUpdateResponse:
    """
    Rename a detected speaker.

    The original diarization label such as 'Speaker 1'
    is preserved permanently.

    Only display_name is changed.
    """

    speaker = db.get(
        Speaker,
        speaker_id,
    )

    if speaker is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Speaker not found.",
        )

    cleaned_name = (
        payload.display_name.strip()
    )

    if not cleaned_name:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=(
                "Speaker name cannot be empty."
            ),
        )

    speaker.display_name = (
        cleaned_name
    )

    db.commit()
    db.refresh(
        speaker
    )

    return SpeakerUpdateResponse(
        id=speaker.id,
        meeting_id=speaker.meeting_id,
        speaker_label=(
            speaker.speaker_label
        ),
        display_name=(
            speaker.display_name
        ),
        message=(
            "Speaker name updated successfully."
        ),
    )