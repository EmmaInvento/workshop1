import os
import subprocess
from pathlib import Path


def code_provenance() -> dict[str, str]:
    """Return explicit code revision and working-tree evidence."""
    if revision := os.getenv("EVAL_CODE_REVISION"):
        return {
            "code_revision": revision,
            "code_state": os.getenv("EVAL_CODE_STATE", "declared"),
        }

    project_dir = Path(__file__).resolve().parents[2]
    try:
        revision_result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=project_dir,
            check=True,
            capture_output=True,
            text=True,
        )
        status_result = subprocess.run(
            ["git", "status", "--porcelain", "--", "."],
            cwd=project_dir,
            check=True,
            capture_output=True,
            text=True,
        )
    except (OSError, subprocess.CalledProcessError):
        return {"code_revision": "unavailable", "code_state": "unavailable"}

    return {
        "code_revision": revision_result.stdout.strip(),
        "code_state": "dirty" if status_result.stdout.strip() else "clean",
    }