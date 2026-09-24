from datetime import datetime

from pydantic import (
    BaseModel,
    Field,
)


class MeetingListItemResponse(BaseModel):
    id: int
    title: str
    original_filename: str

    status: str
    progress_percent: int

    duration: float | None
    language: str | None

    transcript_segment_count: int
    speaker_count: int

    created_at: datetime
    updated_at: datetime


class MeetingListResponse(BaseModel):
    count: int

    meetings: list[
        MeetingListItemResponse
    ]


class MeetingDetailResponse(BaseModel):
    id: int

    title: str

    original_filename: str
    stored_filename: str | None

    status: str
    progress_percent: int

    duration: float | None
    language: str | None

    transcript_segment_count: int
    speaker_count: int

    has_transcript: bool
    has_speakers: bool
    has_notes: bool

    error_message: str | None

    created_at: datetime
    updated_at: datetime


class MeetingStatusResponse(BaseModel):
    meeting_id: int

    status: str
    progress_percent: int

    error_message: str | None

    has_transcript: bool
    has_speakers: bool
    has_notes: bool

    transcript_segment_count: int

    message: str


class MeetingDeleteResponse(BaseModel):
    meeting_id: int

    deleted: bool

    message: str


class TranscriptSegmentUpdateRequest(
    BaseModel
):
    text: str = Field(
        min_length=1,
        max_length=10000,
    )


class TranscriptSegmentUpdateResponse(
    BaseModel
):
    id: int

    meeting_id: int

    start_time: float
    end_time: float

    original_text: str

    edited_text: str

    speaker_id: int | None

    notes_invalidated: bool

    message: str
