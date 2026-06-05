"""Loader for task-specific knowledge injected into agent system prompts.

The framework prompts (`v1_prompts.py`, `prompts.py`) are deliberately
task-agnostic. The actual mission, constraints, file paths, CLI templates,
prior findings, and known dead ends for a specific optimization task live in
an external markdown file referenced via `--task-context` (or the
`task_context_path` constructor arg).

Designed for V1 and V2 to share — when V2 is refactored to also load task
context externally, it imports the same `load_task_context` here.
"""
from __future__ import annotations

from pathlib import Path


def load_task_context(path: str | Path | None, region: str | None = None, model: str | None = None) -> str:
    """Read and return the task-context markdown for the active run.

    Args:
        path: Path to the markdown file. If None, returns a minimal placeholder
            so that prompts referencing `{task_context}` still format cleanly
            (useful in unit tests that don't exercise the file path).
        region: Optional region or task-variant key. If supplied and the file
            contains `{region}` placeholders, they are substituted with this
            string. Tasks without regions can pass None.
        model: Optional model name. If supplied and the file contains `{model}`
            placeholders, they are substituted with this string (slashes replaced
            by underscores).

    Returns:
        The (rendered) markdown content as a string. Always at least one
        non-empty paragraph so downstream prompt formatting never fails on
        empty substitution.
    """
    if path is None:
        return "(no task context provided)"

    p = Path(path)
    if not p.exists():
        return f"(task context file not found at {p})"

    content = p.read_text(encoding="utf-8")
    if region is not None:
        content = content.replace("{region}", region)
    if model is not None:
        # Sanitize model name for path usage
        safe_model = model.replace("/", "_").replace("\\", "_")
        content = content.replace("{model}", safe_model)
    return content
