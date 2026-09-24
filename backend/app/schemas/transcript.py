from pydantic import BaseModel


class TranscriptSegmentResponse(BaseModel):
    id: int

    start_time: float
    end_time: float

    original_text: str
    edited_text: str | None

    speaker_id: int | None
    speaker_label: str | None
    speaker_display_name: str | None


class MeetingTranscriptResponse(BaseModel):
    meeting_id: int

    title: str

    language: str | None

    duration: float | None

    segment_count: int

    segments: list[
        TranscriptSegmentResponse
    ]


class TranscriptionResponse(BaseModel):
    meeting_id: int

    title: str

    language: str | None

    duration: float | None

    segment_count: int

    status: str

    message: str