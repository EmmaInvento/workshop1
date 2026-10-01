# src/support_classifier/run_experiment.py
import json
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Any


DEFAULT_DATASET_PATH = Path(__file__).with_name("dataset.json")
Task = Callable[[str], Mapping[str, Any]]
Scorer = Callable[[Mapping[str, Any], Mapping[str, Any]], bool]


# Take a dateset of cases, execute task on each case, and evaluate the results with the provided evaluators.
def run_evaluation(
    dataset_path: Path = DEFAULT_DATASET_PATH,
    *,
    task: Task,
    evaluators: Mapping[str, Mapping[str, Scorer]], #evaluators will be grouped according to the dimension of the case (e.g. information_extraction, urgency_assessment)
    prompt_version: str,
) -> dict[str, Any]:
    """Run a task and its evaluators over the fixed dataset."""
    dataset = _load_dataset(dataset_path)
    cases: list[dict[str, Any]] = []
    aggregates = {dimension: _empty_aggregate() for dimension in evaluators} #will contain the aggregate results for each dimension (e.g. information_extraction, urgency_assessment)
    tag_aggregates: dict[str, dict[str, int | float]] = {}

    for case in dataset["cases"]:
        metadata = case["metadata"]
        case_id = metadata["case_id"]
        tag = metadata.get("tag", "unknown")
        dimension = _dimension_for_case(case_id) #assign dimension according to the case_id (e.g. extract- or urgency-)
        aggregate = aggregates[dimension]
        aggregate["total"] += 1
        tag_aggregate = tag_aggregates.setdefault(
            tag,
            {"total": 0, "passed": 0, "contract_failures": 0},
        )
        tag_aggregate["total"] += 1
        task_result = task(case["input"]["text"])

        case_result: dict[str, Any] = {
            "case_id": case_id,
            "tag": tag,
            "dimension": dimension,
            "input": case["input"],
            "expected": case["output"],
            "raw_output": task_result.get("raw_output"),
        }
        # If contract validation fails, we skip the scoring and mark the case as failed.
        if not task_result.get("contract_valid"):
            aggregate["contract_failures"] += 1
            tag_aggregate["contract_failures"] += 1
            case_result.update(
                {
                    "contract_valid": False,
                    "passed": False,
                    "errors": task_result.get("errors", []),
                }
            )
            cases.append(case_result)
            continue

        # If contract validation passes, we run the evaluators and compute the aggregate scores.
        output = task_result["output"]
        
        evaluator_scores = {
            name: scorer(output, case["output"]) #write scorer_name followed by True or false depending on whether the scorer passed or failed
            for name, scorer in evaluators[dimension].items() #for each scorer in the dimension
        }
        score_value = sum(evaluator_scores.values()) / len(evaluator_scores)
        passed = all(evaluator_scores.values()) #case passes if all scorers pass
        aggregate["score_sum"] += score_value
        aggregate["passed"] += int(passed)
        tag_aggregate["passed"] += int(passed)
        case_result.update(
            {
                "output": output,
                "contract_valid": True,
                "score": {
                    "score": score_value,
                    "passed": passed,
                    "evaluator_scores": evaluator_scores,
                },
                "passed": passed,
            }
        )
        cases.append(case_result)

    for aggregate in aggregates.values():
        aggregate["pass_rate"] = (
            aggregate["passed"] / aggregate["total"] if aggregate["total"] else 0.0
        )
        aggregate["mean_score"] = (
            aggregate["score_sum"] / aggregate["total"] if aggregate["total"] else 0.0
        )
        del aggregate["score_sum"]

    for aggregate in tag_aggregates.values():
        aggregate["pass_rate"] = aggregate["passed"] / aggregate["total"]

    return {
        "dataset_id": dataset["dataset_id"],
        "dataset_version": dataset["version"],
        "prompt_version": prompt_version,
        "aggregates": aggregates,
        "tag_aggregates": dict(sorted(tag_aggregates.items())),
        "passed": all(case["passed"] for case in cases),
        "cases": cases,
    }
    






def _load_dataset(path: Path) -> Mapping[str, Any]:
    dataset = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(dataset, Mapping) or not isinstance(dataset.get("cases"), list):
        raise TypeError("The evaluation dataset must contain a 'cases' list.")
    return dataset

# Initialization
def _empty_aggregate() -> dict[str, Any]:
    return {
        "total": 0,
        "passed": 0,
        "contract_failures": 0,
        "score_sum": 0.0,
    }

def _dimension_for_case(case_id: str) -> str:
    if case_id.startswith("extract-"):
        return "information_extraction"
    if case_id.startswith("urgency-"):
        return "urgency_assessment"
    raise ValueError(
        f"Cannot select an evaluation dimension for case '{case_id}'. "
        "Use an extract- or urgency- case ID."
    )













































'''

DATASET_NAME = "municipal-assistent-golden"


def _model_slug() -> str:
    return MODEL_NAME.rsplit("/", 1)[-1].replace(".", "").replace("-", "")


def main() -> None:
    setup_tracing()

    from .evaluators import EVALUATOR_VERSION, urgency_level_correct, contract_valid, answer_within_limit, rationale_within_limit, name_correct, reference_number_correct, amount_correct, date_correct
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
    provenance = code_provenance()
    purpose = (
        "dryrun" if dry_run else ("baseline" if PROMPT_VERSION == "v3" else "candidate")
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
            "max_output_tokens": 1024, #will be saved as invocation param
            "evaluator_version": EVALUATOR_VERSION,
            "purpose" : purpose,
            **provenance,
            "dependency_lock": "uv.lock",
            "run_started_at": datetime.now(UTC).isoformat(),
        },
        client=client,
        dry_run=dry_run,
    )
    print(f"Ran experiment '{name}' on dataset version {dataset.version_id}.")
    '''