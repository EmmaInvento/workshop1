from phoenix.client.experiments import create_evaluator
import re
from collections.abc import Mapping
from decimal import Decimal, InvalidOperation
from typing import Any

from ..assistant_output import ALLOWED_URGENCY_LEVELS, EXTRACTION_FIELDS

EVALUATOR_VERSION = "contract"


def output_contract_valid(output: Mapping[str, Any]) -> bool:
    """Check whether the evaluation task produced a valid structured output."""
    return output.get("_contract_valid") is True

def extraction_fields_match(
    output: Mapping[str, Any], expected: Mapping[str, Any]
) -> bool:
    """Compare extracted values with the reference output."""
    fields = output.get("fields")
    expected_fields = expected.get("fields")
    if not isinstance(fields, Mapping) or set(fields) != set(EXTRACTION_FIELDS):
        return False
    if not isinstance(expected_fields, Mapping):
        return False

    return all(
        _extracted_value_matches(field, fields[field], expected_fields.get(field))
        for field in EXTRACTION_FIELDS
    )

def _extracted_value_matches(field: str, actual: Any, expected: Any) -> bool:
    """Compare one extracted value using the smallest safe normalization."""
    # if one of the values is None, return True only if both are None
    if actual is None or expected is None:
        return actual is None and expected is None
    if field == "amount":
        try:
            return Decimal(str(actual)) == Decimal(str(expected)) #avoid float problems by converting to string first
        except (InvalidOperation, ValueError):
            return False
    if not isinstance(actual, str) or not isinstance(expected, str):
        return actual == expected
    return _normalize_extracted_text(field, actual) == _normalize_extracted_text(
        field, expected
    )

def _normalize_extracted_text(field: str, value: str) -> str:
    """Normalize presentation differences without guessing the extracted value."""
    normalized = " ".join(value.casefold().split())
    if field == "date":
        normalized = re.sub(r"\s*([/-])\s*", r"\1", normalized) #remove spaces around date separators
    return normalized

def urgency_level_matches(
    output: Mapping[str, Any], expected: Mapping[str, Any]
) -> bool:
    """Compare an allowed urgency level with its reference value."""
    urgency_level = output.get("urgency_level")
    return urgency_level in ALLOWED_URGENCY_LEVELS and urgency_level == expected.get(
        "urgency_level"
    )

def _not_applicable(dimension: str) -> dict[str, Any]:
    return {
        "score": None,
        "label": "not_applicable",
        "explanation": f"This case is not part of {dimension}.",
    }



@create_evaluator(name="contract_valid", kind="CODE")
def phoenix_output_contract_valid(output: Mapping[str, Any]) -> bool:
    """Expose contract validation as a Phoenix evaluator."""
    return output_contract_valid(output)


@create_evaluator(name="extraction_fields_match", kind="CODE")
def phoenix_extraction_fields_match(
    output: Mapping[str, Any],
    expected: Mapping[str, Any],
    metadata: Mapping[str, Any] | None = None,
    **kwargs: object,
) -> bool | dict[str, Any]:
    """Expose extraction scoring and skip unrelated Phoenix examples."""
    if metadata is not None and metadata.get("dimension") != "information_extraction":
        return _not_applicable("information_extraction")
    return extraction_fields_match(output, expected)    

@create_evaluator(name="urgency_level_matches", kind="CODE")
def phoenix_urgency_level_matches(
    output: Mapping[str, Any],
    expected: Mapping[str, Any],
    metadata: Mapping[str, Any] | None = None,
    **kwargs: object,
) -> bool | dict[str, Any]:
    """Expose urgency scoring and skip unrelated Phoenix examples."""
    if metadata is not None and metadata.get("dimension") != "urgency_assessment":
        return _not_applicable("urgency_assessment")
    return urgency_level_matches(output, expected)



