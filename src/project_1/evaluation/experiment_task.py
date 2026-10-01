"""Business orchestration for the Municipal Front-Desk Assistant."""

from collections.abc import Callable, Mapping
from typing import Any

from ..assistant_output import validate_assistant_output
from ..config import PROMPT_VERSION
from ..prompts.loader import load_prompt

ModelCall = Callable[[str, str], str] #ModelCall is a type for any function that takes two strings (instructions and user_input) and returns a string (the model's output).

def run_task(
    user_input: str,
    *,
    model_call: ModelCall | None = None,
    api_client: Any = None,
) -> dict[str, Any]:
    """Call the application prompt and return a serializable task result."""
    instructions = load_prompt("instruction", PROMPT_VERSION)
    call = model_call or _default_model_call(api_client)
    raw_output = call(instructions, user_input)
    validation = validate_assistant_output(raw_output)

    if not validation["valid"]:
        return {
            "raw_output": raw_output,
            "contract_valid": False,
            "errors": validation["errors"],
        }

    return {
        "raw_output": raw_output,
        "output": validation["output"],
        "contract_valid": True,
        "errors": [],
    }
    

def _default_model_call(api_client: Any) -> ModelCall:
    from ..client import call_model

    def call(instructions: str, user_input: str) -> str:
        return call_model(
            instructions=instructions,
            user_input=user_input,
            api_client=api_client,
        ).output_text

    return call


def run_dataset_case(input: Mapping[str, Any]) -> dict[str, Any]:
    """Run one Phoenix dataset example and return its structured output."""
    text = input.get("text")
    if not isinstance(text, str) or not text.strip():
        return {
            "_contract_valid": False,
            "_errors": ["Dataset input must contain non-empty text."],
        }

    result = run_task(text.strip())
    if not result.get("contract_valid"):
        return {
            "_contract_valid": False,
            "_errors": result.get("errors", []),
            "_raw_output": result.get("raw_output"),
        }

    output = dict(result["output"])
    output["_contract_valid"] = True
    output["_raw_output"] = result.get("raw_output")
    return output































