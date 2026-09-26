"""Business orchestration for the Municipal Front-Desk Assistant."""

import time
import uuid
from datetime import UTC, datetime
from typing import Any

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
from .contract import validate
import json
import os



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
    )
    append_diagnostic(DIAGNOSTICS_PATH, event)


def _run_model_call(query: str, request_id: str, api_client: Any = None) -> str:
    """Load the prompt, call the model, and record optional diagnostics."""
    instructions = load_prompt("instruction_v1")
    started_at = datetime.now(UTC)  
    started_clock = time.perf_counter()

    try:
        result = call_model( 
            instructions=instructions,
            user_input=query,
            api_client=api_client,
        )
    except AssistantError as exc:
        _write_model_call_event( #regoster error
            request_id=request_id,
            instructions=instructions,
            query=query,
            started_at=started_at,
            started_clock=started_clock,
            error=exc,
        )
        raise #raise error

    _write_model_call_event( # register result if no error was raised
        request_id=request_id,
        instructions=instructions,
        query=query,
        started_at=started_at,
        started_clock=started_clock,
        result=result,
    )
    return result.output_text # take text output only



PROMPT_VERSION = os.getenv("PROMPT_VERSION", "v1")

def answer_question(input: dict) -> dict:
    """Task: answer qestion and return the model
    output for scoring."""
    text = input["text"]
    instructions = load_prompt("instruction", PROMPT_VERSION)
    raw = call_model(
        instructions=instructions,
        user_input=text,
    ).output_text
    contract = validate(raw) #check if output contract is verified -> string can be converte in json
    parsed = json.loads(raw) if contract["valid"] else {} #convert in json
    return {
        "raw_output": raw,
        "contract_valid": contract["valid"],
        "contract_violations": contract["violations"],
        "answer": parsed.get("answer"),
        "fields": parsed.get("fields"),
        "urgency_level": parsed.get("urgency_level"),
        "urgency_rationale": parsed.get("urgency_rationale"),
        "model": MODEL_NAME,
        "prompt_version": PROMPT_VERSION,
    }













'''
def answer_question(
    query: str,
    request_id: str | None = None,
    api_client: Any = None,
) -> dict:
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
            answer = _run_model_call(query.strip(), resolved_request_id, api_client)
            contract = validate(answer)
            parsed = json.loads(answer) if contract["valid"] else {}
        except AssistantError as exc:
            span.set_attribute("municipal.outcome", "error")
            span.set_attribute("municipal.error_family", exc.family)
            raise
        span.set_attribute("municipal.outcome", "success")
        return {
        "raw_output": answer,
        "contract_valid": contract["valid"],
        "contract_violations": contract["violations"],
        "answer": parsed.get("answer"),
        "fields": parsed.get("fields"),
        "urgency_level": parsed.get("urgency_level"),
        "urgency_rationale": parsed.get("urgency_rationale"),
        "model": MODEL_NAME,
        "prompt_version": PROMPT_VERSION,
    }

'''

























