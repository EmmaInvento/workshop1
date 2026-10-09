"""Command-line interface for the Municipal Front-Desk Assistant."""
import argparse
import sys
import uuid
from pathlib import Path
from typing import Any


from .chat import MAX_INPUT_TOKENS, answer_turn
from .client import AssistantError
from .config import ConfigurationError
from .conversation import load_conversation
from .tracing import setup_tracing




def _print_usage(result: dict[str, Any]) -> None:
    """Print context and API token usage for one successful turn."""
    usage = result["usage"] if isinstance(result["usage"], dict) else {}
    line = (
        f"Tokens: estimated {result['estimated_tokens']}/{MAX_INPUT_TOKENS}; "
        f"API input {usage.get('input_tokens', '?')}, "
        f"output {usage.get('output_tokens', '?')}; "
        f"removed turns {result['removed_turns']}"
    )
    summary_usage = result["summary_usage"]
    if isinstance(summary_usage, dict):
        line += (
            f"; summary call {summary_usage.get('input_tokens', '?')} input, "
            f"{summary_usage.get('output_tokens', '?')} output"
        )
    print(line)



def _interactive_chat(
    history: list[dict[str, str]],
    conversation_id: str,
    context_strategy: str,
) -> int:
    """Run the in-memory multi-turn terminal chat."""
    print("Principality of Latentia assistant ready. Type /exit to close the chat.")
    while True:
        try:
            message = input("You: ")
        except EOFError:
            print()
            return 0

        if message.strip().lower() in {"/exit", "/quit"}:
            return 0

        request_id = f"{conversation_id}:turn-{len(history) // 2 + 1}"
        try:
            result = answer_turn(
                message,
                history,
                request_id,
                context_strategy=context_strategy,
            )
        except (ConfigurationError, AssistantError, ValueError) as exc:
            print(
                f"Error [{getattr(exc, 'family', 'configuration')}]: {exc}",
                file=sys.stderr,
            )
            continue

        # Commit the turn only after the model returned a valid answer.
        history[:] = result["messages"] #add input messages to history
        history.append({"role": "assistant", "content": result["raw_output"]}) #add answer to history
        print(f"\n Assistant: {result['answer']}\n")
        _print_usage(result)
        print()




def main() -> int:
    """Parse CLI options and run either a one-shot request or a conversation."""
    parser = argparse.ArgumentParser(
        description="Chat with the Principality of Latentia Front-Desk Assistant."
    )
    parser.add_argument(
        "query",
        nargs="*",
        help="optional one-shot question; omit it to open the chat",
    )
    parser.add_argument("--request-id", help="identifier included in diagnostics")
    parser.add_argument(
        "--load-conversation",
        type=Path,
        help="JSON file containing conversations to load into memory",
    )
    parser.add_argument(
        "--conversation-id",
        help="conversation to select from the JSON file",
    )
    parser.add_argument(
        "--context-strategy",
        choices=("trim", "summary"),
        default="trim",
        help="use old-turn removal or optional summarization",
    )
    parser.add_argument(
        "--no-tracing",
        action="store_true",
        help="do not export Phoenix traces",
    )
    args = parser.parse_args()

    try:
        if not args.no_tracing:
            setup_tracing()

        conversation_id = args.request_id or str(uuid.uuid4())
        history: list[dict[str, str]] = []
        if args.load_conversation:
            loaded_id, history = load_conversation(
                args.load_conversation, args.conversation_id
            )
            if args.request_id is None:
                conversation_id = loaded_id
        elif args.conversation_id:
            raise ConfigurationError("--conversation-id requires --load-conversation.")

        if args.query:
            result = answer_turn(
                " ".join(args.query),
                history,
                conversation_id,
                context_strategy=args.context_strategy,
            )
            print(f"\n{result['answer']}\n")
            _print_usage(result)
            print()
            return 0

        return _interactive_chat(history, conversation_id, args.context_strategy)
    except (ConfigurationError, AssistantError, ValueError) as exc:
        print(
            f"Error [{getattr(exc, 'family', 'configuration')}]: {exc}",
            file=sys.stderr,
        )
        return 2

