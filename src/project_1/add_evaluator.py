import os
from .config import PHOENIX_BASE_URL
from phoenix.client import Client
from phoenix.client.experiments import evaluate_experiment

# Import new added evaluator from .evaluators and put name in evaluate_experiment
from .evaluators import summary_within_limit


def main() -> None:
    # Replace with a real experiment ID (printed in the Phoenix UI, or the
    # id of an experiment created by run_experiment.py). Set it via the
    # EXPERIMENT_ID environment variable.
    experiment_id = os.getenv("EXPERIMENT_ID")
    if not experiment_id:
        raise SystemExit(
            "Set EXPERIMENT_ID to an existing experiment id, e.g.\n"
            "  EXPERIMENT_ID= uv run add_evaluator.py"
        )

    px_client = Client(base_url=PHOENIX_BASE_URL)
    experiment = px_client.experiments.get_experiment(experiment_id=experiment_id)

    evaluate_experiment(
        experiment=experiment,
        evaluators=[summary_within_limit],
        client=px_client,
    )
    print(f"Added 'summary_within_limit' to experiment {experiment_id}.")



#Run main only if this file is executed directly
if __name__ == "__main__":
    main()