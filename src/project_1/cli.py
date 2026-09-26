"""Command-line interface for the Municipal Front-Desk Assistant."""



from .chat import answer_question
from .client import AssistantError
from .config import ConfigurationError
from .tracing import setup_tracing
import sys



def main() -> int:
    setup_tracing()

    query = input("What's your question? ")

    try:
        answer = answer_question(query)
        fields = answer.get("fields", {})

    except (ConfigurationError, AssistantError) as exc:
        family = getattr(exc, "family", "configuration") #takes family from AssistantError and configuration from configurationerror
        print(f"Error [{family}]: {exc}", file=sys.stderr)
        return 2

    fields = answer.get("fields", {})

    print(f"Reference_number: {fields.get('reference_number')}")
    print(f"Name: {fields.get('person_name')}")
    print(f"Urgency: {answer.get('urgency_level')}")
    print()
    print(answer.get("answer"))
    
    return 0

