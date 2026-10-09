import tiktoken

from.client import (
    JSON_MODE_INSTRUCTION,
    AssistantError,
    call_model,
    uses_json_mode,
)

from .conversation import validate_history

MESSAGE_OVERHEAD = 4 # message structure to be counted together with content
REPLY_PRIMER = 3
HYBRID_HARD_LIMIT_RATIO = 1.5
SUMMARY_LABEL = "Summary of the earlier conversation:"

# Find the encoding for a given model, with a fallback for OpenRouter or local names.
def _encoding_for_model(model: str):
    """Use the model encoding, with a fallback for OpenRouter or local names."""
    try:
        return tiktoken.encoding_for_model(model)
    except KeyError:
        return tiktoken.get_encoding("o200k_base")
    

def count_tokens(text: str, model: str) -> int:
    """Return the number of tokens in text for the given model."""
    encoding = _encoding_for_model(model)
    return len(encoding.encode(text))

# we don't use encode_chat_completation() like in count_message because it applies to minstral only
def _message_tokens(messages: list[dict[str, str]], model: str) -> int:
    """Count message content plus the per-message overhead from Lecture 7."""
    return sum(
        count_tokens(message["content"], model) + MESSAGE_OVERHEAD
        for message in messages
    )
    
def truncate_oldest(
    history: list[dict[str, str]],
    max_tokens: int,
    model: str,
) -> list[dict[str, str]]:
    """Remove oldest turn pairs until history fits."""
    trimmed = list(history)
    while trimmed and _message_tokens(trimmed, model) > max_tokens:
        # Drop the oldest user + assistant pair.
        trimmed = trimmed[2:]
    return trimmed


def summarize_history(
    older_messages: list[dict[str, str]], api_client=None
) -> tuple[str, object]:
    """Compress older history into a factual summary."""
    result = call_model(
        instructions=(
            "Summarize the key facts, resident constraints, and decisions from this "
            "Principality of Latentia conversation. Preserve names, reference numbers, "
            "dates, amounts, corrections, unresolved questions, and safety signals. "
            "Do not invent information."
        ),
        user_input=older_messages,
        api_client=api_client,
    )
    return result.output_text, result.usage


def hybrid_reduce(
    history: list[dict[str, str]],
    max_tokens: int,
    model: str,
    api_client=None,
) -> tuple[list[dict[str, str]], object]:
    """Use the hybrid summarization/truncation policy from Lecture 7."""
    total = _message_tokens(history, model)

    # Within budget: return the full history unchanged.
    if total <= max_tokens:
        return list(history), None

    # Severely over budget: truncate without paying for a summary call.
    hard_limit = int(max_tokens * HYBRID_HARD_LIMIT_RATIO)
    if total > hard_limit:
        return truncate_oldest(history, max_tokens, model), None

    # Moderately over budget: summarize the older half.
    midpoint = (len(history) // 2) & ~1 #divide by 2 and round down to nearest even number
    if midpoint == 0:
        return truncate_oldest(history, max_tokens, model), None

    older = history[:midpoint]
    recent = history[midpoint:]
    summary, summary_usage = summarize_history(older, api_client)
    summarized_history = [
        {"role": "user", "content": SUMMARY_LABEL},
        {"role": "assistant", "content": summary},
        *recent,
    ]

    # The summary may still be too large, so apply the normal fallback.
    summarized_history = truncate_oldest(summarized_history, max_tokens, model)
    return summarized_history, summary_usage



def prepare_context(
    instructions: str,
    history: list[dict[str, str]],
    current_message: str,
    max_input_tokens: int,
    model: str,
    context_strategy: str = "trim",
    api_client=None,
) -> tuple[list[dict[str, str]], int, int, object]:
    """Build the input while protecting instructions and the current message."""
    validate_history(history)

    fixed_tokens = (
        count_tokens(instructions, model)
        + MESSAGE_OVERHEAD
        + count_tokens(current_message, model)
        + MESSAGE_OVERHEAD
        + REPLY_PRIMER
    )
    if uses_json_mode(instructions):
        fixed_tokens += count_tokens(JSON_MODE_INSTRUCTION, model) + MESSAGE_OVERHEAD
    if fixed_tokens > max_input_tokens:
        raise AssistantError(
            "context_overflow",
            "This message is too long. Please shorten it or split it into smaller messages.",
        )

    history_budget = max_input_tokens - fixed_tokens
    if context_strategy == "trim":
        reduced_history = truncate_oldest(history, history_budget, model)
        summary_usage = None
    elif context_strategy == "summary":
        reduced_history, summary_usage = hybrid_reduce(
            history, history_budget, model, api_client
        )
    else:
        raise ValueError("Context strategy must be 'trim' or 'summary'.")

    messages = [
        *reduced_history,
        {"role": "user", "content": current_message},
    ]
    estimated_tokens = fixed_tokens + _message_tokens(reduced_history, model)
    removed_turns = (len(history) - len(reduced_history)) // 2
    return messages, estimated_tokens, removed_turns, summary_usage