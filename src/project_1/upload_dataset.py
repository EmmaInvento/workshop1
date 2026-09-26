import json
from pathlib import Path

from phoenix.client import Client

from .config import PHOENIX_BASE_URL

DATASET_NAME = "municipal-assistent-golden"
CASES_FILE = "golden_set_v0"


def load_cases(name: str) -> list[dict]:
    """Load the golden set from the package's cases directory."""
    path = Path(__file__).parent / "cases" / f"{name}.json"
    return json.loads(path.read_text(encoding="utf-8"))


def upload_golden_set(
    cases: list[dict],
    dataset_name: str,
) -> None:
    """Upload golden-set cases to a Phoenix
    dataset."""
    px_client = Client(base_url=PHOENIX_BASE_URL)

    examples = [
        {
            "id": case["id"],
            "input": {"text": case["input"]},
            "output": {
                "expected_answer": case["expected_answer"],
                "expected_name": case["expected_name"],
                "expected_reference_number": case["expected_reference_number"],
                "expected_amount": case["expected_amount"],
                "expected_date": case["expected_date"],
                "expected_urgency_level": case["expected_urgency_level"],
                "expected_urgency_rationale": case["expected_urgency_rationale"],
            },
            "metadata": {
                "case_id": case["id"],
                "tag": case.get("tag", "unknown"),
                "note": case.get("note", ""),
                "failure_mode": case.get("failure_mode", ""),
                "source_type": case.get("source_type", ""),
                #"source_trace_id": case.get("source_trace_id", ""),
                "label_status": case.get("label_status", ""),
            },
        }
        for case in cases
    ]

    dataset = px_client.datasets.create_dataset(
        name=dataset_name,
        examples=examples,
    )
    print(f"Dataset: {dataset.name}")
    print(f"Version ID: {dataset.version_id}")
    print(f"Examples: {len(dataset)}")


if __name__ == "__main__":
    cases = load_cases(CASES_FILE)
    upload_golden_set(cases, DATASET_NAME)