"""V1 Supervisor — Single-Context Glia generalist supervisor.

This is intentionally separate from the V2 Supervisor in `supervisor.py`.

Differences from V2 Supervisor:
  - One generalist supervisor (V2 has three: Stats, Domain, Methods).
  - No skill injection (V2's supervisor uses scientific-critical-thinking,
    scientific-brainstorming, or timesfm-forecasting depending on role).
  - Sees the FULL Researcher output in a shared conversation context, not
    just the latest turn — V1 is single-context per the Glia paper §4.1.
  - Does not emit specialized escalation signals ([CEILING], [PIVOT], etc.);
    V1 has no Evaluator to escalate to.
  - Loads task-specific context (dead ends, mission, constraints) from an
    external markdown file so the Supervisor can recognize repeated mistakes
    without the framework prompt being task-specific.
"""
from __future__ import annotations

from pathlib import Path

from .llm import LanguageModel
from .task_context import load_task_context
from .v1_prompts import V1_SUPERVISOR_SYSTEM_PROMPT


class V1Supervisor:
    """V1 Supervisor — generalist Socratic critic, no tools."""

    def __init__(
        self,
        model: LanguageModel,
        task_context_path: str | Path | None = None,
        max_tokens: int = 2048,
    ):
        self.model = model
        self.task_context_path = task_context_path
        self.max_tokens = max_tokens

    def _build_system_prompt(self, researcher_output: str, region: str) -> str:
        task_context = load_task_context(
            self.task_context_path, region=region, model=self.model.model
        )
        return V1_SUPERVISOR_SYSTEM_PROMPT.format(
            researcher_output=researcher_output or "(no output yet)",
            task_context=task_context,
        )

    def take_turn(
        self,
        researcher_output: str,
        region: str = "us",
    ) -> tuple[str, int, int]:
        """Produce a Supervisor critique for the latest Researcher output.

        Args:
            researcher_output: The Researcher's text output from the most
                recent turn.
            region: Task-variant key for task_context substitution.

        Returns:
            (memo_text, input_tokens, output_tokens).
        """
        system_prompt = self._build_system_prompt(
            researcher_output=researcher_output,
            region=region,
        )
        response = self.model.generate(
            messages=[{
                "role": "user",
                "content": (
                    "Read the Researcher's most recent output above. Your role is "
                    "to guide the Researcher Socratically: "
                    "(1) ask 2-4 pointed questions that probe the strongest "
                    "weakness in their plan or claim — choose questions whose "
                    "answers would change a decision; "
                    "(2) when the Researcher is on a clearly promising path, "
                    "name the specific evidence that would convince a skeptic "
                    "and ask whether they have it; "
                    "(3) when the Researcher is repeating a pattern from the "
                    "known dead-end list or chasing an unproductive direction, "
                    "name the pattern and ask why this attempt would differ; "
                    "(4) recall earlier results in this conversation if the "
                    "Researcher has drifted from them. "
                    "Do NOT propose algorithms, hyperparameters, code changes, "
                    "or specific commands — that is the Researcher's job. Stay "
                    "under 250 words."
                ),
            }],
            system=system_prompt,
            tools=[],
            max_tokens=self.max_tokens,
        )
        return response.text, response.input_tokens, response.output_tokens
