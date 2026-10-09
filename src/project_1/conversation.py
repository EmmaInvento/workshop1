import json
from pathlib import Path
from typing import Any

def load_conversation(
    path: Path, selected_id: str | None = None
) -> tuple[str, list[dict[str, str]]]:
    """Load one conversation from the supplied JSON file."""
    try:
        conversations = json.loads(path.read_text(encoding="utf-8")) #trasforma json in oggetto python (list di dict)
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"Failed to load conversation from {path}: {exc}") from exc
    
    if not isinstance(conversations, list):
        raise TypeError("Conversation file must contain a JSON list")
    
    available_ids = []
    for conversation in conversations:
        if not isinstance(conversation, dict) or "conversation_id" not in conversation:
            raise ValueError("Every conversation needs a conversation_id.")
        available_ids.append(conversation["conversation_id"])
        
    if len(set(available_ids)) != len(available_ids):
        raise ValueError("Conversation IDs must be unique.")
    
    if selected_id is None:
        if len(available_ids) != 1:
            raise ValueError(
                "Choose a conversation with --conversation-id. "
                f"Available: {', '.join(available_ids)}."
            )
        selected_id = available_ids[0] #if only one conversation defoult to that one
        
    selected_messages = None
    for conversation in conversations:
        if conversation["conversation_id"] == selected_id:
            selected_messages = conversation.get("messages") #take messages from selected conversation
            break

    if selected_messages is None:
        raise ValueError(
            f"Unknown conversation_id '{selected_id}'. "
            f"Available: {', '.join(available_ids)}."
        )

    validate_history(selected_messages)
    return selected_id, list(selected_messages)




def validate_history(messages: Any) -> None:
    """Validate a history of complete, alternating user/assistant turns."""
    if not isinstance(messages, list):
        # Normalize malformed conversation data to ValueError for the CLI.
        raise ValueError(  # noqa: TRY004
            "Conversation messages must be a JSON list."
        )
    if len(messages) % 2 != 0:
        raise ValueError("A conversation must contain complete user/assistant turns.")

    for index, message in enumerate(messages):
        expected_role = "user" if index % 2 == 0 else "assistant"
        if (
            not isinstance(message, dict)
            or message.get("role") != expected_role
            or not isinstance(message.get("content"), str)
            or not message["content"].strip()
        ):
            raise ValueError(
                f"Message {index} must be a non-empty {expected_role} message."
            )