'''

import json
import os

from openai import BadRequestError
from opentelemetry import trace
from opentelemetry.trace import StatusCode

from .client import ModelCallResult, call_model
from .config import MODEL_NAME
from .contract import validate
from .retry import MAX_RETRIES, RETRYABLE, call_with_retry




PROMPT_VERSION = os.getenv("PROMPT_VERSION", "v5")

_INSTRUCTIONS = load_prompt("instruction", PROMPT_VERSION)

# Add a code only after the selected provider route has been verified to use it
# specifically for a policy block. Unknown request errors remain operational.
VERIFIED_POLICY_ERROR_CODES: frozenset[str] = frozenset()


# Take the error
def _structured_error_code(exc: Exception) -> str | None:
    body = getattr(exc, "body", None)
    if not isinstance(body, dict):
        return None

    code = body.get("code")
    if isinstance(code, str):
        return code

    nested_error = body.get("error")
    if isinstance(nested_error, dict):
        nested_code = nested_error.get("code")
        if isinstance(nested_code, str):
            return nested_code
    return None



def _response_fields(result: ModelResult, retries_used: int) -> dict[str, object]:
    return {
        "raw_output": result.output_text,
        "model": MODEL_NAME,
        "resolved_model": result.resolved_model,
        "prompt_version": PROMPT_VERSION,
        "response_id": result.response_id,
        "response_status": result.response_status,
        "incomplete_reason": result.incomplete_reason,
        "refusal": result.refusal,
        "retries": retries_used,
        "error": None,
        "error_type": None,
        "error_code": None,
    }



# Serve quando la risposta del modello è arrivata,
# ma il risultato non può essere usato per la valutazione
# (es. refusal, risposta troncata, risposta incompleta).
def _quality_failure(
    outcome: str,
    violations: list[str],
    result: ModelCallResult,
    retries_used: int,
) -> dict[str, object]:
    return {
        **_response_fields(result, retries_used),
        "answer": None,
        "fields": None,
        "urgency_level": None,
        "urgency_rationale": None,
        "contract_valid": False,
        "contract_violations": violations,
        "outcome": outcome,
    }


# Serve quando il modello non ha prodotto una risposta utilizzabile
# a causa di un errore operativo.
def _operational_failure(
    exc: Exception,
    *,
    retries_used: int,
    error_code: str | None = None,
) -> dict[str, object]:
    return {
        "raw_output": None,
        "answer": None,
        "fields": None,
        "urgency_level": None,
        "urgency_rationale": None,
        "contract_valid": False,
        "contract_violations": [],
        "model": MODEL_NAME,
        "resolved_model": None,
        "prompt_version": PROMPT_VERSION,
        "response_id": None,
        "response_status": None,
        "incomplete_reason": None,
        "refusal": None,
        "retries": retries_used,
        "outcome": "operational_error",
        "error": str(exc),
        "error_type": type(exc).__name__,
        "error_code": error_code,
    }



def answer_question(input: dict, metadata: dict) -> dict[str, object]:
    """Answer one case and preserve every anticipated per-case outcome."""
    span = trace.get_current_span()
    span.set_attribute("eval.dataset_version", os.environ["DATASET_VERSION"])
    span.set_attribute("eval.case_id", metadata.get("case_id", "unknown"))
    span.set_attribute("eval.prompt_version", PROMPT_VERSION)
    span.set_attribute("eval.model", MODEL_NAME)

    try:
        result, retries_used = call_with_retry(
            lambda: call_model(
                instructions=_INSTRUCTIONS,
                user_input=input["text"],
            )
        )
        

    except BadRequestError as exc:
        error_code = _structured_error_code(exc)
        span.record_exception(exc)
        span.set_attribute("eval.retries_used", 0)

        if error_code in VERIFIED_POLICY_ERROR_CODES:
            span.set_attribute("eval.outcome", "refusal")
            span.set_status(StatusCode.OK)
            return {
                **_operational_failure(
                    exc,
                    retries_used=0,
                    error_code=error_code,
                ),
                "outcome": "refusal",
                "error": None,
                "error_type": None,
                "contract_violations": ["Provider policy refusal"],
            }

        span.set_status(StatusCode.ERROR, str(exc))
        span.set_attribute("eval.error_type", type(exc).__name__)
        span.set_attribute("eval.outcome", "operational_error")
        if error_code is not None:
            span.set_attribute("eval.error_code", error_code)

        return _operational_failure(
            exc,
            retries_used=0,
            error_code=error_code,
        )

    except Exception as exc:
        retries_used = MAX_RETRIES if isinstance(exc, RETRYABLE) else 0
        span.record_exception(exc)
        span.set_status(StatusCode.ERROR, str(exc))
        span.set_attribute("eval.error_type", type(exc).__name__)
        span.set_attribute("eval.outcome", "operational_error")
        span.set_attribute("eval.retries_used", retries_used)

        return _operational_failure(
            exc,
            retries_used=retries_used,
        )

    span.set_attribute("eval.retries_used", retries_used)
    if result.response_status is not None:
        span.set_attribute("eval.response_status", result.response_status)
    if result.incomplete_reason is not None:
        span.set_attribute("eval.incomplete_reason", result.incomplete_reason)

    if result.refusal is not None:
        outcome = "refusal"
        output = _quality_failure(
            outcome,
            ["Model returned a structured refusal"],
            result,
            retries_used,
        )
    elif result.response_status == "incomplete":
        if result.incomplete_reason == "max_output_tokens":
            outcome = "truncated"
            violation = "Response was truncated at the output-token limit"
        elif result.incomplete_reason == "content_filter":
            outcome = "refusal"
            violation = "Response was blocked by the content filter"
        else:
            outcome = "contract_invalid"
            violation = "Response was incomplete"
        output = _quality_failure(outcome, [violation], result, retries_used)
    else:
        contract = validate(result.output_text)
        try:
            parsed_value = json.loads(result.output_text)
        except json.JSONDecodeError:
            parsed = {}
            outcome = "malformed_json"
        else:
            if isinstance(parsed_value, dict):
                parsed = parsed_value
                outcome = "success" if contract["valid"] else "contract_invalid"
            else:
                parsed = {}
                outcome = "unexpected_json_type"

        output = {
            **_response_fields(result, retries_used),
            "answer": parsed.get("answer"),
            "fields": parsed.get("fields"),
            "urgency_level": parsed.get("urgency_level"),
            "urgency_rationale": parsed.get("urgency_rationale"),
            "contract_valid": contract["valid"],
            "contract_violations": contract["violations"],
            "outcome": outcome,
        }

    span.set_attribute("eval.raw_output_length", len(result.output_text))
    span.set_attribute("eval.contract_valid", output["contract_valid"] is True)
    span.set_attribute("eval.outcome", str(output["outcome"]))
    span.set_status(StatusCode.OK)
    return output


'''























