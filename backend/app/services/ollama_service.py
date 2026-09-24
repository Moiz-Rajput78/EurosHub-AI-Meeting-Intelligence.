import json
import logging
import re
from typing import Any
from urllib.error import (
    HTTPError,
    URLError,
)
from urllib.request import (
    Request,
    urlopen,
)

from pydantic import ValidationError

from app.core.config import settings
from app.schemas.analysis import (
    StructuredMeetingAnalysis,
)


logger = logging.getLogger(
    __name__
)


class OllamaServiceError(
    RuntimeError
):
    """
    Raised when Ollama communication fails
    or when the returned structured output
    cannot safely be converted into the
    application's canonical analysis schema.
    """

    pass


def _build_api_url() -> str:
    """
    Build the Ollama chat API endpoint.
    """

    base_url = (
        settings
        .ollama_base_url
        .strip()
        .rstrip("/")
    )

    if not base_url:
        raise OllamaServiceError(
            "OLLAMA_BASE_URL is not configured."
        )

    return f"{base_url}/api/chat"


def _validate_configuration() -> None:
    """
    Validate required Ollama settings.
    """

    if not settings.ollama_model.strip():
        raise OllamaServiceError(
            "OLLAMA_MODEL is not configured."
        )

    if (
        settings
        .ollama_mode
        .strip()
        .lower()
        == "cloud"
        and not settings
        .ollama_api_key
        .strip()
    ):
        raise OllamaServiceError(
            "OLLAMA_API_KEY is not configured."
        )


def _strip_markdown_code_fence(
    content: str,
) -> str:
    """
    Remove Markdown JSON fences if the model
    returns them despite being asked for raw JSON.
    """

    cleaned = content.strip()

    match = re.match(
        r"^```(?:json)?\s*(.*?)\s*```$",
        cleaned,
        flags=(
            re.IGNORECASE
            | re.DOTALL
        ),
    )

    if match:
        return (
            match
            .group(1)
            .strip()
        )

    return cleaned


def _extract_json_object(
    content: str,
) -> dict[str, Any]:
    """
    Parse model content into a dictionary.

    Supports:
    - plain JSON
    - fenced JSON
    - JSON surrounded by minor explanatory text
    """

    cleaned = (
        _strip_markdown_code_fence(
            content
        )
    )

    try:
        parsed = json.loads(
            cleaned
        )

    except json.JSONDecodeError:
        first_brace = cleaned.find(
            "{"
        )

        last_brace = cleaned.rfind(
            "}"
        )

        if (
            first_brace == -1
            or last_brace == -1
            or last_brace
            <= first_brace
        ):
            raise OllamaServiceError(
                "Ollama returned content that "
                "does not contain a JSON object."
            )

        candidate = cleaned[
            first_brace:
            last_brace + 1
        ]

        try:
            parsed = json.loads(
                candidate
            )

        except json.JSONDecodeError as exc:
            logger.exception(
                "Ollama JSON parsing failed."
            )

            raise OllamaServiceError(
                "Ollama returned invalid JSON."
            ) from exc

    if not isinstance(
        parsed,
        dict,
    ):
        raise OllamaServiceError(
            "Ollama structured output "
            "must be a JSON object."
        )

    return parsed


def _looks_like_analysis_payload(
    payload: dict[str, Any],
) -> bool:
    """
    Check whether a dictionary appears to contain
    meeting-analysis information.
    """

    known_keys = {
        "summary",
        "meeting_summary",
        "overview",
        "key_discussion_points",
        "discussion_points",
        "key_points",
        "decisions",
        "action_items",
        "important_dates",
        "open_issues",
        "issues",
        "unanswered_questions",
        "questions",
        "requirements",
        "announcements",
        "topics",
    }

    return bool(
        known_keys.intersection(
            payload.keys()
        )
    )


