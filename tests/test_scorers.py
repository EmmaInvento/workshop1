"""Unit tests for deterministic Workshop 2 scorers."""

from project_1.evaluation.evaluators import (
    extraction_fields_match,
    urgency_level_matches,
)


def test_extraction_normalizes_case_spacing_dates_and_amounts() -> None:
    output = {
        "fields": {
            "person_name": "  ELENA   MARIC ",
            "reference_number": "cs-4827",
            "amount": 75,
            "date": "03 / 04",
        }
    }
    expected = {
        "fields": {
            "person_name": "Elena Maric",
            "reference_number": "CS-4827",
            "amount": 75.0,
            "date": "03/04",
        }
    }

    assert extraction_fields_match(output, expected) is True


def test_extraction_does_not_invent_missing_values() -> None:
    output = {
        "fields": {
            "person_name": "Marco Bianchi",
            "reference_number": "invented",
            "amount": None,
            "date": "3 April",
        }
    }
    expected = {
        "fields": {
            "person_name": "Marco Bianchi",
            "reference_number": None,
            "amount": None,
            "date": "3 April",
        }
    }

    assert extraction_fields_match(output, expected) is False


def test_urgency_requires_an_allowed_matching_level() -> None:
    assert urgency_level_matches(
        {"urgency_level": "urgent"}, {"urgency_level": "urgent"}
    )
    assert not urgency_level_matches(
        {"urgency_level": "immediate"}, {"urgency_level": "immediate"}
    )