"""Unit tests for controlled diagnostic error serialization."""

from datetime import UTC, datetime
from pathlib import Path

from project_1.client import AssistantError
from project_1.diagnostics import build_model_call_event


class ErrorWithInternals(ValueError):
    def __init__(self) -> None:
        super().__init__("invalid response")
        self.internal_token = "must-not-be-serialized"


def test_diagnostic_error_contains_only_controlled_fields() -> None:
    original = ErrorWithInternals()
    error = AssistantError(
        "malformed_response",
        "The response was invalid.",
        original_error=original,
    )

    event = build_model_call_event(
        request_id="CASE-1",
        prompt_version="test-prompt",
        instructions="instructions",
        user_input="question",
        requested_model="test-model",
        phoenix_endpoint="http://localhost:6006/v1/traces",
        phoenix_project="test",
        diagnostics_path=Path("diagnostics/test.jsonl"),
        started_at=datetime.now(UTC),
        latency_ms=1.0,
        error=error,
    )

    assert event["error"] == {
        "type": "ErrorWithInternals",
        "family": "malformed_response",
        "message": "invalid response",
        "application_message": "The response was invalid.",
    }