def _unwrap_analysis_payload(
    payload: dict[str, Any],
) -> dict[str, Any]:
    """
    Remove harmless outer wrappers such as:

    {
        "meeting_notes": {
            ...
        }
    }
    """

    if _looks_like_analysis_payload(
        payload
    ):
        return payload

    wrappers = (
        "meeting_analysis",
        "meeting_notes",
        "analysis",
        "notes",
        "result",
        "data",
        "meeting",
    )

    for wrapper in wrappers:
        nested = payload.get(
            wrapper
        )

        if (
            isinstance(
                nested,
                dict,
            )
            and _looks_like_analysis_payload(
                nested
            )
        ):
            return nested

    dictionaries = [
        value
        for value
        in payload.values()
        if isinstance(
            value,
            dict,
        )
    ]

    if len(dictionaries) == 1:
        candidate = (
            dictionaries[0]
        )

        if _looks_like_analysis_payload(
            candidate
        ):
            return candidate

    return payload


def _clean_string(
    value: Any,
) -> str | None:
    """
    Convert a simple scalar into a cleaned string.

    Complex dictionaries/lists are deliberately not
    serialized blindly here.
    """

    if value is None:
        return None

    if isinstance(
        value,
        str,
    ):
        cleaned = value.strip()

        return (
            cleaned
            if cleaned
            else None
        )

    if isinstance(
        value,
        (
            int,
            float,
            bool,
        ),
    ):
        return str(
            value
        )

    return None


def _extract_text_from_dict(
    value: dict[str, Any],
) -> str | None:
    """
    Safely extract natural-language text from a small
    dictionary returned by the model.

    No facts are created here. Existing model text is
    only flattened into our canonical string format.
    """

    preferred_keys = (
        "summary",
        "meeting_summary",
        "text",
        "content",
        "description",
        "details",
        "detail",
        "overview",
        "point",
        "discussion_point",
        "topic",
        "title",
        "issue",
        "question",
        "announcement",
        "requirement",
        "decision",
        "task",
    )

    pieces: list[str] = []

    for key in preferred_keys:
        if key not in value:
            continue

        cleaned = (
            _clean_string(
                value[key]
            )
        )

        if (
            cleaned
            and cleaned not in pieces
        ):
            pieces.append(
                cleaned
            )

    if pieces:
        return " — ".join(
            pieces
        )

    for nested_value in (
        value.values()
    ):
        cleaned = (
            _clean_string(
                nested_value
            )
        )

        if (
            cleaned
            and cleaned not in pieces
        ):
            pieces.append(
                cleaned
            )

    if pieces:
        return " — ".join(
            pieces
        )

    return None


def _coerce_text(
    value: Any,
) -> str | None:
    """
    Convert a model-provided text representation
    into a canonical string without adding facts.
    """

    cleaned = (
        _clean_string(
            value
        )
    )

    if cleaned is not None:
        return cleaned

    if isinstance(
        value,
        dict,
    ):
        return (
            _extract_text_from_dict(
                value
            )
        )

    return None


def _coerce_string_list(
    value: Any,
) -> list[str]:
    """
    Normalize values such as:

    [
        "Point one",
        {
            "topic": "Attendance",
            "details": "Friday absences increased"
        }
    ]

    into:

    [
        "Point one",
        "Attendance — Friday absences increased"
    ]
    """

    if value is None:
        return []

    if not isinstance(
        value,
        list,
    ):
        value = [
            value
        ]

    result: list[str] = []

    for item in value:
        text = (
            _coerce_text(
                item
            )
        )

        if (
            text
            and text not in result
        ):
            result.append(
                text
            )

    return result


