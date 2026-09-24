import json
import logging

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    status,
)
from sqlalchemy import (
    delete,
    select,
)
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.models.analysis import (
    ActionItem,
    Decision,
    MeetingAnalysis,
    MeetingRequirement,
    OpenIssue,
)
from app.models.meeting import (
    Meeting,
    MeetingStatus,
)
from app.models.speaker import Speaker
from app.models.transcript import (
    TranscriptSegment,
)
from app.schemas.analysis import (
    ActionItemResponse,
    AnalysisRunResponse,
    DecisionResponse,
    MeetingNotesResponse,
    OpenIssueResponse,
    RequirementResponse,
)
from app.services.analysis_service import (
    TranscriptLine,
    analyze_transcript,
)
from app.services.ollama_service import (
    OllamaServiceError,
)


logger = logging.getLogger(
    __name__
)


router = APIRouter(
    prefix="/meetings",
    tags=["Meeting Analysis"],
)


def _build_transcript_lines(
    *,
    segments: list[TranscriptSegment],
    speakers: list[Speaker],
) -> list[TranscriptLine]:
    speakers_by_id = {
        speaker.id: speaker
        for speaker in speakers
    }

    lines: list[
        TranscriptLine
    ] = []

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

        if not text.strip():
            continue

        lines.append(
            TranscriptLine(
                start_time=(
                    segment.start_time
                ),
                end_time=(
                    segment.end_time
                ),
                speaker=(
                    speaker_name
                ),
                text=(
                    text.strip()
                ),
            )
        )

    return lines


@router.post(
    "/{meeting_id}/analyze",
    response_model=AnalysisRunResponse,
)
def analyze_meeting(
    meeting_id: int,
    db: Session = Depends(
        get_db
    ),
) -> AnalysisRunResponse:
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

    if not segments:
        raise HTTPException(
            status_code=(
                status.HTTP_409_CONFLICT
            ),
            detail=(
                "Generate the meeting "
                "transcript before running "
                "AI analysis."
            ),
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
        ).all()
    )

    transcript_lines = (
        _build_transcript_lines(
            segments=segments,
            speakers=speakers,
        )
    )

    if not transcript_lines:
        raise HTTPException(
            status_code=(
                status.HTTP_409_CONFLICT
            ),
            detail=(
                "The transcript contains "
                "no analyzable text."
            ),
        )

    meeting.status = (
        MeetingStatus.GENERATING_NOTES
    )

    meeting.error_message = None

    db.commit()

    try:
        result = analyze_transcript(
            transcript_lines
        )

        analysis = result.analysis

        existing_analysis = (
            db.scalar(
                select(
                    MeetingAnalysis
                )
                .where(
                    MeetingAnalysis.meeting_id
                    == meeting_id
                )
            )
        )

        if existing_analysis is None:
            existing_analysis = (
                MeetingAnalysis(
                    meeting_id=(
                        meeting_id
                    ),
                    summary=(
                        analysis.summary
                    ),
                    model_name=(
                        settings.ollama_model
                    ),
                )
            )

            db.add(
                existing_analysis
            )

        existing_analysis.summary = (
            analysis.summary
        )

        existing_analysis.model_name = (
            settings.ollama_model
        )

        existing_analysis.key_discussion_points_json = (
            json.dumps(
                analysis.key_discussion_points,
                ensure_ascii=False,
            )
        )

        existing_analysis.important_dates_json = (
            json.dumps(
                [
                    item.model_dump()
                    for item
                    in analysis.important_dates
                ],
                ensure_ascii=False,
            )
        )

        existing_analysis.unanswered_questions_json = (
            json.dumps(
                [
                    item.model_dump()
                    for item
                    in (
                        analysis
                        .unanswered_questions
                    )
                ],
                ensure_ascii=False,
            )
        )

        existing_analysis.announcements_json = (
            json.dumps(
                [
                    item.model_dump()
                    for item
                    in analysis.announcements
                ],
                ensure_ascii=False,
            )
        )

        existing_analysis.topics_json = (
            json.dumps(
                analysis.topics,
                ensure_ascii=False,
            )
        )

        db.execute(
            delete(
                Decision
            ).where(
                Decision.meeting_id
                == meeting_id
            )
        )

        db.execute(
            delete(
                ActionItem
            ).where(
                ActionItem.meeting_id
                == meeting_id
            )
        )

        db.execute(
            delete(
                OpenIssue
            ).where(
                OpenIssue.meeting_id
                == meeting_id
            )
        )

        db.execute(
            delete(
                MeetingRequirement
            ).where(
                MeetingRequirement.meeting_id
                == meeting_id
            )
        )

        for item in analysis.decisions:
            db.add(
                Decision(
                    meeting_id=(
                        meeting_id
                    ),
                    decision_text=(
                        item.decision
                    ),
                    evidence_text=(
                        item.evidence
                    ),
                )
            )

        for item in analysis.action_items:
            db.add(
                ActionItem(
                    meeting_id=(
                        meeting_id
                    ),
                    task=item.task,
                    responsible_person=(
                        item.responsible_person
                    ),
                    deadline=(
                        item.deadline
                    ),
                    priority=(
                        item.priority
                    ),
                    topic=(
                        item.topic
                    ),
                    evidence_text=(
                        item.evidence
                    ),
                )
            )

        for item in analysis.open_issues:
            db.add(
                OpenIssue(
                    meeting_id=(
                        meeting_id
                    ),
                    issue_text=(
                        item.issue
                    ),
                    evidence_text=(
                        item.evidence
                    ),
                )
            )

        for item in analysis.requirements:
            db.add(
                MeetingRequirement(
                    meeting_id=(
                        meeting_id
                    ),
                    requirement_text=(
                        item.requirement
                    ),
                    evidence_text=(
                        item.evidence
                    ),
                )
            )

        meeting.status = (
            MeetingStatus.COMPLETED
        )

        meeting.error_message = None

        db.commit()

        return AnalysisRunResponse(
            meeting_id=meeting_id,
            status=(
                meeting.status.value
            ),
            model=(
                settings.ollama_model
            ),
            transcript_segment_count=(
                len(segments)
            ),
            transcript_chunk_count=(
                result.chunk_count
            ),
            message=(
                "Meeting intelligence "
                "analysis completed "
                "successfully."
            ),
        )

    except (
        OllamaServiceError,
        ValueError,
    ) as exc:
        db.rollback()

        logger.exception(
            "Meeting analysis failed "
            "for meeting %s.",
            meeting_id,
        )

        meeting = db.get(
            Meeting,
            meeting_id,
        )

        if meeting is not None:
            meeting.status = (
                MeetingStatus.FAILED
            )

            meeting.error_message = (
                str(exc)
            )

            db.commit()

        raise HTTPException(
            status_code=(
                status.HTTP_502_BAD_GATEWAY
            ),
            detail=(
                "Meeting analysis could "
                "not be completed. "
                f"{exc}"
            ),
        ) from exc

    except Exception as exc:
        db.rollback()

        logger.exception(
            "Unexpected meeting analysis "
            "failure for meeting %s.",
            meeting_id,
        )

        meeting = db.get(
            Meeting,
            meeting_id,
        )

        if meeting is not None:
            meeting.status = (
                MeetingStatus.FAILED
            )

            meeting.error_message = (
                "Unexpected meeting "
                "analysis failure."
            )

            db.commit()

        raise HTTPException(
            status_code=(
                status.HTTP_500_INTERNAL_SERVER_ERROR
            ),
            detail=(
                "An unexpected error "
                "occurred while generating "
                "meeting notes."
            ),
        ) from exc


