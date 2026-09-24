from datetime import datetime
from typing import Literal

from pydantic import (
    BaseModel,
    Field,
)


PriorityValue = Literal[
    "HIGH",
    "MEDIUM",
    "LOW",
    "NOT_SPECIFIED",
]


class DecisionExtraction(BaseModel):
    decision: str
    evidence: str


class ActionItemExtraction(BaseModel):
    task: str

    responsible_person: str | None = None

    deadline: str | None = None

    priority: PriorityValue = (
        "NOT_SPECIFIED"
    )

    topic: str | None = None

    evidence: str


class ImportantDateExtraction(BaseModel):
    date_or_time: str

    description: str

    evidence: str


class OpenIssueExtraction(BaseModel):
    issue: str

    evidence: str


class QuestionExtraction(BaseModel):
    question: str

    evidence: str


class RequirementExtraction(BaseModel):
    requirement: str

    evidence: str


class AnnouncementExtraction(BaseModel):
    announcement: str

    evidence: str


class StructuredMeetingAnalysis(BaseModel):
    summary: str

    key_discussion_points: list[str] = (
        Field(
            default_factory=list
        )
    )

    decisions: list[
        DecisionExtraction
    ] = Field(
        default_factory=list
    )

    action_items: list[
        ActionItemExtraction
    ] = Field(
        default_factory=list
    )

    important_dates: list[
        ImportantDateExtraction
    ] = Field(
        default_factory=list
    )

    open_issues: list[
        OpenIssueExtraction
    ] = Field(
        default_factory=list
    )

    unanswered_questions: list[
        QuestionExtraction
    ] = Field(
        default_factory=list
    )

    requirements: list[
        RequirementExtraction
    ] = Field(
        default_factory=list
    )

    announcements: list[
        AnnouncementExtraction
    ] = Field(
        default_factory=list
    )

    topics: list[str] = Field(
        default_factory=list
    )


class DecisionResponse(BaseModel):
    id: int
    decision: str
    evidence: str


class ActionItemResponse(BaseModel):
    id: int

    task: str

    responsible_person: str | None

    deadline: str | None

    priority: str

    topic: str | None

    evidence: str


class OpenIssueResponse(BaseModel):
    id: int

    issue: str

    evidence: str


class RequirementResponse(BaseModel):
    id: int

    requirement: str

    evidence: str


class AnalysisRunResponse(BaseModel):
    meeting_id: int

    status: str

    model: str

    transcript_segment_count: int

    transcript_chunk_count: int

    message: str


class MeetingNotesResponse(BaseModel):
    meeting_id: int

    title: str

    summary: str

    key_discussion_points: list[str]

    decisions: list[
        DecisionResponse
    ]

    action_items: list[
        ActionItemResponse
    ]

    important_dates: list[
        ImportantDateExtraction
    ]

    open_issues: list[
        OpenIssueResponse
    ]

    unanswered_questions: list[
        QuestionExtraction
    ]

    requirements: list[
        RequirementResponse
    ]

    announcements: list[
        AnnouncementExtraction
    ]

    topics: list[str]

    model_name: str

    created_at: datetime

    updated_at: datetime