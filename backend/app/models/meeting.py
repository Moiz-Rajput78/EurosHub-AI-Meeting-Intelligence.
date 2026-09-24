import enum
from datetime import datetime

from sqlalchemy import DateTime, Enum, Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class MeetingStatus(str, enum.Enum):
    UPLOADED = "UPLOADED"
    PROCESSING_AUDIO = "PROCESSING_AUDIO"
    TRANSCRIBING = "TRANSCRIBING"
    DIARIZING = "DIARIZING"
    GENERATING_NOTES = "GENERATING_NOTES"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class Meeting(Base):
    __tablename__ = "meetings"

    id: Mapped[int] = mapped_column(
        primary_key=True,
        index=True,
    )

    title: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    original_filename: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
    )

    stored_filename: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )

    file_path: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    normalized_audio_path: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    duration: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )

    language: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )

    status: Mapped[MeetingStatus] = mapped_column(
        Enum(MeetingStatus),
        default=MeetingStatus.UPLOADED,
        nullable=False,
        index=True,
    )

    progress_percent: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )

    error_message: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
        index=True,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )

    def __repr__(self) -> str:
        return (
            f"<Meeting("
            f"id={self.id}, "
            f"title='{self.title}', "
            f"status='{self.status.value}', "
            f"progress={self.progress_percent}%"
            f")>"
        )
