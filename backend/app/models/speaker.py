from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class Speaker(Base):
    __tablename__ = "speakers"

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

    speaker_label: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    display_name: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    def __repr__(self) -> str:
        return (
            f"<Speaker("
            f"id={self.id}, "
            f"meeting_id={self.meeting_id}, "
            f"speaker_label='{self.speaker_label}'"
            f")>"
        )