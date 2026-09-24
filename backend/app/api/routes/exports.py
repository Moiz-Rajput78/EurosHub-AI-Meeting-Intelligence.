import io
import re
from datetime import datetime
from typing import Any

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Query,
    status,
)
from fastapi.responses import StreamingResponse
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import (
    ParagraphStyle,
    getSampleStyleSheet,
)
from reportlab.lib.units import mm
from reportlab.platypus import (
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
)
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.analysis import (
    ActionItem,
    Decision,
    MeetingAnalysis,
    MeetingRequirement,
    OpenIssue,
)
from app.models.meeting import Meeting
from app.models.speaker import Speaker
from app.models.transcript import TranscriptSegment


router = APIRouter(
    prefix="/meetings",
    tags=["Meeting Export"],
)


SUPPORTED_FORMATS = {
    "txt",
    "md",
    "pdf",
}


def _format_timestamp(
    seconds: float,
) -> str:
    total_seconds = max(
        0,
        int(seconds),
    )

    hours = (
        total_seconds // 3600
    )

    minutes = (
        total_seconds % 3600
    ) // 60

    secs = (
        total_seconds % 60
    )

    if hours > 0:
        return (
            f"{hours:02d}:"
            f"{minutes:02d}:"
            f"{secs:02d}"
        )

    return (
        f"{minutes:02d}:"
        f"{secs:02d}"
    )


def _format_duration(
    seconds: float | None,
) -> str:
    if seconds is None:
        return "Not available"

    return _format_timestamp(
        seconds
    )


def _format_datetime(
    value: datetime,
) -> str:
    return value.strftime(
        "%Y-%m-%d %H:%M"
    )


def _safe_filename(
    title: str,
) -> str:
    cleaned = re.sub(
        r"[^a-zA-Z0-9_-]+",
        "_",
        title.strip(),
    )

    cleaned = cleaned.strip(
        "_"
    )

    if not cleaned:
        cleaned = "meeting"

    return cleaned[:100]


def _escape_pdf_text(
    value: str,
) -> str:
    return (
        value
        .replace(
            "&",
            "&amp;",
        )
        .replace(
            "<",
            "&lt;",
        )
        .replace(
            ">",
            "&gt;",
        )
    )


def _load_export_data(
    db: Session,
    meeting_id: int,
) -> dict[str, Any]:
    meeting = db.get(
        Meeting,
        meeting_id,
    )

    if meeting is None:
        raise HTTPException(
            status_code=(
                status.HTTP_404_NOT_FOUND
            ),
            detail="Meeting not found.",
        )

    speakers = list(
        db.scalars(
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
        ).all()
    )

    segments = list(
        db.scalars(
            select(
                TranscriptSegment
            )
            .where(
                TranscriptSegment.meeting_id
                == meeting_id
            )
            .order_by(
                TranscriptSegment.start_time
            )
        ).all()
    )

    analysis = db.scalar(
        select(
            MeetingAnalysis
        )
        .where(
            MeetingAnalysis.meeting_id
            == meeting_id
        )
    )

    decisions = list(
        db.scalars(
            select(
                Decision
            )
            .where(
                Decision.meeting_id
                == meeting_id
            )
            .order_by(
                Decision.id
            )
        ).all()
    )

    action_items = list(
        db.scalars(
            select(
                ActionItem
            )
            .where(
                ActionItem.meeting_id
                == meeting_id
            )
            .order_by(
                ActionItem.id
            )
        ).all()
    )

    open_issues = list(
        db.scalars(
            select(
                OpenIssue
            )
            .where(
                OpenIssue.meeting_id
                == meeting_id
            )
            .order_by(
                OpenIssue.id
            )
        ).all()
    )

    requirements = list(
        db.scalars(
            select(
                MeetingRequirement
            )
            .where(
                MeetingRequirement.meeting_id
                == meeting_id
            )
            .order_by(
                MeetingRequirement.id
            )
        ).all()
    )

    speakers_by_id = {
        speaker.id: speaker
        for speaker in speakers
    }

    transcript = []

    for segment in segments:
        speaker_name = (
            "Unknown Speaker"
        )

        if segment.speaker_id:
            speaker = (
                speakers_by_id.get(
                    segment.speaker_id
                )
            )

            if speaker is not None:
                speaker_name = (
                    speaker.display_name
                    or speaker.speaker_label
                )

        text = (
            segment.edited_text
            if (
                segment.edited_text
                and segment.edited_text.strip()
            )
            else segment.original_text
        )

        transcript.append(
            {
                "start_time": (
                    segment.start_time
                ),
                "end_time": (
                    segment.end_time
                ),
                "speaker": (
                    speaker_name
                ),
                "text": (
                    text.strip()
                ),
            }
        )

    return {
        "meeting": meeting,
        "speakers": speakers,
        "transcript": transcript,
        "analysis": analysis,
        "decisions": decisions,
        "action_items": action_items,
        "open_issues": open_issues,
        "requirements": requirements,
    }


