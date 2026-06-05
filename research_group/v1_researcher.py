"""V1 Researcher — Single-Context Glia researcher with shell access.

This is intentionally separate from the V2 Researcher in `researcher.py`. The
two configurations test different architectures and must not share code paths
that could subtly affect their behavior in the H2 ablation.

Differences from V2 Researcher:
  - Runs experiments DIRECTLY via tools; no "orchestrator runs experiments"
    delegation pattern.
  - System prompt is V1_RESEARCHER_SYSTEM_PROMPT (no findings_board /
    supervisor_memos / evaluator_directive / killed_directions templating).
  - No skill injection (`/scientific-critical-thinking`) — V1 is the
    no-skills baseline by design.
  - Task-specific knowledge (mission, dead ends, CLI templates, metrics) is
    loaded from an external markdown file at construction time so the same
    framework can evaluate against TimesFM, CIFAR-10, MNIST, etc.
"""
from __future__ import annotations

import datetime
from pathlib import Path
from typing import Any

from .llm import LanguageModel
from .task_context import load_task_context
from .tools import TOOL_DEFINITIONS, ToolExecutor
from .v1_prompts import V1_RESEARCHER_SYSTEM_PROMPT


class V1Researcher:
    """V1 Researcher — single-context, shell access, executes directly."""

    SUMMARY_NUDGE_PROMPT = (
        "[SUPERVISOR] You are nearing your tool-iteration budget for this turn. "
        "STOP calling tools now. Summarize what you found, what you concluded, "
        "and what you propose for the next turn. Use plain text."
    )

    def __init__(
        self,
        model: LanguageModel,
        executor: ToolExecutor,
        task_context_path: str | Path | None = None,
        max_tokens: int = 8096,
        max_tool_iterations: int = 20,
        summary_nudge_offset: int = 5,
    ):
        self.model = model
        self.executor = executor
        self.task_context_path = task_context_path
        self.max_tokens = max_tokens
        self.max_tool_iterations = max_tool_iterations
        self.summary_nudge_offset = summary_nudge_offset

    def _build_system_prompt(self, region: str) -> str:
        task_context = load_task_context(
            self.task_context_path, region=region, model=self.model.model
        )
        return V1_RESEARCHER_SYSTEM_PROMPT.format(task_context=task_context)

    def take_turn(
        self,
        conversation_history: list[dict],
        region: str = "us",
        on_tool_call: Any = None,
        on_tool_result: Any = None,
        wall_deadline: datetime.datetime | None = None,
    ) -> tuple[str, list[dict], int, int]:
        """Run one V1 Researcher turn.

        Args:
            conversation_history: Full message history (user/assistant alternating).
                In V1 this includes prior Supervisor messages (single-context).
            region: Task-variant key passed into the task-context template
                (e.g., "us", "china" for TimesFM regions). For tasks without
                variants this string is still substituted but typically ignored.
            on_tool_call: Optional callback(tool_name, tool_input).
            on_tool_result: Optional callback(tool_name, result_str).

        Returns:
            (final_text, new_messages, input_tokens, output_tokens).
        """
        system_prompt = self._build_system_prompt(region=region)

        messages = list(conversation_history)
        new_messages: list[dict] = []
        all_text_parts: list[str] = []

        turn_input_tokens = 0
        turn_output_tokens = 0
        iteration = 0
        summary_nudge_iter = max(2, self.max_tool_iterations - self.summary_nudge_offset + 1)
        nudge_sent = False

        while True:
            iteration += 1

            # In-turn wall-clock check (mirrors V2 Researcher; see comment
            # there). Without this, V1's tool loop can run for hours past
            # the orchestrator's per-turn budget — observed in pilot v10
            # where V1 turn 1 hit the outer 4h watchdog with no diagnostic
            # state on disk.
            if wall_deadline is not None and datetime.datetime.now() >= wall_deadline:
                marker = "[WALL_TIMEOUT] Researcher exceeded wall-clock budget mid-turn."
                if all_text_parts:
                    final_text = "\n".join(all_text_parts).strip() + "\n\n" + marker
                else:
                    final_text = marker
                return final_text, new_messages, turn_input_tokens, turn_output_tokens

            if iteration > self.max_tool_iterations:
                cap_msg = "[WARNING] Max tool iterations reached. Returning partial results."
                if all_text_parts:
                    final_text = "\n".join(all_text_parts).strip() + "\n\n" + cap_msg
                else:
                    final_text = cap_msg
                return final_text, new_messages, turn_input_tokens, turn_output_tokens

            if iteration == summary_nudge_iter and not nudge_sent:
                nudge_msg = {"role": "user", "content": self.SUMMARY_NUDGE_PROMPT}
                messages.append(nudge_msg)
                new_messages.append(nudge_msg)
                nudge_sent = True

            response = self.model.generate(
                messages=messages,
                system=system_prompt,
                tools=TOOL_DEFINITIONS,
                max_tokens=self.max_tokens,
            )

            turn_input_tokens += response.input_tokens
            turn_output_tokens += response.output_tokens

            text_parts = []
            if response.text:
                text_parts.append(response.text)
                all_text_parts.append(response.text)

            tool_calls = response.tool_calls

            assistant_content = []
            if response.text:
                assistant_content.append({"type": "text", "text": response.text})
            for call in tool_calls:
                tool_use_dict = {
                    "type": "tool_use",
                    "id": call.id,
                    "name": call.name,
                    "input": call.input,
                }
                if call.thought_signature:
                    tool_use_dict["thought_signature"] = call.thought_signature
                assistant_content.append(tool_use_dict)

            if assistant_content:
                assistant_msg = {"role": "assistant", "content": assistant_content}
                messages.append(assistant_msg)
                new_messages.append(assistant_msg)

            if not tool_calls:
                final_text = "\n".join(all_text_parts).strip()
                return final_text, new_messages, turn_input_tokens, turn_output_tokens

            tool_results = []
            for call in tool_calls:
                if on_tool_call:
                    on_tool_call(call.name, call.input)

                result_str = self.executor.execute(call.name, call.input)

                if on_tool_result:
                    on_tool_result(call.name, result_str)

                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": call.id,
                    "name": call.name,
                    "content": result_str,
                })

            user_tool_msg = {"role": "user", "content": tool_results}
            messages.append(user_tool_msg)
            new_messages.append(user_tool_msg)
