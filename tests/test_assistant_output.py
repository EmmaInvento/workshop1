"""Unit tests for the structured assistant-output contract."""

import json

from project_1.assistant_output import validate_assistant_output


def valid_output() -> dict[str, object]:
    return {
        "answer": "Contact the permits office.",
        "fields": {
            "person_name": "Elena Maric",
            "reference_number": "CS-4827",
            "amount": 75.0,
            "date": "last Tuesday",
        },
        "urgency_level": "routine",
        "urgency_rationale": "No deadline or immediate hazard is stated.",
    }


def test_accepts_complete_valid_output() -> None:
    result = validate_assistant_output(json.dumps(valid_output()))

    assert result["valid"] is True
    assert result["output"] == valid_output()
    assert result["errors"] == []


def test_rejects_non_json_output() -> None:
    result = validate_assistant_output("not JSON")

    assert result["valid"] is False
    assert result["output"] is None
    assert "not valid JSON" in result["errors"][0]


def test_rejects_extra_top_level_field() -> None:
    output = valid_output()
    output["unexpected"] = True

    result = validate_assistant_output(json.dumps(output))

    assert result["valid"] is False
    assert result["output"] is None


def test_rejects_boolean_amount_and_unknown_urgency() -> None:
    output = valid_output()
    fields = output["fields"]
    assert isinstance(fields, dict)
    fields["amount"] = True
    output["urgency_level"] = "immediate"

    result = validate_assistant_output(json.dumps(output))

    assert result["valid"] is False
    assert len(result["errors"]) == 2