def _build_text_export(
    data: dict[str, Any],
) -> str:
    meeting = data[
        "meeting"
    ]

    analysis = data[
        "analysis"
    ]

    lines: list[str] = [
        meeting.title,
        "=" * len(
            meeting.title
        ),
        "",
        (
            "Original file: "
            f"{meeting.original_filename}"
        ),
        (
            "Created: "
            f"{_format_datetime(meeting.created_at)}"
        ),
        (
            "Duration: "
            f"{_format_duration(meeting.duration)}"
        ),
        (
            "Language: "
            f"{meeting.language or 'Not available'}"
        ),
        "",
    ]

    if analysis:
        lines.extend(
            [
                "SUMMARY",
                "-------",
                analysis.summary,
                "",
                "KEY DISCUSSION POINTS",
                "---------------------",
            ]
        )

        if (
            analysis
            .key_discussion_points
        ):
            for item in (
                analysis
                .key_discussion_points
            ):
                lines.append(
                    f"- {item}"
                )
        else:
            lines.append(
                "None extracted."
            )

        lines.extend(
            [
                "",
                "DECISIONS",
                "---------",
            ]
        )

        if data["decisions"]:
            for item in data[
                "decisions"
            ]:
                lines.append(
                    f"- {item.decision_text}"
                )

                lines.append(
                    "  Evidence: "
                    f"{item.evidence_text}"
                )
        else:
            lines.append(
                "No confirmed decisions."
            )

        lines.extend(
            [
                "",
                "ACTION ITEMS",
                "------------",
            ]
        )

        if data[
            "action_items"
        ]:
            for item in data[
                "action_items"
            ]:
                lines.append(
                    f"- {item.task}"
                )

                lines.append(
                    "  Responsible: "
                    f"{item.responsible_person or 'Not specified'}"
                )

                lines.append(
                    "  Deadline: "
                    f"{item.deadline or 'Not mentioned'}"
                )

                lines.append(
                    "  Priority: "
                    f"{item.priority}"
                )

                if item.topic:
                    lines.append(
                        "  Topic: "
                        f"{item.topic}"
                    )

                lines.append(
                    "  Evidence: "
                    f"{item.evidence_text}"
                )
        else:
            lines.append(
                "No action items."
            )

        lines.extend(
            [
                "",
                "IMPORTANT DATES",
                "---------------",
            ]
        )

        important_dates = (
            analysis
            .important_dates
        )

        if important_dates:
            for item in (
                important_dates
            ):
                lines.append(
                    "- "
                    f"{item.get('date_or_time', '')}: "
                    f"{item.get('description', '')}"
                )
        else:
            lines.append(
                "No important dates."
            )

        lines.extend(
            [
                "",
                "OPEN ISSUES",
                "-----------",
            ]
        )

        if data[
            "open_issues"
        ]:
            for item in data[
                "open_issues"
            ]:
                lines.append(
                    f"- {item.issue_text}"
                )

                lines.append(
                    "  Evidence: "
                    f"{item.evidence_text}"
                )
        else:
            lines.append(
                "No open issues."
            )

        lines.extend(
            [
                "",
                "UNANSWERED QUESTIONS",
                "--------------------",
            ]
        )

        questions = (
            analysis
            .unanswered_questions
        )

        if questions:
            for item in questions:
                lines.append(
                    "- "
                    f"{item.get('question', '')}"
                )
        else:
            lines.append(
                "No unanswered questions."
            )

        lines.extend(
            [
                "",
                "REQUIREMENTS",
                "------------",
            ]
        )

        if data[
            "requirements"
        ]:
            for item in data[
                "requirements"
            ]:
                lines.append(
                    "- "
                    f"{item.requirement_text}"
                )
        else:
            lines.append(
                "No requirements extracted."
            )

        lines.extend(
            [
                "",
                "ANNOUNCEMENTS",
                "-------------",
            ]
        )

        announcements = (
            analysis.announcements
        )

        if announcements:
            for item in (
                announcements
            ):
                lines.append(
                    "- "
                    f"{item.get('announcement', '')}"
                )
        else:
            lines.append(
                "No announcements."
            )

        lines.extend(
            [
                "",
                "TOPICS",
                "------",
            ]
        )

        if analysis.topics:
            lines.append(
                ", ".join(
                    analysis.topics
                )
            )
        else:
            lines.append(
                "No topics extracted."
            )

        lines.append(
            ""
        )

    lines.extend(
        [
            "SPEAKERS",
            "--------",
        ]
    )

    if data["speakers"]:
        for speaker in data[
            "speakers"
        ]:
            display = (
                speaker.display_name
                or speaker.speaker_label
            )

            if speaker.display_name:
                lines.append(
                    "- "
                    f"{display} "
                    f"({speaker.speaker_label})"
                )
            else:
                lines.append(
                    f"- {display}"
                )
    else:
        lines.append(
            "No speakers detected."
        )

    lines.extend(
        [
            "",
            "FULL TRANSCRIPT",
            "---------------",
        ]
    )

    if data[
        "transcript"
    ]:
        for segment in data[
            "transcript"
        ]:
            timestamp = (
                _format_timestamp(
                    segment[
                        "start_time"
                    ]
                )
            )

            lines.append(
                f"[{timestamp}] "
                f"{segment['speaker']}: "
                f"{segment['text']}"
            )
    else:
        lines.append(
            "No transcript available."
        )

    lines.append(
        ""
    )

    return "\n".join(
        lines
    )


