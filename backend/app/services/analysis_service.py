import json
import re
from dataclasses import dataclass

from app.core.config import settings
from app.schemas.analysis import (
    ActionItemExtraction,
    AnnouncementExtraction,
    DecisionExtraction,
    ImportantDateExtraction,
    OpenIssueExtraction,
    QuestionExtraction,
    RequirementExtraction,
    StructuredMeetingAnalysis,
)
from app.services.ollama_service import (
    request_structured_analysis,
)


SYSTEM_PROMPT = """
You are a rigorous meeting intelligence analyst.

Your task is to analyze ONLY the meeting transcript provided
to you and return structured meeting notes.

GROUNDING RULES:

1. Never invent a person's name.
2. Never invent an owner or responsible person.
3. Never invent a deadline.
4. Never invent a date.
5. Never invent a decision.
6. Never invent a requirement.
7. Never invent an action item.
8. Never convert a suggestion into a confirmed decision.
9. Never convert an idea into an assigned task.
10. Preserve uncertainty from the transcript.
11. If an owner is not explicitly stated, use null.
12. If a deadline is not explicitly stated, use null.
13. If priority is not explicitly stated, use
    NOT_SPECIFIED.
14. Do not infer identities from Speaker 1, Speaker 2,
    or similar generic labels.
15. A user's manually supplied display name may be used
    exactly as shown in the transcript.
16. Evidence fields must contain a short exact excerpt of
    SPOKEN WORDS copied from the supplied transcript.
17. Do not put timestamps or speaker labels inside the
    evidence field.
18. If you cannot provide exact supporting evidence for a
    decision, action item, date, issue, question,
    requirement, or announcement, do not extract it.
19. Summaries and discussion points must remain faithful
    to the transcript.
20. Do not use outside knowledge.

Return JSON matching the supplied schema.
""".strip()


@dataclass
class TranscriptLine:
    start_time: float
    end_time: float
    speaker: str
    text: str


@dataclass
class AnalysisResult:
    analysis: StructuredMeetingAnalysis
    chunk_count: int


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

    return (
        f"{hours:02d}:"
        f"{minutes:02d}:"
        f"{secs:02d}"
    )


def format_transcript_line(
    line: TranscriptLine,
) -> str:
    start = _format_timestamp(
        line.start_time
    )

    end = _format_timestamp(
        line.end_time
    )

    return (
        f"[{start} - {end}] "
        f"{line.speaker}: "
        f"{line.text.strip()}"
    )


def chunk_transcript(
    lines: list[TranscriptLine],
) -> list[list[TranscriptLine]]:
    if not lines:
        return []

    max_chars = max(
        2000,
        settings.analysis_chunk_chars,
    )

    overlap_count = max(
        0,
        settings.analysis_chunk_overlap_lines,
    )

    chunks: list[
        list[TranscriptLine]
    ] = []

    current_chunk: list[
        TranscriptLine
    ] = []

    current_length = 0

    index = 0

    while index < len(lines):
        line = lines[index]

        formatted = (
            format_transcript_line(
                line
            )
        )

        extra_length = (
            len(formatted) + 1
        )

        if (
            current_chunk
            and (
                current_length
                + extra_length
                > max_chars
            )
        ):
            chunks.append(
                current_chunk
            )

            if overlap_count > 0:
                current_chunk = (
                    current_chunk[
                        -overlap_count:
                    ]
                )
            else:
                current_chunk = []

            current_length = sum(
                len(
                    format_transcript_line(
                        item
                    )
                )
                + 1
                for item
                in current_chunk
            )

            continue

        current_chunk.append(
            line
        )

        current_length += (
            extra_length
        )

        index += 1

    if current_chunk:
        chunks.append(
            current_chunk
        )

    return chunks


def _normalize_for_evidence(
    value: str,
) -> str:
    return re.sub(
        r"[^a-z0-9]+",
        " ",
        value.lower(),
    ).strip()


