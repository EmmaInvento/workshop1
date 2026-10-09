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
    CONTEXT_WINDOW_TOKENS,
    DIAGNOSTICS_PATH,
    MODEL_NAME,
    OUTPUT_BUFFER_TOKENS,
    PHOENIX_COLLECTOR_ENDPOINT,
    PHOENIX_PROJECT_NAME,
    PROMPT_VERSION,
    ConfigurationError,
    validate_model_configuration,
)
from .context import prepare_context
from .diagnostics import append_diagnostic, build_model_call_event
from .prompts.loader import load_prompt
from .tracing import get_tracer

tracer = get_tracer(__name__)
MAX_INPUT_TOKENS = CONTEXT_WINDOW_TOKENS - OUTPUT_BUFFER_TOKENS

# Write the event of the model call if the diagnostic path was configured
def _write_model_call_event(
    *,
    request_id: str,
    instructions: str,
    query: str,
    context_usage: dict[str, object],
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
        context_usage=context_usage,
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


# Complete turn: context preparation, model call, answer validation, and diagnostics.
def model_turn(
    query: str,
    history: list[dict[str, str]],
    request_id: str,
    *,
    context_strategy: str = "trim",
    api_client: Any = None,
) -> dict[str, Any]:
    """Prepare the context, call the model, and return one successful turn."""
    instructions = load_prompt("instruction", PROMPT_VERSION)
    messages, estimated_tokens, removed_turns, summary_usage = prepare_context(
        instructions,
        history,
        query,
        MAX_INPUT_TOKENS,
        MODEL_NAME,
        context_strategy,
        api_client,
    )
    context_usage: dict[str, object] = {
        "strategy": context_strategy,
        "estimated_input_tokens": estimated_tokens,
        "input_limit": MAX_INPUT_TOKENS,
        "removed_turns": removed_turns,
    }
    started_at = datetime.now(UTC)
    started_clock = time.perf_counter()

    try:
        result = call_model(
            instructions=instructions,
            user_input=messages,
            api_client=api_client,
        )
    except AssistantError as exc:
        _write_model_call_event(
            request_id=request_id,
            instructions=instructions,
            query=query,
            context_usage=context_usage,
            started_at=started_at,
            started_clock=started_clock,
            error=exc,
        )
        raise

    validation = validate_assistant_output(result.output_text)
    structured_output = validation["output"]
    if structured_output is None:
        output_error = AssistantError(
            "malformed_response",
            "; ".join(validation["errors"]),
        )
        _write_model_call_event(
            request_id=request_id,
            instructions=instructions,
            query=query,
            context_usage=context_usage,
            started_at=started_at,
            started_clock=started_clock,
            result=result,
            error=output_error,
        )
        raise output_error

    _write_model_call_event(
        request_id=request_id,
        instructions=instructions,
        query=query,
        context_usage=context_usage,
        started_at=started_at,
        started_clock=started_clock,
        result=result,
        structured_output=structured_output,
    )

    current_span = trace.get_current_span()
    current_span.set_attribute(
        "municipal.urgency_level", structured_output["urgency_level"]
    )
    current_span.set_attribute(
        "municipal.extracted_fields",
        json.dumps(structured_output["fields"], ensure_ascii=False),
    )
    current_span.set_attribute("municipal.estimated_input_tokens", estimated_tokens)
    current_span.set_attribute("municipal.removed_turns", removed_turns)

    return {
        "answer": structured_output["answer"],
        "raw_output": result.output_text,
        "messages": messages,
        "estimated_tokens": estimated_tokens,
        "removed_turns": removed_turns,
        "usage": result.usage,
        "summary_usage": summary_usage,
    }




# Does all the checking - apply model_turn -> prepare context and call model
def answer_turn(
    query: str,
    history: list[dict[str, str]],
    request_id: str,
    *,
    context_strategy: str = "trim",
    api_client: Any = None,
) -> dict[str, Any]:
    """Validate and run one turn without changing the supplied history list."""
    query = query.strip()
    if not query:
        raise ConfigurationError("The resident's question must not be empty.")
    if MAX_INPUT_TOKENS <= 0:
        raise ConfigurationError(
            "OUTPUT_BUFFER_TOKENS must be smaller than CONTEXT_WINDOW_TOKENS."
        )
    if api_client is None:
        validate_model_configuration()

    with tracer.start_as_current_span("municipal_front_desk.request") as span:
        span.set_attribute("municipal.request_id", request_id)
        span.set_attribute("municipal.prompt_version", PROMPT_VERSION)
        span.set_attribute("municipal.context_strategy", context_strategy)
        try:
            result = model_turn(
                query,
                history,
                request_id,
                context_strategy=context_strategy,
                api_client=api_client,
            )
        except AssistantError as exc:
            span.set_attribute("municipal.outcome", "error")
            span.set_attribute("municipal.error_family", exc.family)
            raise
        span.set_attribute("municipal.outcome", "success")
        return result



def model_call(query: str, request_id: str, api_client: Any = None) -> str:
    """Backward-compatible single-turn model-call helper."""
    return answer_turn(query, [], request_id, api_client=api_client)["answer"]


def answer_question(
    query: str,
    request_id: str | None = None,
    api_client: Any = None,
) -> str:
    """Run the single-turn path used by evaluation and smoke tests."""
    return answer_turn(
        query,
        [],
        request_id or str(uuid.uuid4()),
        api_client=api_client,
    )["answer"]