def _prefer_value(
    payload: dict[str, Any],
    canonical_key: str,
    aliases: tuple[str, ...],
    expected_type: type,
) -> Any:
    """
    Prefer a correctly shaped canonical value.

    If the canonical value has the wrong shape, use a
    correctly shaped alias before falling back to the
    original value.
    """

    canonical_value = (
        payload.get(
            canonical_key
        )
    )

    if isinstance(
        canonical_value,
        expected_type,
    ):
        return canonical_value

    for alias in aliases:
        alias_value = (
            payload.get(
                alias
            )
        )

        if isinstance(
            alias_value,
            expected_type,
        ):
            return alias_value

    if canonical_value is not None:
        return canonical_value

    for alias in aliases:
        if alias in payload:
            return payload[
                alias
            ]

    return None


def _normalize_summary(
    payload: dict[str, Any],
) -> None:
    """
    Normalize summary into the string required by the
    application schema.
    """

    raw_summary = (
        _prefer_value(
            payload=payload,
            canonical_key="summary",
            aliases=(
                "meeting_summary",
                "overview",
            ),
            expected_type=str,
        )
    )

    summary = (
        _coerce_text(
            raw_summary
        )
    )

    if summary:
        payload[
            "summary"
        ] = summary


def _normalize_discussion_points(
    payload: dict[str, Any],
) -> None:
    """
    Normalize discussion-point representations into
    list[str].
    """

    raw_points = (
        _prefer_value(
            payload=payload,
            canonical_key=(
                "key_discussion_points"
            ),
            aliases=(
                "discussion_points",
                "key_points",
            ),
            expected_type=list,
        )
    )

    payload[
        "key_discussion_points"
    ] = (
        _coerce_string_list(
            raw_points
        )
    )


def _normalize_topics(
    payload: dict[str, Any],
) -> None:
    """
    Topics are always represented as list[str].
    """

    payload[
        "topics"
    ] = _coerce_string_list(
        payload.get(
            "topics"
        )
    )


def _normalize_object_item(
    item: Any,
    *,
    canonical_field: str,
    aliases: tuple[str, ...],
    evidence_aliases: tuple[str, ...] = (
        "evidence",
        "quote",
        "excerpt",
        "source_text",
        "supporting_text",
    ),
) -> dict[str, Any] | None:
    """
    Normalize one structured extraction item.

    This only remaps existing model fields.
    It never manufactures evidence or facts.
    """

    if isinstance(
        item,
        str,
    ):
        return {
            canonical_field: (
                item.strip()
            ),
            "evidence": "",
        }

    if not isinstance(
        item,
        dict,
    ):
        return None

    result = dict(
        item
    )

    if not result.get(
        canonical_field
    ):
        for alias in aliases:
            value = (
                _coerce_text(
                    result.get(
                        alias
                    )
                )
            )

            if value:
                result[
                    canonical_field
                ] = value

                break

    if not result.get(
        "evidence"
    ):
        for alias in evidence_aliases:
            value = (
                _coerce_text(
                    result.get(
                        alias
                    )
                )
            )

            if value:
                result[
                    "evidence"
                ] = value

                break

    return result


def _normalize_decisions(
    payload: dict[str, Any],
) -> None:
    raw_items = (
        payload.get(
            "decisions"
        )
        or []
    )

    if not isinstance(
        raw_items,
        list,
    ):
        raw_items = [
            raw_items
        ]

    normalized = []

    for item in raw_items:
        converted = (
            _normalize_object_item(
                item,
                canonical_field=(
                    "decision"
                ),
                aliases=(
                    "decision_text",
                    "text",
                    "description",
                    "content",
                ),
            )
        )

        if converted:
            normalized.append(
                converted
            )

    payload[
        "decisions"
    ] = normalized


def _normalize_action_items(
    payload: dict[str, Any],
) -> None:
    raw_items = (
        payload.get(
            "action_items"
        )
        or []
    )

    if not isinstance(
        raw_items,
        list,
    ):
        raw_items = [
            raw_items
        ]

    normalized = []

    for item in raw_items:
        converted = (
            _normalize_object_item(
                item,
                canonical_field="task",
                aliases=(
                    "action",
                    "action_item",
                    "description",
                    "text",
                    "content",
                ),
            )
        )

        if not converted:
            continue

        if not converted.get(
            "responsible_person"
        ):
            for key in (
                "owner",
                "assignee",
                "responsible",
                "assigned_to",
                "person",
            ):
                value = (
                    _coerce_text(
                        converted.get(
                            key
                        )
                    )
                )

                if value:
                    converted[
                        "responsible_person"
                    ] = value

                    break

        if not converted.get(
            "deadline"
        ):
            for key in (
                "due_date",
                "due",
                "date",
                "deadline_date",
            ):
                value = (
                    _coerce_text(
                        converted.get(
                            key
                        )
                    )
                )

                if value:
                    converted[
                        "deadline"
                    ] = value

                    break

        priority = (
            _coerce_text(
                converted.get(
                    "priority"
                )
            )
        )

        if priority:
            priority = (
                priority
                .strip()
                .upper()
                .replace(
                    " ",
                    "_",
                )
            )

        if priority not in {
            "HIGH",
            "MEDIUM",
            "LOW",
            "NOT_SPECIFIED",
        }:
            priority = (
                "NOT_SPECIFIED"
            )

        converted[
            "priority"
        ] = priority

        normalized.append(
            converted
        )

    payload[
        "action_items"
    ] = normalized


def _normalize_important_dates(
    payload: dict[str, Any],
) -> None:
    raw_items = (
        payload.get(
            "important_dates"
        )
        or []
    )

    if not isinstance(
        raw_items,
        list,
    ):
        raw_items = [
            raw_items
        ]

    normalized = []

    for item in raw_items:
        if not isinstance(
            item,
            dict,
        ):
            continue

        converted = dict(
            item
        )

        if not converted.get(
            "date_or_time"
        ):
            for key in (
                "date",
                "time",
                "datetime",
                "when",
                "deadline",
            ):
                value = (
                    _coerce_text(
                        converted.get(
                            key
                        )
                    )
                )

                if value:
                    converted[
                        "date_or_time"
                    ] = value

                    break

        if not converted.get(
            "description"
        ):
            for key in (
                "event",
                "text",
                "details",
                "content",
                "reason",
            ):
                value = (
                    _coerce_text(
                        converted.get(
                            key
                        )
                    )
                )

                if value:
                    converted[
                        "description"
                    ] = value

                    break

        if not converted.get(
            "evidence"
        ):
            for key in (
                "quote",
                "excerpt",
                "source_text",
                "supporting_text",
            ):
                value = (
                    _coerce_text(
                        converted.get(
                            key
                        )
                    )
                )

                if value:
                    converted[
                        "evidence"
                    ] = value

                    break

        normalized.append(
            converted
        )

    payload[
        "important_dates"
    ] = normalized


def _normalize_simple_extraction_list(
    payload: dict[str, Any],
    *,
    canonical_list_key: str,
    list_aliases: tuple[str, ...],
    canonical_field: str,
    field_aliases: tuple[str, ...],
) -> None:
    """
    Normalize lists such as issues, questions,
    requirements and announcements.
    """

    raw_items = (
        payload.get(
            canonical_list_key
        )
    )

    if not raw_items:
        for alias in list_aliases:
            alias_value = (
                payload.get(
                    alias
                )
            )

            if alias_value:
                raw_items = (
                    alias_value
                )
                break

    if raw_items is None:
        raw_items = []

    if not isinstance(
        raw_items,
        list,
    ):
        raw_items = [
            raw_items
        ]

    normalized = []

    for item in raw_items:
        converted = (
            _normalize_object_item(
                item,
                canonical_field=(
                    canonical_field
                ),
                aliases=(
                    field_aliases
                ),
            )
        )

        if converted:
            normalized.append(
                converted
            )

    payload[
        canonical_list_key
    ] = normalized


def _normalize_analysis_payload(
    payload: dict[str, Any],
) -> dict[str, Any]:
    """
    Convert common Ollama output variations into the
    application's canonical StructuredMeetingAnalysis
    representation.

    This function only:
    - renames equivalent keys
    - flattens existing text
    - supplies empty lists
    - normalizes known enum-like values

    It does not create meeting facts.
    """

    normalized = dict(
        payload
    )

    _normalize_summary(
        normalized
    )

    _normalize_discussion_points(
        normalized
    )

    _normalize_decisions(
        normalized
    )

    _normalize_action_items(
        normalized
    )

    _normalize_important_dates(
        normalized
    )

    _normalize_simple_extraction_list(
        normalized,
        canonical_list_key=(
            "open_issues"
        ),
        list_aliases=(
            "issues",
        ),
        canonical_field="issue",
        field_aliases=(
            "issue_text",
            "problem",
            "description",
            "text",
            "content",
        ),
    )

    _normalize_simple_extraction_list(
        normalized,
        canonical_list_key=(
            "unanswered_questions"
        ),
        list_aliases=(
            "questions",
        ),
        canonical_field="question",
        field_aliases=(
            "question_text",
            "text",
            "content",
            "description",
        ),
    )

    _normalize_simple_extraction_list(
        normalized,
        canonical_list_key=(
            "requirements"
        ),
        list_aliases=(),
        canonical_field=(
            "requirement"
        ),
        field_aliases=(
            "requirement_text",
            "text",
            "content",
            "description",
        ),
    )

    _normalize_simple_extraction_list(
        normalized,
        canonical_list_key=(
            "announcements"
        ),
        list_aliases=(),
        canonical_field=(
            "announcement"
        ),
        field_aliases=(
            "announcement_text",
            "text",
            "content",
            "description",
        ),
    )

    _normalize_topics(
        normalized
    )

    collection_fields = (
        "key_discussion_points",
        "decisions",
        "action_items",
        "important_dates",
        "open_issues",
        "unanswered_questions",
        "requirements",
        "announcements",
        "topics",
    )

    for field_name in (
        collection_fields
    ):
        if (
            field_name
            not in normalized
            or normalized[
                field_name
            ] is None
        ):
            normalized[
                field_name
            ] = []

    return normalized


def _parse_structured_content(
    content: str,
) -> StructuredMeetingAnalysis:
    """
    Parse, normalize and strictly validate Ollama output.
    """

    payload = (
        _extract_json_object(
            content
        )
    )

    payload = (
        _unwrap_analysis_payload(
            payload
        )
    )

    payload = (
        _normalize_analysis_payload(
            payload
        )
    )

    try:
        return (
            StructuredMeetingAnalysis
            .model_validate(
                payload
            )
        )

    except ValidationError as exc:
        logger.error(
            "Ollama structured output "
            "failed Pydantic validation: %s",
            exc,
        )

        logger.error(
            "Top-level Ollama payload keys: %s",
            sorted(
                payload.keys()
            ),
        )

        logger.error(
            "Normalized Ollama field types: %s",
            {
                key: type(
                    value
                ).__name__
                for key, value
                in payload.items()
            },
        )

        raise OllamaServiceError(
            "Ollama returned structured data "
            "that did not match the required schema."
        ) from exc


def request_structured_analysis(
    *,
    system_prompt: str,
    user_prompt: str,
) -> StructuredMeetingAnalysis:
    """
    Request structured analysis from Ollama.

    Works with Ollama Cloud and remains compatible
    with a local Ollama endpoint if configured later.
    """

    _validate_configuration()

    mode = (
        settings
        .ollama_mode
        .strip()
        .lower()
        or "local"
    )

    logger.info(
        "[ANALYSIS] Ollama started. Mode=%s model=%s",
        mode,
        settings.ollama_model,
    )

    schema = (
        StructuredMeetingAnalysis
        .model_json_schema()
    )

    formatting_instruction = """
STRICT OUTPUT REQUIREMENTS:

Return exactly one JSON object.

Do not return Markdown.
Do not use ```json fences.
Do not add explanatory prose.

The top-level JSON object must directly contain:

summary
key_discussion_points
decisions
action_items
important_dates
open_issues
unanswered_questions
requirements
announcements
topics

IMPORTANT TYPE REQUIREMENTS:

summary MUST be a plain JSON string.

Example:
"summary": "The team discussed attendance trends."

Do NOT return summary as an object.

key_discussion_points MUST be an array of plain strings.

Example:
"key_discussion_points": [
  "The team discussed Friday attendance.",
  "Student follow-up was reviewed."
]

Do NOT return discussion points as objects.

For decisions, action items, dates, issues, questions,
requirements and announcements, follow the supplied
JSON schema exactly.

Evidence must contain only exact spoken words copied
from the supplied transcript.
""".strip()

    payload = {
        "model": (
            settings.ollama_model
        ),
        "messages": [
            {
                "role": "system",
                "content": (
                    system_prompt
                    + "\n\n"
                    + formatting_instruction
                ),
            },
            {
                "role": "user",
                "content": (
                    user_prompt
                ),
            },
        ],
        "stream": False,
        "format": schema,
        "options": {
            "temperature": 0,
        },
    }

    headers = {
        "Content-Type": (
            "application/json"
        ),
    }

    api_key = (
        settings
        .ollama_api_key
        .strip()
    )

    if api_key:
        headers[
            "Authorization"
        ] = (
            f"Bearer {api_key}"
        )

    request = Request(
        url=_build_api_url(),
        data=json.dumps(
            payload,
            ensure_ascii=False,
        ).encode(
            "utf-8"
        ),
        headers=headers,
        method="POST",
    )

    try:
        with urlopen(
            request,
            timeout=(
                settings
                .ollama_timeout_seconds
            ),
        ) as response:
            response_body = (
                response
                .read()
                .decode(
                    "utf-8"
                )
            )

    except HTTPError as exc:
        try:
            error_body = (
                exc
                .read()
                .decode(
                    "utf-8"
                )
            )

        except Exception:
            error_body = ""

        logger.error(
            "Ollama HTTP error %s: %s",
            exc.code,
            error_body,
        )

        if exc.code == 401:
            raise OllamaServiceError(
                "Ollama authentication failed."
            ) from exc

        if exc.code == 429:
            raise OllamaServiceError(
                "Ollama rate limit or usage "
                "limit was reached."
            ) from exc

        raise OllamaServiceError(
            "Ollama Cloud returned "
            f"HTTP {exc.code}."
        ) from exc

    except URLError as exc:
        logger.exception(
            "Unable to reach Ollama."
        )

        raise OllamaServiceError(
            "Unable to connect to Ollama."
        ) from exc

    except TimeoutError as exc:
        raise OllamaServiceError(
            "Ollama request timed out."
        ) from exc

    try:
        response_data = (
            json.loads(
                response_body
            )
        )

    except json.JSONDecodeError as exc:
        logger.exception(
            "Ollama HTTP response was "
            "not valid JSON."
        )

        raise OllamaServiceError(
            "Ollama returned an invalid "
            "HTTP response."
        ) from exc

    error_message = (
        response_data.get(
            "error"
        )
    )

    if error_message:
        raise OllamaServiceError(
            f"Ollama error: {error_message}"
        )

    message = (
        response_data.get(
            "message"
        )
    )

    if not isinstance(
        message,
        dict,
    ):
        raise OllamaServiceError(
            "Ollama response did not "
            "contain a message."
        )

    content = (
        message.get(
            "content"
        )
    )

    if (
        not isinstance(
            content,
            str,
        )
        or not content.strip()
    ):
        raise OllamaServiceError(
            "Ollama returned an empty "
            "analysis."
        )

    result = (
        _parse_structured_content(
            content
        )
    )

    logger.info(
        "[ANALYSIS] Ollama completed successfully. "
        "Mode=%s model=%s",
        mode,
        settings.ollama_model,
    )

    return result