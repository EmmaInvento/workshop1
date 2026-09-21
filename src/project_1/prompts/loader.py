"""Location-independent prompt loading."""

from pathlib import Path

PROMPTS_DIR = Path(__file__).resolve().parent


def load_prompt(name: str) -> str:
    """Load a named UTF-8 prompt without depending on the working directory."""
    return (PROMPTS_DIR / f"{name}.txt").read_text(encoding="utf-8").strip()