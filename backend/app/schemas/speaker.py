from pydantic import BaseModel, ConfigDict, Field


class SpeakerResponse(BaseModel):
    model_config = ConfigDict(
        from_attributes=True
    )

    id: int
    speaker_label: str
    display_name: str | None


class SpeakerUpdateRequest(BaseModel):
    display_name: str = Field(
        min_length=1,
        max_length=255,
    )


class SpeakerUpdateResponse(BaseModel):
    id: int
    meeting_id: int
    speaker_label: str
    display_name: str | None
    message: str


class MeetingSpeakersResponse(BaseModel):
    meeting_id: int
    speaker_count: int
    speakers: list[SpeakerResponse]


class DiarizationResponse(BaseModel):
    meeting_id: int
    speaker_count: int
    assigned_segment_count: int
    unassigned_segment_count: int
    speakers: list[SpeakerResponse]
    message: str