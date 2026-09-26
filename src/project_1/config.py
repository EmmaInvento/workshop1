from dotenv import load_dotenv
import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2] #Project path

load_dotenv(PROJECT_ROOT / ".env") #Take .env from project path

# Create a new type of error called ConfigurationError
# It is a particular type of ValueError
class ConfigurationError(ValueError):
    """Raised when a required setting is missing or invalid."""


OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL")
MODEL_NAME = os.getenv("MODEL_NAME", "openai/gpt-5-mini")
PROMPT_VERSION = os.getenv("PROMPT_VERSION", "v1")
PHOENIX_BASE_URL: str = os.getenv(
    "PHOENIX_BASE_URL",
    "http://localhost:6006",
)
PHOENIX_COLLECTOR_ENDPOINT = os.getenv(
    "PHOENIX_COLLECTOR_ENDPOINT",
    "http://localhost:6006/v1/traces",
)
PHOENIX_PROJECT_NAME = os.getenv("PHOENIX_PROJECT_NAME", "project-1")

# Create function that check for API ket and URL and raise an explicative 
# error if one is missing -> To be called before client creation.

def validate_model_configuration() -> None:
    if not OPENAI_API_KEY: 
        raise ConfigurationError(
            "OPENAI_API_KEY is missing."
        )
    if not OPENAI_BASE_URL:
        raise ConfigurationError(
            "OPENAI_BASE_URL is missing. Set it to https://openrouter.ai/api/v1 "
            "in .env."
        )

# Create a function that check variable DIAGNOSTIC_PATH:
# if it is empty returns None
# Otherwise check is the path is absolute or not:
# Absolute -> stays at it is
# Relative -> is made absolute by adding PROJECT_ROOT        
def _diagnostics_path() -> Path | None:
    value = os.getenv("DIAGNOSTICS_PATH", "").strip()
    if not value:
        return None

    path = Path(value)
    if not path.is_absolute():
        path = PROJECT_ROOT / path
    return path


DIAGNOSTICS_PATH = _diagnostics_path()        