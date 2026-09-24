from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.meeting import MeetingStatus


class MeetingUploadResponse(BaseModel):
    model_config = ConfigDict(
        from_attributes=True
    )

    id: int
    title: str
    original_filename: str
    stored_filename: str | None
    status: MeetingStatus
    progress_percent: int
    created_at: datetime

    message: str = "Meeting uploaded successfully"


class MeetingProcessingResponse(BaseModel):
    id: int
    title: str
    status: MeetingStatus
    progress_percent: int
    duration: float | None

    message: str