def _build_markdown_export(
    data: dict[str, Any],
) -> str:
    meeting = data[
        "meeting"
    ]

    analysis = data[
        "analysis"
    ]

    lines = [
        f"# {meeting.title}",
        "",
        (
            f"**Original file:** "
            f"{meeting.original_filename}"
        ),
        (
            f"**Created:** "
            f"{_format_datetime(meeting.created_at)}"
        ),
        (
            f"**Duration:** "
            f"{_format_duration(meeting.duration)}"
        ),
        (
            f"**Language:** "
            f"{meeting.language or 'Not available'}"
        ),
        "",
    ]

    if analysis:
        lines.extend(
            [
                "## Summary",
                "",
                analysis.summary,
                "",
                "## Key Discussion Points",
                "",
            ]
        )

        for item in (
            analysis
            .key_discussion_points
        ):
            lines.append(
                f"- {item}"
            )

        if not (
            analysis
            .key_discussion_points
        ):
            lines.append(
                "_None extracted._"
            )

        lines.extend(
            [
                "",
                "## Decisions",
                "",
            ]
        )

        for item in data[
            "decisions"
        ]:
            lines.append(
                f"- {item.decision_text}"
            )

            lines.append(
                "  - **Evidence:** "
                f"{item.evidence_text}"
            )

        if not data[
            "decisions"
        ]:
            lines.append(
                "_No confirmed decisions._"
            )

        lines.extend(
            [
                "",
                "## Action Items",
                "",
            ]
        )

        for item in data[
            "action_items"
        ]:
            lines.extend(
                [
                    f"### {item.task}",
                    "",
                    (
                        "- **Responsible:** "
                        f"{item.responsible_person or 'Not specified'}"
                    ),
                    (
                        "- **Deadline:** "
                        f"{item.deadline or 'Not mentioned'}"
                    ),
                    (
                        "- **Priority:** "
                        f"{item.priority}"
                    ),
                ]
            )

            if item.topic:
                lines.append(
                    "- **Topic:** "
                    f"{item.topic}"
                )

            lines.extend(
                [
                    (
                        "- **Evidence:** "
                        f"{item.evidence_text}"
                    ),
                    "",
                ]
            )

        if not data[
            "action_items"
        ]:
            lines.append(
                "_No action items._"
            )

        lines.extend(
            [
                "",
                "## Important Dates",
                "",
            ]
        )

        for item in (
            analysis
            .important_dates
        ):
            lines.append(
                "- **"
                f"{item.get('date_or_time', '')}"
                "** — "
                f"{item.get('description', '')}"
            )

        if not (
            analysis
            .important_dates
        ):
            lines.append(
                "_No important dates._"
            )

        lines.extend(
            [
                "",
                "## Open Issues",
                "",
            ]
        )

        for item in data[
            "open_issues"
        ]:
            lines.append(
                f"- {item.issue_text}"
            )

        if not data[
            "open_issues"
        ]:
            lines.append(
                "_No open issues._"
            )

        lines.extend(
            [
                "",
                "## Unanswered Questions",
                "",
            ]
        )

        for item in (
            analysis
            .unanswered_questions
        ):
            lines.append(
                "- "
                f"{item.get('question', '')}"
            )

        if not (
            analysis
            .unanswered_questions
        ):
            lines.append(
                "_No unanswered questions._"
            )

        lines.extend(
            [
                "",
                "## Requirements",
                "",
            ]
        )

        for item in data[
            "requirements"
        ]:
            lines.append(
                "- "
                f"{item.requirement_text}"
            )

        if not data[
            "requirements"
        ]:
            lines.append(
                "_No requirements extracted._"
            )

        lines.extend(
            [
                "",
                "## Announcements",
                "",
            ]
        )

        for item in (
            analysis
            .announcements
        ):
            lines.append(
                "- "
                f"{item.get('announcement', '')}"
            )

        if not (
            analysis
            .announcements
        ):
            lines.append(
                "_No announcements._"
            )

        lines.extend(
            [
                "",
                "## Topics",
                "",
            ]
        )

        if analysis.topics:
            lines.append(
                ", ".join(
                    f"`{topic}`"
                    for topic in (
                        analysis.topics
                    )
                )
            )
        else:
            lines.append(
                "_No topics extracted._"
            )

    lines.extend(
        [
            "",
            "## Speakers",
            "",
        ]
    )

    for speaker in data[
        "speakers"
    ]:
        if speaker.display_name:
            lines.append(
                "- "
                f"**{speaker.display_name}** "
                f"({speaker.speaker_label})"
            )
        else:
            lines.append(
                "- "
                f"{speaker.speaker_label}"
            )

    if not data[
        "speakers"
    ]:
        lines.append(
            "_No speakers detected._"
        )

    lines.extend(
        [
            "",
            "## Full Transcript",
            "",
        ]
    )

    for segment in data[
        "transcript"
    ]:
        timestamp = (
            _format_timestamp(
                segment[
                    "start_time"
                ]
            )
        )

        lines.append(
            f"**[{timestamp}] "
            f"{segment['speaker']}**  "
        )

        lines.append(
            segment["text"]
        )

        lines.append(
            ""
        )

    if not data[
        "transcript"
    ]:
        lines.append(
            "_No transcript available._"
        )

    return "\n".join(
        lines
    )


