import json

import pytest

from project_1 import context as context_module
from project_1.chat import answer_turn
from project_1.client import AssistantError, call_model
from project_1.context import hybrid_reduce, prepare_context
from project_1.conversation import load_conversation
from project_1.prompts.loader import load_prompt

def word_count(text: str, model: str) -> int:
    return len(text.split())

def test_context_keeps_recent_complete_turns(monkeypatch) -> None:
    # Temporaly substirute count_tokens with word_count -> deterministic and easly understandable test
    monkeypatch.setattr(context_module, "count_tokens", word_count)
    # 2 turns history, follow up will be next question asked
    history = [
        {"role": "user", "content": "old user message"},
        {"role": "assistant", "content": "old assistant response"},
        {"role": "user", "content": "recent user message"},
        {"role": "assistant", "content": "recent assistant response"},
    ]

    # Prepare context using max 29 tokens
    messages, estimated_tokens, removed_turns, summary_usage = prepare_context(
        "system rules",
        history,
        "follow up",
        max_input_tokens=29,
        model="test-model",
    )

    assert [message["content"] for message in messages] == [
        "recent user message",
        "recent assistant response",
        "follow up",
    ]
    assert removed_turns == 1
    assert summary_usage is None
    assert estimated_tokens <= 29
    assert history[0]["content"] == "old user message"


def test_oversized_current_message_is_rejected(monkeypatch) -> None:
    monkeypatch.setattr(context_module, "count_tokens", word_count)

    with pytest.raises(AssistantError) as raised:
        prepare_context(
            "system rules",
            [],
            "one two three four five six seven eight nine ten",
            max_input_tokens=20,
            model="test-model",
        )

    assert raised.value.family == "context_overflow"
    assert "shorten" in str(raised.value)
    

# Test passes only if error is generated    
def test_incomplete_history_is_rejected() -> None:
    with pytest.raises(ValueError, match="complete user/assistant turns"):
        prepare_context(
            "rules",
            [{"role": "user", "content": "orphan"}],
            "next",
            max_input_tokens=100,
            model="test-model",
        )
        
        
def test_context_count_includes_message_overhead_and_reply_primer(monkeypatch) -> None:
    monkeypatch.setattr(context_module, "count_tokens", word_count)

    _, estimated_tokens, _, _ = prepare_context(
        "system rules",
        [],
        "follow up",
        max_input_tokens=15,
        model="test-model",
    )

    # 2 instruction words + 4 overhead + 2 user words + 4 overhead + 3 primer.
    assert estimated_tokens == 15
    

def test_context_count_includes_json_mode_message(monkeypatch) -> None:
    monkeypatch.setattr(context_module, "count_tokens", word_count)

    _, estimated_tokens, _, _ = prepare_context(
        "valid JSON object",
        [],
        "follow up",
        max_input_tokens=25,
        model="test-model",
    )

    # Instructions, resident message, JSON developer message, and reply primer.
    assert estimated_tokens == 25
    with pytest.raises(AssistantError, match="shorten"):
        prepare_context(
            "valid JSON object",
            [],
            "follow up",
            max_input_tokens=24,
            model="test-model",
        )
        
        
def test_v5_and_v6_keep_distinct_conversation_instructions() -> None:
    single_turn = load_prompt("instruction", "v5")
    multi_turn = load_prompt("instruction", "v6")

    assert "check independently whether its value is explicitly present" in single_turn
    assert "continuous conversation" not in single_turn
    assert "continuous conversation" in multi_turn
    assert "later correction" in multi_turn
    assert "older turns are absent" in multi_turn
    assert "Return exactly one valid JSON object with these fields:" in single_turn
    assert "OUTPUT CONTRACT:" in multi_turn


VALID_OUTPUT = {
    "answer": "Please contact the relevant Principality office.",
    "fields": {
        "person_name": None,
        "reference_number": None,
        "amount": None,
        "date": None,
    },
    "urgency_level": "routine",
    "urgency_rationale": "No urgent signal was stated.",
}


# Mock per non fare vere chiamate durante i test
class Response:
    def __init__(self, text: str, response_id: str = "response-1"):
        self.output_text = text
        self.model = "test-model"
        self.id = response_id
        self.usage = {"input_tokens": 20, "output_tokens": 10, "total_tokens": 30}

    def model_dump(self, mode="json"):
        return {"id": self.id}
    
class Responses:
    def __init__(self, outputs=None):
        self.calls = []
        self.outputs = list(outputs or [json.dumps(VALID_OUTPUT)])

    def create(self, **kwargs):
        self.calls.append(kwargs)
        text = self.outputs.pop(0)
        return Response(text, f"response-{len(self.calls)}")


class Client:
    def __init__(self, outputs=None):
        self.responses = Responses(outputs)
        

def commit_turn(history, result) -> None:
    history[:] = result["messages"] #put user_input(result["messages"]) in history
    history.append({"role": "assistant", "content": result["raw_output"]})
    
    