def _evidence_exists(
    evidence: str,
    spoken_transcript: str,
) -> bool:
    normalized_evidence = (
        _normalize_for_evidence(
            evidence
        )
    )

    normalized_transcript = (
        _normalize_for_evidence(
            spoken_transcript
        )
    )

    if not normalized_evidence:
        return False

    return (
        normalized_evidence
        in normalized_transcript
    )


def _deduplicate_strings(
    values: list[str],
) -> list[str]:
    result: list[str] = []

    seen: set[str] = set()

    for value in values:
        cleaned = value.strip()

        if not cleaned:
            continue

        key = (
            _normalize_for_evidence(
                cleaned
            )
        )

        if not key:
            continue

        if key in seen:
            continue

        seen.add(
            key
        )

        result.append(
            cleaned
        )

    return result


def _deduplicate_objects(
    values: list,
    key_getter,
) -> list:
    result = []

    seen: set[str] = set()

    for value in values:
        raw_key = key_getter(
            value
        )

        key = (
            _normalize_for_evidence(
                raw_key
            )
        )

        if not key:
            continue

        if key in seen:
            continue

        seen.add(
            key
        )

        result.append(
            value
        )

    return result


def _validate_grounded_items(
    analysis: StructuredMeetingAnalysis,
    spoken_transcript: str,
) -> StructuredMeetingAnalysis:
    decisions = [
        item
        for item
        in analysis.decisions
        if _evidence_exists(
            item.evidence,
            spoken_transcript,
        )
    ]

    action_items = [
        item
        for item
        in analysis.action_items
        if _evidence_exists(
            item.evidence,
            spoken_transcript,
        )
    ]

    important_dates = [
        item
        for item
        in analysis.important_dates
        if _evidence_exists(
            item.evidence,
            spoken_transcript,
        )
    ]

    open_issues = [
        item
        for item
        in analysis.open_issues
        if _evidence_exists(
            item.evidence,
            spoken_transcript,
        )
    ]

    unanswered_questions = [
        item
        for item
        in analysis.unanswered_questions
        if _evidence_exists(
            item.evidence,
            spoken_transcript,
        )
    ]

    requirements = [
        item
        for item
        in analysis.requirements
        if _evidence_exists(
            item.evidence,
            spoken_transcript,
        )
    ]

    announcements = [
        item
        for item
        in analysis.announcements
        if _evidence_exists(
            item.evidence,
            spoken_transcript,
        )
    ]

    return StructuredMeetingAnalysis(
        summary=(
            analysis.summary.strip()
            or (
                "No reliable summary "
                "could be generated."
            )
        ),
        key_discussion_points=(
            _deduplicate_strings(
                analysis
                .key_discussion_points
            )
        ),
        decisions=(
            _deduplicate_objects(
                decisions,
                lambda item: (
                    item.decision
                ),
            )
        ),
        action_items=(
            _deduplicate_objects(
                action_items,
                lambda item: (
                    item.task
                ),
            )
        ),
        important_dates=(
            _deduplicate_objects(
                important_dates,
                lambda item: (
                    item.date_or_time
                    + " "
                    + item.description
                ),
            )
        ),
        open_issues=(
            _deduplicate_objects(
                open_issues,
                lambda item: (
                    item.issue
                ),
            )
        ),
        unanswered_questions=(
            _deduplicate_objects(
                unanswered_questions,
                lambda item: (
                    item.question
                ),
            )
        ),
        requirements=(
            _deduplicate_objects(
                requirements,
                lambda item: (
                    item.requirement
                ),
            )
        ),
        announcements=(
            _deduplicate_objects(
                announcements,
                lambda item: (
                    item.announcement
                ),
            )
        ),
        topics=(
            _deduplicate_strings(
                analysis.topics
            )
        ),
    )


