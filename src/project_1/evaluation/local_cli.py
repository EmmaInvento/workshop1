"""Command-line entry point for the local Workshop 2 evaluation."""

import json
import sys

from ..client import AssistantError
from ..config import (
    PROMPT_VERSION,
    ConfigurationError,
    validate_model_configuration,
)
from .run_experiment import run_evaluation
from .evaluators import extraction_fields_match, urgency_level_matches
from .experiment_task import run_task

EVALUATORS = {
    "information_extraction": {
        "fields_match": extraction_fields_match,
    },
    "urgency_assessment": {
        "level_match": urgency_level_matches,
    },
}


def main() -> int:
    """Run the golden set and print its complete JSON result."""
    try:
        validate_model_configuration()
        result = run_evaluation(
            task=run_task,
            evaluators=EVALUATORS,
            prompt_version=PROMPT_VERSION,
        )
    except (ConfigurationError, AssistantError) as exc:
        family = getattr(exc, "family", "configuration")
        print(f"Error [{family}]: {exc}", file=sys.stderr)
        return 2

    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["passed"] else 1