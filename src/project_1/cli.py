"""Command-line interface for the Municipal Front-Desk Assistant."""



from .chat import answer_question
from .client import AssistantError
from .config import ConfigurationError
from .tracing import setup_tracing



def main() -> int:
    setup_tracing()

    query = input("What's your question? ")

    try:
        answer = answer_question(query)
    except (ConfigurationError, AssistantError) as exc:
        family = getattr(exc, "family", "configuration") #takes family from AssistantError and configuration from configurationerror
        print(f"Error [{family}]: {exc}", file=sys.stderr)
        return 2

    print(answer)
    return 0

