"""Unit tests for evaluation task and aggregation behavior."""

import json
from pathlib import Path

from project_1.evaluation.run_experiment import run_evaluation
from project_1.evaluation.experiment_task import run_task


def structured_output(*, urgency_level: str = "routine") -> dict[str, object]:
    return {
        "answer": "Contact the municipal office.",
        "fields": {
            "person_name": None,
            "reference_number": None,
            "amount": None,
            "date": None,
        },
        "urgency_level": urgency_level,
        "urgency_rationale": "The request contains no immediate hazard.",
    }


def test_task_records_contract_failure_without_raising() -> None:
    result = run_task("Question", model_call=lambda instructions, user_input: "invalid")

    assert result["contract_valid"] is False
    assert result["errors"]


def test_runner_aggregates_dimensions_and_tags(tmp_path: Path) -> None:
    dataset = {
        "dataset_id": "test-v1",
        "version": 1,
        "cases": [
            {
                "input": {"text": "Extract this"},
                "output": {"fields": structured_output()["fields"]},
                "metadata": {"case_id": "extract-001", "tag": "representative"},
            },
            {
                "input": {"text": "Assess this"},
                "output": {"urgency_level": "urgent"},
                "metadata": {"case_id": "urgency-001", "tag": "edge"},
            },
        ],
    }
    dataset_path = tmp_path / "dataset.json"
    dataset_path.write_text(json.dumps(dataset), encoding="utf-8")

    def task(user_input: str) -> dict[str, object]:
        urgency = "urgent" if user_input == "Assess this" else "routine"
        return {
            "raw_output": "{}",
            "output": structured_output(urgency_level=urgency),
            "contract_valid": True,
            "errors": [],
        }

    result = run_evaluation(
        dataset_path,
        task=task,
        evaluators={
            "information_extraction": {
                "fields": lambda output, expected: (
                    output["fields"] == expected["fields"]
                )
            },
            "urgency_assessment": {
                "urgency": lambda output, expected: (
                    output["urgency_level"] == expected["urgency_level"]
                )
            },
        },
        prompt_version="test-prompt",
    )

    assert result["passed"] is True
    assert result["aggregates"]["information_extraction"]["pass_rate"] == 1.0
    assert result["aggregates"]["urgency_assessment"]["pass_rate"] == 1.0
    assert result["tag_aggregates"]["edge"]["pass_rate"] == 1.0