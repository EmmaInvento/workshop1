"""Opt-in, full-fidelity JSONL diagnostics for model calls."""

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .client import AssistantError, ModelCallResult


# Takes the AssistantError and return a dict containing all error detail
def _error_details(exc: AssistantError) -> dict[str, str]:
    """Return controlled error fields without serializing exception internals."""
    original = exc.original_error or exc # take original error if present
    return {
        "type": type(original).__name__, #string containing original error name
        "family": exc.family, #family we defined in assistanError
        "message": str(original), #moriginal message
        "application_message": str(exc), #massage we defined in AssistantError
    }


# Create a dict containing a strin: "model call" and ANY -> all information
# of the call given in inpiut. NB: result and error can be None -> we cam have 
# a succesfull model call or one which raised an error.    
def build_model_call_event(
    *,
    request_id: str,
    prompt_version: str,
    instructions: str,
    user_input: str,
    requested_model: str,
    phoenix_endpoint: str,
    phoenix_project: str,
    diagnostics_path: Path,
    started_at: datetime,
    latency_ms: float,
    result: ModelCallResult | None = None,
    error: AssistantError | None = None,
) -> dict[str, Any]:
    """Build one complete success or failure event."""
    return {
        "event": "model_call",
        "timestamp": started_at.astimezone(UTC).isoformat(),
        "request_id": request_id,
        "prompt_version": prompt_version,
        "configuration": {
            "model": requested_model,
            "prompt_version": prompt_version,
            "diagnostics_path": str(diagnostics_path),
            "phoenix_endpoint": phoenix_endpoint,
            "phoenix_project": phoenix_project,
        },
        "input_context": {
            "instructions": instructions,
            "user_input": user_input,
        },
        "model": {
            "requested": requested_model,
            "resolved": result.resolved_model if result else None,
        },
        "response_id": result.response_id if result else None,
        "raw_response": result.raw_response if result else None,
        "usage": result.usage if result else None,
        "output_text": result.output_text if result else None,
        "latency_ms": round(latency_ms, 3),
        "outcome": "success" if result else "error",
        "error": _error_details(error) if error else None,
    }


# Add event(dict) to parent directory
def append_diagnostic(path: Path, event: dict[str, Any]) -> None:
    """Append one event, creating its parent directory when needed."""
    try:
        path.parent.mkdir(parents=True, exist_ok=True) #Create a folder in the parent directory. If it already exsits use it
        #open file in append mode, call it stream while we use it, then close it
        with path.open("a", encoding="utf-8") as stream:
            #convert in jason, use str as a defolt if you can't convert, new line
            stream.write(json.dumps(event, ensure_ascii=False, default=str) + "\n") 
    
    # If anything goes wrong        
    except (OSError, TypeError, ValueError) as exc:
        raise AssistantError(
            "local_logging",
            f"The local diagnostic event could not be written to {path}: {exc}",
            original_error=exc,
        ) from exc    
    