def _build_pdf_export(
    data: dict[str, Any],
) -> bytes:
    buffer = io.BytesIO()

    meeting = data[
        "meeting"
    ]

    analysis = data[
        "analysis"
    ]

    document = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=18 * mm,
        leftMargin=18 * mm,
        topMargin=18 * mm,
        bottomMargin=18 * mm,
        title=meeting.title,
        author="Meeting Intelligence",
    )

    styles = (
        getSampleStyleSheet()
    )

    title_style = (
        styles["Title"]
    )

    heading_style = (
        styles["Heading2"]
    )

    subheading_style = (
        styles["Heading3"]
    )

    body_style = ParagraphStyle(
        "MeetingBody",
        parent=styles["BodyText"],
        fontSize=9.5,
        leading=14,
        spaceAfter=6,
        alignment=TA_LEFT,
    )

    meta_style = ParagraphStyle(
        "MeetingMeta",
        parent=styles["BodyText"],
        fontSize=8.5,
        leading=12,
        textColor="#555555",
        spaceAfter=4,
    )

    transcript_style = (
        ParagraphStyle(
            "Transcript",
            parent=styles["BodyText"],
            fontSize=8.5,
            leading=12,
            spaceAfter=7,
        )
    )

    story: list[Any] = []

    story.append(
        Paragraph(
            _escape_pdf_text(
                meeting.title
            ),
            title_style,
        )
    )

    story.append(
        Spacer(
            1,
            5 * mm,
        )
    )

    metadata = [
        (
            "Original file",
            meeting.original_filename,
        ),
        (
            "Created",
            _format_datetime(
                meeting.created_at
            ),
        ),
        (
            "Duration",
            _format_duration(
                meeting.duration
            ),
        ),
        (
            "Language",
            meeting.language
            or "Not available",
        ),
    ]

    for label, value in metadata:
        story.append(
            Paragraph(
                (
                    f"<b>{label}:</b> "
                    f"{_escape_pdf_text(str(value))}"
                ),
                meta_style,
            )
        )

    story.append(
        Spacer(
            1,
            5 * mm,
        )
    )

    if analysis:
        story.append(
            Paragraph(
                "Summary",
                heading_style,
            )
        )

        story.append(
            Paragraph(
                _escape_pdf_text(
                    analysis.summary
                ),
                body_style,
            )
        )

        story.append(
            Paragraph(
                "Key Discussion Points",
                heading_style,
            )
        )

        if (
            analysis
            .key_discussion_points
        ):
            for item in (
                analysis
                .key_discussion_points
            ):
                story.append(
                    Paragraph(
                        "• "
                        + _escape_pdf_text(
                            item
                        ),
                        body_style,
                    )
                )
        else:
            story.append(
                Paragraph(
                    "None extracted.",
                    body_style,
                )
            )

        story.append(
            Paragraph(
                "Decisions",
                heading_style,
            )
        )

        if data["decisions"]:
            for item in data[
                "decisions"
            ]:
                story.append(
                    Paragraph(
                        "• "
                        + _escape_pdf_text(
                            item
                            .decision_text
                        ),
                        body_style,
                    )
                )

                story.append(
                    Paragraph(
                        (
                            "<i>Evidence:</i> "
                            + _escape_pdf_text(
                                item
                                .evidence_text
                            )
                        ),
                        meta_style,
                    )
                )
        else:
            story.append(
                Paragraph(
                    "No confirmed decisions.",
                    body_style,
                )
            )

        story.append(
            Paragraph(
                "Action Items",
                heading_style,
            )
        )

        if data[
            "action_items"
        ]:
            for item in data[
                "action_items"
            ]:
                story.append(
                    Paragraph(
                        _escape_pdf_text(
                            item.task
                        ),
                        subheading_style,
                    )
                )

                details = [
                    (
                        "Responsible",
                        item.responsible_person
                        or "Not specified",
                    ),
                    (
                        "Deadline",
                        item.deadline
                        or "Not mentioned",
                    ),
                    (
                        "Priority",
                        item.priority,
                    ),
                ]

                if item.topic:
                    details.append(
                        (
                            "Topic",
                            item.topic,
                        )
                    )

                for (
                    label,
                    value,
                ) in details:
                    story.append(
                        Paragraph(
                            (
                                f"<b>{label}:</b> "
                                + _escape_pdf_text(
                                    str(value)
                                )
                            ),
                            body_style,
                        )
                    )

                story.append(
                    Paragraph(
                        (
                            "<i>Evidence:</i> "
                            + _escape_pdf_text(
                                item
                                .evidence_text
                            )
                        ),
                        meta_style,
                    )
                )

                story.append(
                    Spacer(
                        1,
                        2 * mm,
                    )
                )
        else:
            story.append(
                Paragraph(
                    "No action items.",
                    body_style,
                )
            )

        story.append(
            Paragraph(
                "Important Dates",
                heading_style,
            )
        )

        if (
            analysis
            .important_dates
        ):
            for item in (
                analysis
                .important_dates
            ):
                text = (
                    f"{item.get('date_or_time', '')}: "
                    f"{item.get('description', '')}"
                )

                story.append(
                    Paragraph(
                        "• "
                        + _escape_pdf_text(
                            text
                        ),
                        body_style,
                    )
                )
        else:
            story.append(
                Paragraph(
                    "No important dates.",
                    body_style,
                )
            )

        story.append(
            Paragraph(
                "Open Issues",
                heading_style,
            )
        )

        if data[
            "open_issues"
        ]:
            for item in data[
                "open_issues"
            ]:
                story.append(
                    Paragraph(
                        "• "
                        + _escape_pdf_text(
                            item.issue_text
                        ),
                        body_style,
                    )
                )
        else:
            story.append(
                Paragraph(
                    "No open issues.",
                    body_style,
                )
            )

        story.append(
            Paragraph(
                "Unanswered Questions",
                heading_style,
            )
        )

        if (
            analysis
            .unanswered_questions
        ):
            for item in (
                analysis
                .unanswered_questions
            ):
                story.append(
                    Paragraph(
                        "• "
                        + _escape_pdf_text(
                            item.get(
                                "question",
                                "",
                            )
                        ),
                        body_style,
                    )
                )
        else:
            story.append(
                Paragraph(
                    "No unanswered questions.",
                    body_style,
                )
            )

        story.append(
            Paragraph(
                "Requirements",
                heading_style,
            )
        )

        if data[
            "requirements"
        ]:
            for item in data[
                "requirements"
            ]:
                story.append(
                    Paragraph(
                        "• "
                        + _escape_pdf_text(
                            item
                            .requirement_text
                        ),
                        body_style,
                    )
                )
        else:
            story.append(
                Paragraph(
                    "No requirements extracted.",
                    body_style,
                )
            )

        story.append(
            Paragraph(
                "Announcements",
                heading_style,
            )
        )

        if (
            analysis
            .announcements
        ):
            for item in (
                analysis
                .announcements
            ):
                story.append(
                    Paragraph(
                        "• "
                        + _escape_pdf_text(
                            item.get(
                                "announcement",
                                "",
                            )
                        ),
                        body_style,
                    )
                )
        else:
            story.append(
                Paragraph(
                    "No announcements.",
                    body_style,
                )
            )

        story.append(
            Paragraph(
                "Topics",
                heading_style,
            )
        )

        story.append(
            Paragraph(
                _escape_pdf_text(
                    ", ".join(
                        analysis.topics
                    )
                    if analysis.topics
                    else "No topics extracted."
                ),
                body_style,
            )
        )

    story.append(
        Paragraph(
            "Speakers",
            heading_style,
        )
    )

    if data["speakers"]:
        for speaker in data[
            "speakers"
        ]:
            if (
                speaker.display_name
            ):
                text = (
                    f"{speaker.display_name} "
                    f"({speaker.speaker_label})"
                )
            else:
                text = (
                    speaker.speaker_label
                )

            story.append(
                Paragraph(
                    "• "
                    + _escape_pdf_text(
                        text
                    ),
                    body_style,
                )
            )
    else:
        story.append(
            Paragraph(
                "No speakers detected.",
                body_style,
            )
        )

    story.append(
        PageBreak()
    )

    story.append(
        Paragraph(
            "Full Transcript",
            title_style,
        )
    )

    story.append(
        Spacer(
            1,
            4 * mm,
        )
    )

    if data[
        "transcript"
    ]:
        for segment in data[
            "transcript"
        ]:
            timestamp = (
                _format_timestamp(
                    segment[
                        "start_time"
                    ]
                )
            )

            heading = (
                f"<b>[{timestamp}] "
                f"{_escape_pdf_text(segment['speaker'])}</b>"
            )

            story.append(
                Paragraph(
                    heading,
                    transcript_style,
                )
            )

            story.append(
                Paragraph(
                    _escape_pdf_text(
                        segment["text"]
                    ),
                    transcript_style,
                )
            )
    else:
        story.append(
            Paragraph(
                "No transcript available.",
                body_style,
            )
        )

    document.build(
        story
    )

    buffer.seek(
        0
    )

    return buffer.read()


