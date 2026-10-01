"""CLI for the Phoenix dataset and evaluation workflow."""
# to be run from terminal - specify run vs upload, dataset name, dataset version, purpose, experiment name, dry run

import argparse
import json
import os
import sys
from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import Any

from phoenix.client import Client
from phoenix.client.experiments import run_experiment

from ..client import AssistantError
from ..config import (
    MODEL_NAME,
    PHOENIX_BASE_URL,
    PROJECT_ROOT,
    PROMPT_VERSION,
    ConfigurationError,
    validate_model_configuration,
)
from ..tracing import setup_tracing
from .run_experiment import DEFAULT_DATASET_PATH
from .evaluators import (
    phoenix_extraction_fields_match,
    phoenix_output_contract_valid,
    phoenix_urgency_level_matches,
)
from .experiment_task import run_dataset_case

DATASET_NAME = "workshop-2-golden"
EVALUATORS = [
    phoenix_output_contract_valid,
    phoenix_extraction_fields_match,
    phoenix_urgency_level_matches,
]


def load_dataset(path: Path) -> Mapping[str, Any]:
    """Read the repository snapshot before creating a Phoenix dataset."""
    dataset = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(dataset, Mapping) or not isinstance(dataset.get("cases"), list):
        raise TypeError("The evaluation dataset must contain a 'cases' list.")
    return dataset


def dataset_examples(dataset: Mapping[str, Any]) -> Iterable[dict[str, Any]]:
    """Map each local case to Phoenix input, reference output, and metadata."""
    for case in dataset["cases"]:
        if not isinstance(case, Mapping):
            raise TypeError("Every evaluation case must be an object.")
        input_data = case.get("input")
        expected = case.get("output")
        metadata = case.get("metadata")
        if not isinstance(input_data, Mapping) or not isinstance(expected, Mapping):
            raise TypeError("Every case must contain input and output objects.")
        if not isinstance(metadata, Mapping):
            raise TypeError("Every case must contain a metadata object.")

        text = input_data.get("text")
        case_id = metadata.get("case_id")
        if not isinstance(text, str) or not text:
            raise ValueError("Every case must contain non-empty input.text.")
        if not isinstance(case_id, str) or not case_id:
            raise ValueError("Every case must contain metadata.case_id.")

        if case_id.startswith("extract-"):
            dimension = "information_extraction"
        elif case_id.startswith("urgency-"):
            dimension = "urgency_assessment"
        else:
            raise ValueError(f"Unsupported case ID: {case_id}")

        phoenix_metadata = dict(metadata)
        phoenix_metadata["dimension"] = dimension
        yield {
            "input": {"text": text},
            "output": dict(expected),
            "metadata": phoenix_metadata,
        }


def upload_dataset(dataset_name: str, dataset_path: Path) -> Any:
    """Create a versioned Phoenix dataset from the local snapshot."""
    dataset = load_dataset(dataset_path)
    client = Client(base_url=PHOENIX_BASE_URL)
    return client.datasets.create_dataset(
        name=dataset_name,
        examples=list(dataset_examples(dataset)),
        dataset_description=(
            f"Municipal Front-Desk golden set from {dataset['dataset_id']} "
            f"version {dataset['version']}."
        ),
    )


def run_phoenix_evaluation(
    *,
    dataset_name: str,
    dataset_version: str | None,
    purpose: str,
    experiment_name: str | None,
    dry_run: bool | int,
) -> Any:
    """Run a persistent Phoenix evaluation over a pinned dataset version."""
    if dataset_version is None and not dry_run:
        raise ValueError("A dataset version is required for a persistent evaluation.")

    validate_model_configuration()
    setup_tracing()
    client = Client(base_url=PHOENIX_BASE_URL)
    dataset = client.datasets.get_dataset(
        dataset=dataset_name,
        version_id=dataset_version,
    )
    model_slug = MODEL_NAME.replace(".", "").replace("-", "")
    name = experiment_name or f"{PROMPT_VERSION}-{model_slug}-{purpose}"
    return run_experiment(
        dataset=dataset,
        task=run_dataset_case,
        evaluators=EVALUATORS,
        experiment_name=name,
        experiment_description=(
            f"{purpose.capitalize()} run with prompt {PROMPT_VERSION} on "
            f"{MODEL_NAME}; dataset version {dataset.version_id}."
        ),
        experiment_metadata={
            "prompt_version": PROMPT_VERSION,
            "model": MODEL_NAME,
            "dataset_name": dataset_name,
            "dataset_version": dataset.version_id,
            "purpose": purpose,
        },
        client=client,
        dry_run=dry_run,
    )


def main() -> int:
    """Parse and run a Phoenix dataset or experiment command."""
    parser = argparse.ArgumentParser(
        description="Manage the municipal dataset and Phoenix evaluations."
    )
    # parser avrà sottocomandi "upload" e "run" per gestire il dataset e le valutazioni
    commands = parser.add_subparsers(dest="command", required=True)
    
    # Sottocomando per caricare un dataset Phoenix
    upload = commands.add_parser("upload", help="Create a Phoenix dataset")
    upload.add_argument("--dataset-name", default=DATASET_NAME)
    upload.add_argument("--dataset-path", default=str(DEFAULT_DATASET_PATH))
    
    # Sottocomando per eseguire una valutazione Phoenix
    run = commands.add_parser("run", help="Run a Phoenix evaluation")
    run.add_argument("--dataset-name", default=DATASET_NAME)
    run.add_argument(
        "--dataset-version",
        default=os.getenv("PHOENIX_DATASET_VERSION"),
    )
    run.add_argument("--purpose", default="baseline")
    run.add_argument("--experiment-name")
    run.add_argument("--dry-run", nargs="?", const=True, type=int)

    args = parser.parse_args() #prende argomenti da terminale e trasforma in oggetto arg
    if args.command == "upload":
        path = Path(args.dataset_path)
        if not path.is_absolute():
            path = PROJECT_ROOT / path
        dataset = upload_dataset(args.dataset_name, path)
        print(
            f"Created Phoenix dataset '{dataset.name}' with {len(dataset)} examples "
            f"(version: {dataset.version_id})."
        )
        return 0
    
    # Sottocomando per eseguire una valutazione Phoenix (run)
    if args.dataset_version is None and args.dry_run is None:
        run.error(
            "--dataset-version (or PHOENIX_DATASET_VERSION) is required for "
            "a persistent evaluation; use --dry-run to test the wiring."
        )

    try:
        result = run_phoenix_evaluation(
            dataset_name=args.dataset_name,
            dataset_version=args.dataset_version,
            purpose=args.purpose,
            experiment_name=args.experiment_name,
            dry_run=args.dry_run if args.dry_run is not None else False,
        )
    except (ConfigurationError, AssistantError) as exc:
        family = getattr(exc, "family", "configuration")
        print(f"Error [{family}]: {exc}", file=sys.stderr)
        return 2

    experiment_id = getattr(result, "id", None)
    print(
        "Phoenix evaluation completed"
        + (f" (id: {experiment_id})" if experiment_id else ".")
    )
    return 0