from dataclasses import dataclass #Allows to easly create classes containing data
from typing import Any # Any can be any type of variable
from .config import MODEL_NAME, validate_model_configuration

from openai import (
    APIConnectionError,
    APIError,
    APITimeoutError,
    AuthenticationError,
    BadRequestError,
    OpenAI,
    RateLimitError,
)

# Create a defoult client variable which can either be OpenAI or None and 
# initializes it to None (we do not have created a client yet)
_default_client_instance: OpenAI | None = None 


# Create a class -> structure of response of model call
# Forzen means that once the result have been created after response, 
# nothing can be modified
@dataclass(frozen=True)
class ModelCallResult:
    """Text and SDK metadata returned by one successful model call."""

    output_text: str
    resolved_model: str | None
    response_id: str | None
    raw_response: Any
    usage: Any

# Create AssistantError: can be personilized
# associate with a family and a message easy to understand
# Still save original error
class AssistantError(RuntimeError):
    """A typed, user-readable model-call or diagnostics failure."""

    def __init__(
        self,
        family: str,  # kind of error
        message: str, # message of the error
        *, # following variable MUST be specified
        original_error: Exception | None = None, #can keep original errpr (before changing in AssistantError)
    ) -> None:
        super().__init__(message) # Use all info of RuntimeError
        self.family = family      # Add AssistantError family
        self.original_error = original_error #Add assistant error original error


# We want to create the client the first time only, for following runs use the same one
def _default_client() -> OpenAI:
    """Create the default client on first use and reuse it for later calls."""
    global _default_client_instance #use global variable defined outside function

    validate_model_configuration() #check API key and url are present
    if _default_client_instance is None: #first call
        _default_client_instance = OpenAI()
    return _default_client_instance


# Error "translation"
def error_message(exc: APIError) -> tuple[str, str]:
    """Translate OpenAI SDK errors into readable messages."""
    if isinstance(exc, AuthenticationError):
        return "authentication", "Authentication failed. Check your OpenRouter API key."
    if isinstance(exc, RateLimitError):
        return "rate_limit", "The API rate or quota limit was reached. Wait and retry."
    if isinstance(exc, (APITimeoutError, APIConnectionError)):
        return (
            "connection_or_timeout",
            "OpenRouter could not be reached. Check network, proxy, DNS, and firewall settings.",
        )
    if isinstance(exc, BadRequestError):
        return "malformed_request", f"OpenRouter rejected the request: {exc}" # Print whole error to see where the bad request is
    return "api_error", f"The model API request failed: {exc}" #if not of the above


# Convert value in a jason (if is not None and if attribute "model_dump" exists)
def _model_dump(value: Any) -> Any:
    """Convert SDK models into JSON-compatible diagnostic data."""
    if value is None:
        return None
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json")
    return value


# Call model: takes instruction, user_input and can take client
# Output: ModelCallResult
def call_model(
    instructions: str,
    user_input: str,
    api_client: Any = None,
) -> ModelCallResult:
    """Send one request and return its text with diagnostic metadata."""
    # If client in input use it otherwise use defoult client (OpenAI())
    selected_client = api_client if api_client is not None else _default_client()

    try:
        response = selected_client.responses.create(
            model=MODEL_NAME,
            instructions=instructions,
            input=user_input,
        )
    except APIError as exc: # If instead an APIError is obtained, save it as exc
        family, message = error_message(exc) # From error gives us family and message
        raise AssistantError(  # Raise the generic assistant error keeping the original one
            family,
            message,
            original_error=exc,
        ) from exc

    answer = response.output_text.strip()
    if not answer: #If the string is empty
        raise AssistantError(
            "malformed_response",
            "The API response contained no usable text. Inspect the Phoenix trace.",
        )

    return ModelCallResult(
        output_text=answer,
        resolved_model=getattr(response, "model", None),
        response_id=getattr(response, "id", None),
        raw_response=_model_dump(response),
        usage=_model_dump(getattr(response, "usage", None)),
    )




    