def _analyze_single_chunk(
    chunk: list[TranscriptLine],
    chunk_number: int,
    total_chunks: int,
) -> StructuredMeetingAnalysis:
    transcript_text = "\n".join(
        format_transcript_line(
            line
        )
        for line in chunk
    )

    prompt = f"""
Analyze this meeting transcript section.

This is transcript chunk {chunk_number} of {total_chunks}.

Important:
- Treat this as part of one larger meeting.
- Extract only information explicitly supported here.
- Evidence must be copied exactly from spoken words.
- Return valid structured JSON only.

TRANSCRIPT:

{transcript_text}
""".strip()

    return request_structured_analysis(
        system_prompt=(
            SYSTEM_PROMPT
        ),
        user_prompt=prompt,
    )


def _merge_without_llm(
    analyses: list[
        StructuredMeetingAnalysis
    ],
) -> StructuredMeetingAnalysis:
    summaries = [
        item.summary.strip()
        for item in analyses
        if item.summary.strip()
    ]

    return StructuredMeetingAnalysis(
        summary=(
            " ".join(
                summaries
            )
        ),
        key_discussion_points=[
            point
            for analysis in analyses
            for point in (
                analysis
                .key_discussion_points
            )
        ],
        decisions=[
            item
            for analysis in analyses
            for item in (
                analysis.decisions
            )
        ],
        action_items=[
            item
            for analysis in analyses
            for item in (
                analysis.action_items
            )
        ],
        important_dates=[
            item
            for analysis in analyses
            for item in (
                analysis.important_dates
            )
        ],
        open_issues=[
            item
            for analysis in analyses
            for item in (
                analysis.open_issues
            )
        ],
        unanswered_questions=[
            item
            for analysis in analyses
            for item in (
                analysis
                .unanswered_questions
            )
        ],
        requirements=[
            item
            for analysis in analyses
            for item in (
                analysis.requirements
            )
        ],
        announcements=[
            item
            for analysis in analyses
            for item in (
                analysis.announcements
            )
        ],
        topics=[
            topic
            for analysis in analyses
            for topic in analysis.topics
        ],
    )


def _consolidate_chunk_analyses(
    analyses: list[
        StructuredMeetingAnalysis
    ],
) -> StructuredMeetingAnalysis:
    payload = [
        analysis.model_dump()
        for analysis in analyses
    ]

    prompt = f"""
You are consolidating structured analyses from consecutive
chunks of the SAME meeting.

Remove duplicates created by overlapping transcript chunks.

Do not add any new facts.

Do not invent any owners, names, dates, deadlines,
decisions, requirements, tasks, or announcements.

Preserve evidence exactly as supplied.

Create one coherent meeting summary.

If two chunk analyses conflict, preserve uncertainty rather
than choosing an unsupported interpretation.

CHUNK ANALYSES:

{json.dumps(
    payload,
    ensure_ascii=False,
)}
""".strip()

    return request_structured_analysis(
        system_prompt=(
            SYSTEM_PROMPT
        ),
        user_prompt=prompt,
    )


def analyze_transcript(
    lines: list[TranscriptLine],
) -> AnalysisResult:
    chunks = chunk_transcript(
        lines
    )

    if not chunks:
        raise ValueError(
            "The meeting transcript is empty."
        )

    analyses: list[
        StructuredMeetingAnalysis
    ] = []

    for index, chunk in enumerate(
        chunks,
        start=1,
    ):
        analyses.append(
            _analyze_single_chunk(
                chunk=chunk,
                chunk_number=index,
                total_chunks=len(
                    chunks
                ),
            )
        )

    if len(analyses) == 1:
        combined_analysis = (
            analyses[0]
        )
    else:
        preliminary = (
            _merge_without_llm(
                analyses
            )
        )

        combined_analysis = (
            _consolidate_chunk_analyses(
                [
                    preliminary
                ]
            )
        )

    spoken_transcript = "\n".join(
        line.text
        for line in lines
    )

    grounded_analysis = (
        _validate_grounded_items(
            combined_analysis,
            spoken_transcript,
        )
    )

    return AnalysisResult(
        analysis=grounded_analysis,
        chunk_count=len(
            chunks
        ),
    )