def test_second_message_contains_the_first_turn() -> None:
    client = Client([json.dumps(VALID_OUTPUT), json.dumps(VALID_OUTPUT)])
    # start with an empty history
    history = []

    first = answer_turn("My first question", history, "turn-1", api_client=client)
    commit_turn(history, first) #add answer
    answer_turn("What about the deadline?", history, "turn-2", api_client=client)

    second_input = client.responses.calls[1]["input"] #take second call input
    assert [message["role"] for message in second_input] == [
        "developer",
        "user",
        "assistant",
        "user",
    ]
    assert second_input[0]["content"] == "Return a valid json object."
    assert second_input[1]["content"] == "My first question"
    assert "Please contact" in second_input[2]["content"]
    assert client.responses.calls[1]["text"] == {"format": {"type": "json_object"}}
    
    
    
def test_later_correction_is_sent_with_the_earlier_turn() -> None:
    client = Client([json.dumps(VALID_OUTPUT), json.dumps(VALID_OUTPUT)])
    history = []
    first = answer_turn("My reference is OLD-123", history, "turn-1", api_client=client)
    commit_turn(history, first)

    answer_turn("Correction: it is NEW-456", history, "turn-2", api_client=client)

    input_messages = client.responses.calls[1]["input"]
    assert [message["content"] for message in input_messages[1:]] == [
        "My reference is OLD-123",
        json.dumps(VALID_OUTPUT),
        "Correction: it is NEW-456",
    ]
    assert "later correction" in client.responses.calls[1]["instructions"]
  
    
def test_plain_text_model_call_does_not_request_json_mode() -> None:
    client = Client(["Summary of the earlier conversation."])

    result = call_model(
        "Summarize the conversation.",
        "An earlier resident message.",
        api_client=client,
    )

    assert result.output_text == "Summary of the earlier conversation."
    assert client.responses.calls[0]["input"] == "An earlier resident message."
    assert "text" not in client.responses.calls[0]
    
    
def test_failed_turn_does_not_change_memory() -> None:
    class FailingResponses:
        def create(self, **kwargs):
            raise RuntimeError("model failed")

    class FailingClient:
        responses = FailingResponses()

    history = [
        {"role": "user", "content": "Saved question"},
        {"role": "assistant", "content": "Saved answer"},
    ]
    original_history = list(history)

    with pytest.raises(AssistantError):
        answer_turn("Do not save this", history, "turn-2", api_client=FailingClient())

    assert history == original_history
    
    
    
    
def test_load_conversation_selects_one_conversation(tmp_path) -> None:
    path = tmp_path / "conversations.json"
    path.write_text(
        json.dumps(
            [
                {
                    "conversation_id": "one",
                    "messages": [
                        {"role": "user", "content": "Question"},
                        {"role": "assistant", "content": "Answer"},
                    ],
                },
                {"conversation_id": "two", "messages": []},
            ]
        ),
        encoding="utf-8",
    )

    conversation_id, messages = load_conversation(path, "one")

    assert conversation_id == "one"
    assert messages[0]["content"] == "Question"
    with pytest.raises(ValueError, match="Choose a conversation"):
        load_conversation(path)
        
        
# Generate 6 turn history -> 72 tokens (counting overhead)
def _history_for_hybrid_test() -> list[dict[str, str]]:
    return [
        {"role": "user", "content": f"Question {index}"}
        if index % 2 == 0
        else {"role": "assistant", "content": f"Answer {index}"}
        for index in range(12)
    ]
    
    
def test_hybrid_keeps_history_that_is_within_budget(monkeypatch) -> None:
    monkeypatch.setattr(context_module, "count_tokens", word_count)
    client = Client()
    history = _history_for_hybrid_test()

    reduced, summary_usage = hybrid_reduce(
        history,
        max_tokens=72,
        model="test-model",
        api_client=client,
    )

    assert reduced == history
    assert summary_usage is None
    assert client.responses.calls == []
    
    
    
def test_hybrid_summarizes_history_moderately_over_budget(monkeypatch) -> None:
    monkeypatch.setattr(context_module, "count_tokens", word_count)
    summary = "Keep the corrected facts."
    client = Client([summary])
    history = _history_for_hybrid_test()

    reduced, summary_usage = hybrid_reduce(
        history,
        max_tokens=60,
        model="test-model",
        api_client=client,
    )

    assert len(client.responses.calls) == 1
    assert client.responses.calls[0]["input"] == history[:6]
    assert "text" not in client.responses.calls[0]
    assert reduced[0]["content"] == context_module.SUMMARY_LABEL
    assert reduced[1]["content"] == summary
    assert reduced[2]["content"] == "Question 6"
    assert len(reduced) == 8
    assert summary_usage == {
        "input_tokens": 20,
        "output_tokens": 10,
        "total_tokens": 30,
    }
    
    
def test_hybrid_trims_history_severely_over_budget(monkeypatch) -> None:
    monkeypatch.setattr(context_module, "count_tokens", word_count)
    client = Client()

    reduced, summary_usage = hybrid_reduce(
        _history_for_hybrid_test(),
        max_tokens=40,
        model="test-model",
        api_client=client,
    )

    assert len(reduced) == 6
    assert reduced[0]["content"] == "Question 6"
    assert summary_usage is None
    assert client.responses.calls == []