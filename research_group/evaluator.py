"""Evaluator agent: strategic authority with kill/redirect/terminate powers."""
from __future__ import annotations

from pathlib import Path

from .llm import LanguageModel

from .prompts import EVALUATOR_SYSTEM_PROMPT
from .skill_loader import load_skill_content
from .task_context import load_task_context


class Evaluator:
    """Evaluator agent — the strategic authority in ResearchGroup.

    Fires every 3 turns or on escalation from supervisors (revised 2026-05-08;
    previously every 9 turns). Has access to
    the full findings board and all supervisor memos. Can kill unproductive
    directions, redirect to new ones, or terminate the entire run.

    Has access to broad literature context (recent patents, ArXiv publications)
    for evaluating whether research directions align with state of the art.

    Uses the peer-review skill framework for structured evaluation:
    initial assessment → methodological rigor → statistical rigor →
    reproducibility → issue classification (major/minor) → verdict.
    In Claude Code native mode, the orchestrator invokes /peer-review
    before the evaluator agent call.
    """

    def __init__(
        self,
        model: LanguageModel,
        max_tokens: int = 4096,
        task_context_path: str | Path | None = None,
    ):
        self.model = model
        self.max_tokens = max_tokens
        self.task_context_path = task_context_path

    def _build_system_prompt(
        self,
        turn_number: int,
        findings_board: str,
        supervisor_memos: str,
        active_directions: str,
        killed_directions: str,
        region: str,
    ) -> str:
        skill_content = load_skill_content("peer-review")
        task_context = load_task_context(
            self.task_context_path, region=region, model=self.model.model
        )
        return EVALUATOR_SYSTEM_PROMPT.format(
            turn_number=turn_number,
            findings_board=findings_board or "(empty — no experiments yet)",
            supervisor_memos=supervisor_memos or "(none yet)",
            active_directions=active_directions or "(none defined yet)",
            killed_directions=killed_directions or "(none)",
            skill_content=skill_content,
            task_context=task_context,
        )

    def take_turn(
        self,
        turn_number: int,
        findings_board: str = "",
        supervisor_memos: str = "",
        active_directions: str = "",
        killed_directions: str = "",
        region: str = "us",
    ) -> tuple[str, int, int]:
        """Produce a strategic evaluation for this cycle.

        Args:
            turn_number: Current ResearchGroup turn number.
            findings_board: Full findings board content (not trimmed).
            supervisor_memos: Formatted latest memos from all 3 supervisors.
            active_directions: Currently active research directions.
            killed_directions: Previously killed directions.

        Returns:
            Tuple of (evaluator_text, input_tokens, output_tokens) where evaluator_text
            possibly contains:
            - [KILL: direction_name] — terminate a direction
            - [REDIRECT: description] — open a new direction
            - [TERMINATE] — end the entire run
        """
        system_prompt = self._build_system_prompt(
            turn_number=turn_number,
            findings_board=findings_board,
            supervisor_memos=supervisor_memos,
            active_directions=active_directions,
            killed_directions=killed_directions,
            region=region,
        )

        response = self.model.generate(
            messages=[{
                "role": "user",
                "content": (
                    "Conduct your strategic review. Assess each active direction, "
                    "evaluate the measurement framework, and issue directives for "
                    "the next cycle. Be decisive — kill marginal directions early."
                ),
            }],
            system=system_prompt,
            tools=[],
            max_tokens=self.max_tokens,
        )

        return response.text, response.input_tokens, response.output_tokens

    @staticmethod
    def parse_directives(output: str) -> dict:
        """Parse evaluator output for kill/redirect/terminate directives.

        Returns:
            {
                "terminate": bool,
                "kills": list[str],       # direction names
                "redirects": list[str],   # new direction descriptions
            }
        """
        result = {"terminate": False, "kills": [], "redirects": []}

        for line in output.split("\n"):
            stripped = line.strip()
            if stripped.startswith("[TERMINATE]"):
                result["terminate"] = True
            elif stripped.startswith("[KILL:"):
                # Extract direction name from [KILL: direction_name]
                name = stripped.split("[KILL:", 1)[1].rstrip("]").strip()
                if name:
                    result["kills"].append(name)
            elif stripped.startswith("[REDIRECT:"):
                desc = stripped.split("[REDIRECT:", 1)[1].rstrip("]").strip()
                if desc:
                    result["redirects"].append(desc)

        return result
