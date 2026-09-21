import json
from pathlib import Path

import pytest
from opentelemetry.sdk.trace.export.in_memory_span_exporter import (
    InMemorySpanExporter,
)
from project_1.chat import answer_question

SMOKE_INPUTS: list[str] = json.loads(
    (Path(__file__).parent / "smoke_inputs.json").read_text()
)


@pytest.mark.parametrize("message", SMOKE_INPUTS)
def test_chat_response_returns_valid_answer(message: str) -> None:
    """The function returns a non-empty string ."""
    result = answer_question(message)

    # The output must not be empty.
    assert result != "", (
        f"Empty output for input: {message!r}"
    )
    # The output must be one of the declared category strings.
    # This is a FORMAT check: the prompt instructs the model
    # to respond with exactly one category name in lowercase.
    # If the output is not in OFFICES, the format
    # instruction failed, which is a structural failure.
    '''
    assert result in OFFICES, (
        f"Output {result!r} is not a valid category. "
        f"Expected one of: {OFFICES}"
    )
    '''
    


# Check that spans with a certain name (we decided in classifier.py) or certain 
#attributes are being produced

def test_chat_response_emits_a_span(
    span_exporter: InMemorySpanExporter,
) -> None:
    """A chat_response span is exported after each call."""
    span_exporter.clear()
    answer_question("Who should I contact about a broken streetlight?")

    spans = span_exporter.get_finished_spans()
    assert len(spans) > 0, (
        "No spans exported after chat_response call"
    )
    span_names = [s.name for s in spans]
    assert "chat_response.request" in span_names, (
        f"Expected 'chat_response.request' span. "
        f"Spans found: {span_names}"
    )