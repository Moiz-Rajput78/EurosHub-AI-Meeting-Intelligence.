import json
from datetime import datetime

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class MeetingAnalysis(Base):
    __tablename__ = "meeting_analyses"

    __table_args__ = (
        UniqueConstraint(
            "meeting_id",
            name="uq_meeting_analysis_meeting_id",
        ),
    )

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

    summary: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    key_discussion_points_json: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        default="[]",
    )

    important_dates_json: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        default="[]",
    )

    unanswered_questions_json: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        default="[]",
    )

    announcements_json: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        default="[]",
    )

    topics_json: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        default="[]",
    )

    model_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )

    @property
    def key_discussion_points(self) -> list[str]:
        return json.loads(
            self.key_discussion_points_json
        )

    @property
    def important_dates(self) -> list[dict]:
        return json.loads(
            self.important_dates_json
        )

    @property
    def unanswered_questions(self) -> list[dict]:
        return json.loads(
            self.unanswered_questions_json
        )

    @property
    def announcements(self) -> list[dict]:
        return json.loads(
            self.announcements_json
        )

    @property
    def topics(self) -> list[str]:
        return json.loads(
            self.topics_json
        )


class Decision(Base):
    __tablename__ = "decisions"

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

    decision_text: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    evidence_text: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )


class ActionItem(Base):
    __tablename__ = "action_items"

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

    task: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    responsible_person: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    deadline: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    priority: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="NOT_SPECIFIED",
    )

    topic: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    evidence_text: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )


class OpenIssue(Base):
    __tablename__ = "open_issues"

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

    issue_text: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    evidence_text: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )


class MeetingRequirement(Base):
    __tablename__ = "meeting_requirements"

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

    requirement_text: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    evidence_text: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )