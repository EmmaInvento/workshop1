"""Validation for the structured output returned by the assistant prompt."""

import json
from collections.abc import Mapping
from typing import Any, TypedDict, cast

EXTRACTION_FIELDS = (
    "person_name",
    "reference_number",
    "amount",
    "date",
)
ALLOWED_URGENCY_LEVELS = {
    "routine",
    "time_sensitive",
    "urgent",
}
REQUIRED_OUTPUT_FIELDS = {
    "answer",
    "fields",
    "urgency_level",
    "urgency_rationale",
}


class ExtractedFields(TypedDict):
    """Information extracted verbatim from a resident request."""

    person_name: str | None
    reference_number: str | None
    amount: int | float | None
    date: str | None


class AssistantOutput(TypedDict):
    """Validated structured response produced by the assistant."""

    answer: str
    fields: ExtractedFields
    urgency_level: str
    urgency_rationale: str


class ValidationResult(TypedDict):
    """Result of validating one raw model response."""

    valid: bool
    output: AssistantOutput | None
    errors: list[str]


def validate_assistant_output(raw_output: str) -> ValidationResult:
    """Validate one structured assistant response without raising contract errors."""
    errors: list[str] = []
    try:
        output = json.loads(raw_output)
    except json.JSONDecodeError as exc:
        return {
            "valid": False,
            "output": None,
            "errors": [f"The model response was not valid JSON: {exc.msg}"],
        }

    if not isinstance(output, Mapping):
        return {
            "valid": False,
            "output": None,
            "errors": ["The model response must be a JSON object."],
        }
    if set(output) != REQUIRED_OUTPUT_FIELDS:
        return {
            "valid": False,
            "output": None,
            "errors": [
                "The model response must contain exactly: "
                + ", ".join(sorted(REQUIRED_OUTPUT_FIELDS))
                + "."
            ],
        }

    answer = output["answer"]
    if not isinstance(answer, str) or not answer.strip():
        errors.append("The 'answer' field must be a non-empty string.")

    fields = output["fields"]
    if not isinstance(fields, Mapping) or set(fields) != set(EXTRACTION_FIELDS):
        errors.append(
            "The 'fields' object must contain exactly the documented extraction fields."
        )
    else:
        _append_nullable_string_error(errors, fields, "person_name")
        _append_nullable_string_error(errors, fields, "reference_number")
        _append_nullable_string_error(errors, fields, "date")
        amount = fields["amount"]
        if amount is not None and (
            isinstance(amount, bool) or not isinstance(amount, (int, float))
        ):
            errors.append("The 'amount' field must be a JSON number or null.")

    urgency_level = output["urgency_level"]
    if urgency_level not in ALLOWED_URGENCY_LEVELS:
        errors.append(
            "The 'urgency_level' field must be routine, time_sensitive, or urgent."
        )

    rationale = output["urgency_rationale"]
    if not isinstance(rationale, str) or not rationale.strip():
        errors.append("The 'urgency_rationale' field must be a non-empty string.")

    return {
        "valid": not errors,
        "output": cast(AssistantOutput, dict(output)) if not errors else None,
        "errors": errors,
    }


# Take a list of errors, fields (that should be a dictionary-like type with string keys and any type of value)
def _append_nullable_string_error(
    errors: list[str], fields: Mapping[str, Any], field: str
) -> None:
    value = fields[field]
    if value is not None and not isinstance(value, str):
        errors.append(f"The '{field}' field must be a string or null.")