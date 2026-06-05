"""Supervisor agent: domain-expert guidance via Socratic feedback."""
from __future__ import annotations

from pathlib import Path

from .llm import LanguageModel

from .prompts import SUPERVISOR_SYSTEM_PROMPT
from .skill_loader import load_skill_content
from .task_context import load_task_context

# The three supervisor specializations.
SUPERVISOR_ROLES = ("Stats", "Domain", "Methods")

# Default skill assignments used when no explicit `skill_name` is passed to
# Supervisor.__init__. These defaults are TimesFM-specific only for the
# Methods role; Stats and Domain skills are task-agnostic methodology.
#
# For task T2 (hyperparameter search per EVALUATION_PROTOCOL.md §2), the
# Methods skill should be overridden to a task-relevant expert (e.g.
# `cifar-classification`, `hyperparameter-search`, etc.). Pass `skill_name`
# explicitly to Supervisor() or use the harness's --supervisor-skills flag.
DEFAULT_ROLE_SKILLS = {
    "Stats": "scientific-critical-thinking",
    "Domain": "scientific-brainstorming",
    "Methods": "timesfm-forecasting",
}

# Backwards-compat alias — older tests / external code may import this name.
ROLE_SKILLS = DEFAULT_ROLE_SKILLS


class Supervisor:
    """Supervisor agent that reads researcher outputs and provides guidance.

    In ResearchGroup, three supervisors run in parallel — each with a different
    specialization (Stats, Domain, Methods). They write independent memos
    and do NOT see each other's output (prevents anchoring).

    Supervisors fire every turn (revised 2026-05-08; previously every 3 turns).
    """

    def __init__(
        self,
        model: LanguageModel,
        role: str = "Stats",
        max_tokens: int = 2048,
        task_context_path: str | Path | None = None,
        skill_name: str | None = None,
    ):
        if role not in SUPERVISOR_ROLES:
            raise ValueError(f"role must be one of {SUPERVISOR_ROLES}, got {role!r}")
        self.model = model
        self.role = role
        self.max_tokens = max_tokens
        self.task_context_path = task_context_path
        # Per-instance skill — falls back to the role default. For T2
        # (hyperparameter search), the Methods role's default of
        # `timesfm-forecasting` will be wrong; pass the relevant expert
        # skill at construction time instead.
        self.skill_name = skill_name if skill_name is not None else DEFAULT_ROLE_SKILLS[role]

    def _build_system_prompt(
        self,
        turn_number: int,
        researcher_outputs: str,
        findings_board: str,
        escalation_queue: str,
        evaluator_directive: str,
        region: str,
    ) -> str:
        """Format the supervisor system prompt with current state."""
        skill_content = load_skill_content(self.skill_name)
        task_context = load_task_context(
            self.task_context_path, region=region, model=self.model.model
        )

        return SUPERVISOR_SYSTEM_PROMPT.format(
            supervisor_role=self.role,
            turn_number=turn_number,
            researcher_outputs=researcher_outputs,
            findings_board=findings_board or "(empty)",
            escalation_queue=escalation_queue or "(none)",
            evaluator_directive=evaluator_directive or "(none yet)",
            skill_content=skill_content,
            task_context=task_context,
        )

    def take_turn(
        self,
        researcher_outputs: str,
        turn_number: int,
        findings_board: str = "",
        escalation_queue: str = "",
        evaluator_directive: str = "",
        region: str = "us",
    ) -> tuple[str, int, int]:
        """Produce a supervisor memo for this turn.

        Args:
            researcher_outputs: Combined text output from all researchers this turn.
            turn_number: Current ResearchGroup turn number.
            findings_board: Shared findings board content.
            escalation_queue: Any escalation signals from researchers.
            evaluator_directive: Latest strategic directive from evaluator.

        Returns:
            Tuple of (memo_text, input_tokens, output_tokens).
        """
        system_prompt = self._build_system_prompt(
            turn_number=turn_number,
            researcher_outputs=researcher_outputs,
            findings_board=findings_board,
            escalation_queue=escalation_queue,
            evaluator_directive=evaluator_directive,
            region=region,
        )

        response = self.model.generate(
            messages=[{
                "role": "user",
                "content": (
                    f"Review the researchers' outputs above and provide your "
                    f"{self.role} perspective. Focus on your domain of expertise. "
                    f"If all research directions in your domain have reached a "
                    f"satisfactory conclusion, prefix with [APPROVED]."
                ),
            }],
            system=system_prompt,
            tools=[],
            max_tokens=self.max_tokens,
        )

        return response.text, response.input_tokens, response.output_tokens