@router.get(
    "/{meeting_id}/notes",
    response_model=MeetingNotesResponse,
)
def get_meeting_notes(
    meeting_id: int,
    db: Session = Depends(
        get_db
    ),
) -> MeetingNotesResponse:
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

    analysis = db.scalar(
        select(
            MeetingAnalysis
        )
        .where(
            MeetingAnalysis.meeting_id
            == meeting_id
        )
    )

    if analysis is None:
        raise HTTPException(
            status_code=(
                status.HTTP_404_NOT_FOUND
            ),
            detail=(
                "Meeting notes have "
                "not been generated yet."
            ),
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

    return MeetingNotesResponse(
        meeting_id=meeting_id,
        title=meeting.title,
        summary=analysis.summary,
        key_discussion_points=(
            analysis
            .key_discussion_points
        ),
        decisions=[
            DecisionResponse(
                id=item.id,
                decision=(
                    item.decision_text
                ),
                evidence=(
                    item.evidence_text
                ),
            )
            for item in decisions
        ],
        action_items=[
            ActionItemResponse(
                id=item.id,
                task=item.task,
                responsible_person=(
                    item.responsible_person
                ),
                deadline=(
                    item.deadline
                ),
                priority=(
                    item.priority
                ),
                topic=(
                    item.topic
                ),
                evidence=(
                    item.evidence_text
                ),
            )
            for item in action_items
        ],
        important_dates=(
            analysis.important_dates
        ),
        open_issues=[
            OpenIssueResponse(
                id=item.id,
                issue=(
                    item.issue_text
                ),
                evidence=(
                    item.evidence_text
                ),
            )
            for item in open_issues
        ],
        unanswered_questions=(
            analysis
            .unanswered_questions
        ),
        requirements=[
            RequirementResponse(
                id=item.id,
                requirement=(
                    item.requirement_text
                ),
                evidence=(
                    item.evidence_text
                ),
            )
            for item in requirements
        ],
        announcements=(
            analysis.announcements
        ),
        topics=(
            analysis.topics
        ),
        model_name=(
            analysis.model_name
        ),
        created_at=(
            analysis.created_at
        ),
        updated_at=(
            analysis.updated_at
        ),
    )