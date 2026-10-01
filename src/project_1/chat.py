"""Business orchestration for the Municipal Front-Desk Assistant."""

import time
import uuid
from datetime import UTC, datetime
from typing import Any
import json

from opentelemetry import trace
from .assistant_output import AssistantOutput, validate_assistant_output

from .client import AssistantError, ModelCallResult, call_model
from .config import (
    DIAGNOSTICS_PATH,
    MODEL_NAME,
    PHOENIX_COLLECTOR_ENDPOINT,
    PHOENIX_PROJECT_NAME,
    PROMPT_VERSION,
    ConfigurationError,
    validate_model_configuration,
)
from .diagnostics import append_diagnostic, build_model_call_event
from .prompts.loader import load_prompt
from .tracing import get_tracer

tracer = get_tracer(__name__)

# Write the event of the model call if the diagnostic path was configured
def _write_model_call_event(
    *,
    request_id: str,
    instructions: str,
    query: str,
    started_at: datetime,
    started_clock: float,
    result: ModelCallResult | None = None,
    structured_output: AssistantOutput | None = None,
    error: AssistantError | None = None,
) -> None:
    """Write a local event when optional JSONL diagnostics are enabled."""
    if DIAGNOSTICS_PATH is None: #If we do not define a path -> we do not write diagnostic
        return

    event = build_model_call_event( 
        request_id=request_id,
        prompt_version=PROMPT_VERSION,
        instructions=instructions,
        user_input=query,
        requested_model=MODEL_NAME,
        phoenix_endpoint=PHOENIX_COLLECTOR_ENDPOINT,
        phoenix_project=PHOENIX_PROJECT_NAME,
        diagnostics_path=DIAGNOSTICS_PATH,
        started_at=started_at,
        latency_ms=(time.perf_counter() - started_clock) * 1000,
        result=result,
        error=error,
        structured_output=structured_output,
    )
    append_diagnostic(DIAGNOSTICS_PATH, event)


def _run_model_call(query: str, request_id: str, api_client: Any = None) -> str:
    """Load the prompt, call the model, and record optional diagnostics."""
    instructions = load_prompt("instruction", PROMPT_VERSION)
    started_at = datetime.now(UTC)  
    started_clock = time.perf_counter()

    try:
        result = call_model( 
            instructions=instructions,
            user_input=query,
            api_client=api_client,
        )
    # If we get an error from the call
    except AssistantError as exc:
        _write_model_call_event( #register error
            request_id=request_id,
            instructions=instructions,
            query=query,
            started_at=started_at,
            started_clock=started_clock,
            error=exc, #keep error not result
        )
        raise #raise error
    
    validation = validate_assistant_output(result.output_text) #validate output text
    structured_output = validation["output"]
    # If you get errors from validation
    if structured_output is None:
        output_error = AssistantError(
            "malformed_response",
            "; ".join(validation["errors"]),
        )
        _write_model_call_event(
            request_id=request_id,
            instructions=instructions,
            query=query,
            started_at=started_at,
            started_clock=started_clock,
            error=output_error,
        )
        raise output_error

    # If we don't get errors from validation
    _write_model_call_event( # register result if no error was raised
        request_id=request_id,
        instructions=instructions,
        query=query,
        started_at=started_at,
        started_clock=started_clock,
        result=result, #keep result not error
        structured_output=structured_output, #keep structured output
    )
    
    current_span = trace.get_current_span()
    current_span.set_attribute("municipal.urgency_level", structured_output["urgency_level"])
    current_span.set_attribute(
        "municipal.extracted_fields",
        json.dumps(structured_output["fields"], ensure_ascii=False),
    )
    return structured_output




def answer_question(
    query: str,
    request_id: str | None = None,
    api_client: Any = None,
) -> str:
    """Run the complete municipal question-answering path."""
    if not query.strip():
        raise ConfigurationError("The municipal question must not be empty.") #error is before client call
    if api_client is None:
        validate_model_configuration()

    resolved_request_id = request_id or str(uuid.uuid4()) # if no request_id -> generate one
    with tracer.start_as_current_span("chat_response.request") as span:
        span.set_attribute("municipal.request_id", resolved_request_id)
        span.set_attribute("municipal.prompt_version", PROMPT_VERSION)
        try:
            output = _run_model_call(query.strip(), resolved_request_id, api_client)
        except AssistantError as exc:
            span.set_attribute("municipal.outcome", "error")
            span.set_attribute("municipal.error_family", exc.family)
            raise
        span.set_attribute("municipal.outcome", "success")
        return output["answer"]






