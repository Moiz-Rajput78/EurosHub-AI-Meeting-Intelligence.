from sqlalchemy import Float, ForeignKey, Integer, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class TranscriptSegment(Base):
    __tablename__ = "transcript_segments"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        index=True,
    )

    meeting_id: Mapped[int] = mapped_column(
        ForeignKey(
            "meetings.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    speaker_id: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        index=True,
    )

    start_time: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )

    end_time: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )

    original_text: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    edited_text: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    def __repr__(self) -> str:
        return (
            f"<TranscriptSegment("
            f"id={self.id}, "
            f"meeting_id={self.meeting_id}, "
            f"start_time={self.start_time}, "
            f"end_time={self.end_time}"
            f")>"
        )