@router.get(
    "/{meeting_id}/export",
)
def export_meeting(
    meeting_id: int,
    format: str = Query(
        default="pdf",
        description=(
            "Export format: txt, md, or pdf."
        ),
    ),
    db: Session = Depends(
        get_db
    ),
) -> StreamingResponse:
    export_format = (
        format
        .strip()
        .lower()
    )

    if (
        export_format
        not in SUPPORTED_FORMATS
    ):
        raise HTTPException(
            status_code=(
                status.HTTP_422_UNPROCESSABLE_CONTENT
            ),
            detail=(
                "Unsupported export format. "
                "Use txt, md, or pdf."
            ),
        )

    data = (
        _load_export_data(
            db,
            meeting_id,
        )
    )

    meeting = data[
        "meeting"
    ]

    base_filename = (
        _safe_filename(
            meeting.title
        )
    )

    if export_format == "txt":
        content = (
            _build_text_export(
                data
            )
            .encode(
                "utf-8"
            )
        )

        media_type = (
            "text/plain; charset=utf-8"
        )

        extension = "txt"

    elif export_format == "md":
        content = (
            _build_markdown_export(
                data
            )
            .encode(
                "utf-8"
            )
        )

        media_type = (
            "text/markdown; charset=utf-8"
        )

        extension = "md"

    else:
        content = (
            _build_pdf_export(
                data
            )
        )

        media_type = (
            "application/pdf"
        )

        extension = "pdf"

    filename = (
        f"{base_filename}.{extension}"
    )

    headers = {
        "Content-Disposition": (
            f'attachment; filename="{filename}"'
        ),
    }

    return StreamingResponse(
        io.BytesIO(
            content
        ),
        media_type=media_type,
        headers=headers,
    )