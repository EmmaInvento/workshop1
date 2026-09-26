"""Location-independent prompt loading."""

from pathlib import Path

PROMPTS_DIR = Path(__file__).resolve().parent


def load_prompt(
    name: str,
    version: str | None = None,
) -> str:
    """Load a prompt file by name and optional version.

    If version is None, load the highest-numbered version.
    Prompt files follow the pattern: {name}_v{N}.txt
    """
    prompts_dir = PROMPTS_DIR
    if version is not None:
        path = prompts_dir / f"{name}_{version}.txt"
        if not path.exists():
            raise FileNotFoundError(f"Prompt not found: {path}")
        return path.read_text(encoding="utf-8").strip()

    # Find highest version number
    candidates = sorted(
        prompts_dir.glob(f"{name}_v*.txt"),
        key=lambda p: int(p.stem.split("_v")[-1]),
    )
    if not candidates:
        raise FileNotFoundError(f"No prompt files for: {name}")
    return candidates[-1].read_text(encoding="utf-8").strip()
