# src/support_classifier/run_experiment.py
import os
from phoenix.client import Client
from phoenix.client.experiments import run_experiment
from .config import MODEL_NAME, PHOENIX_BASE_URL
from .tracing import setup_tracing

DATASET_NAME = "municipal-assistent-golden"


def _model_slug() -> str:
    return MODEL_NAME.rsplit("/", 1)[-1].replace(".", "").replace("-", "")


def main() -> None:
    setup_tracing()

    from .evaluators import urgency_level_correct, contract_valid, answer_within_limit, rationale_within_limit, name_correct, reference_number_correct, amount_correct, date_correct
    from .experiment_task import PROMPT_VERSION, answer_question

    dry_run_env = os.getenv("DRY_RUN")
    dry_run: bool | int = int(dry_run_env) if dry_run_env else False
    version_id = os.getenv("DATASET_VERSION")
    if not version_id and not dry_run:
        raise RuntimeError("Set DATASET_VERSION for a recorded experiment")

    client = Client(base_url=PHOENIX_BASE_URL)
    dataset = client.datasets.get_dataset(
        dataset=DATASET_NAME,
        version_id=version_id or None,
    )
    purpose = (
        "dryrun" if dry_run else ("baseline" if PROMPT_VERSION == "v1" else "candidate")
    )
    name = f"{PROMPT_VERSION}-{_model_slug()}-{purpose}"

    run_experiment(
        dataset=dataset,
        task=answer_question,
        evaluators=[contract_valid, urgency_level_correct, answer_within_limit, rationale_within_limit, name_correct, reference_number_correct, amount_correct, date_correct],
        experiment_name=name,
        experiment_description=(
            f"{purpose.capitalize()} run with prompt {PROMPT_VERSION} on {MODEL_NAME}; "
            f"dataset version {dataset.version_id}."
        ),
        experiment_metadata={
            "prompt_version": PROMPT_VERSION,
            "model": MODEL_NAME,
            "dataset_version": dataset.version_id,
            "max_output_tokens": 1024,
            "purpose": purpose,
        },
        client=client,
        dry_run=dry_run,
    )
    print(f"Ran experiment '{name}' on dataset version {dataset.version_id}.")