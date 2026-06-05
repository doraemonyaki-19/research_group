"""Researcher agent: hypothesis-driven experimenter with tool access."""
from __future__ import annotations

import datetime
from pathlib import Path
from typing import Any

from .llm import LanguageModel

from .prompts import RESEARCHER_SYSTEM_PROMPT
from .skill_loader import load_skill_content
from .task_context import load_task_context
from .tools import TOOL_DEFINITIONS, ToolExecutor


class Researcher:
    """Researcher agent that plans experiments, runs tools, and reports findings.

    In ResearchGroup, multiple researchers run in parallel, each with a unique ID
    and exploring different hypotheses. They share a read-only findings board
    to avoid duplicating work.
    """

    # When the inner tool loop is `summary_nudge_offset` iterations away
    # from the cap, inject a user message asking the model to stop calling
    # tools and produce its findings. Some models (notably Gemini 3.1 Pro
    # Preview) prefer to call tools silently and never produce narrative
    # text without an explicit prompt — leading to a loop that hits the
    # iteration cap with no findings on the board.
    SUMMARY_NUDGE_PROMPT = (
        "[ORCHESTRATOR] You are nearing your tool-iteration budget for this "
        "turn. STOP calling tools now. Produce your findings as plain text, "
        "ending with the **## Findings for Board** section in the format "
        "specified in the system prompt. Subsequent turns can resume tool use."
    )

    def __init__(
        self,
        model: LanguageModel,
        executor: ToolExecutor,
        researcher_id: str = "R1",
        max_tokens: int = 8096,
        max_tool_iterations: int = 20,
        summary_nudge_offset: int = 5,
        task_context_path: str | Path | None = None,
    ):
        self.model = model
        self.executor = executor
        self.researcher_id = researcher_id
        self.max_tokens = max_tokens
        self.max_tool_iterations = max_tool_iterations
        self.summary_nudge_offset = summary_nudge_offset
        self.task_context_path = task_context_path

    def _build_system_prompt(
        self,
        turn_number: int,
        findings_board: str,
        supervisor_memos: str,
        evaluator_directive: str,
        killed_directions: str,
        region: str,
    ) -> str:
        """Format the researcher system prompt with current state."""
        skill_content = load_skill_content("scientific-critical-thinking")
        task_context = load_task_context(
            self.task_context_path, region=region, model=self.model.model
        )
        return RESEARCHER_SYSTEM_PROMPT.format(
            researcher_id=self.researcher_id,
            turn_number=turn_number,
            findings_board=findings_board or "(empty — first turn)",
            supervisor_memos=supervisor_memos or "(none yet)",
            evaluator_directive=evaluator_directive or "(none yet)",
            killed_directions=killed_directions or "(none)",
            skill_content=skill_content,
            task_context=task_context,
        )

    def take_turn(
        self,
        conversation_history: list[dict],
        turn_number: int = 1,
        findings_board: str = "",
        supervisor_memos: str = "",
        evaluator_directive: str = "",
        killed_directions: str = "",
        region: str = "us",
        on_tool_call: Any = None,
        on_tool_result: Any = None,
        wall_deadline: datetime.datetime | None = None,
    ) -> tuple[str, list[dict], int, int]:
        """Run one Researcher turn, executing tools until a pure-text response.

        Args:
            conversation_history: Full message history (user/assistant alternating).
            turn_number: Current ResearchGroup turn number.
            findings_board: Shared findings from all researchers (read-only).
            supervisor_memos: Formatted latest memos from all supervisors.
            evaluator_directive: Latest strategic directive from evaluator.
            killed_directions: Directions terminated by evaluator.
            region: Market region (us, china, japan, europe).
            on_tool_call: Optional callback(tool_name, tool_input) for logging.
            on_tool_result: Optional callback(tool_name, result_str) for logging.

        Returns:
            (text_output, new_messages, input_tokens, output_tokens) where new_messages
            are the assistant messages produced this turn (including intermediate tool-use messages).
        """
        system_prompt = self._build_system_prompt(
            turn_number=turn_number,
            findings_board=findings_board,
            supervisor_memos=supervisor_memos,
            evaluator_directive=evaluator_directive,
            killed_directions=killed_directions,
            region=region,
        )

        messages = list(conversation_history)
        new_messages: list[dict] = []
        # Aggregate text across ALL iterations within this turn — not just
        # the final one. Without this, if the LLM emits substantive narrative
        # during tool-using iterations and then ends with a silent "no text +
        # no tool calls" response, the returned output is empty and the
        # caller sees a fabricated-looking blank turn. (May 2026 V1 stall
        # failure mode.)
        all_text_parts: list[str] = []

        turn_input_tokens = 0
        turn_output_tokens = 0
        iteration = 0
        # Iteration at which the summary nudge fires. Floor at 2 so we
        # never inject the nudge before the model has had at least one
        # tool-use opportunity. +1 because iteration is incremented at
        # the top of the loop, so we want the check before the model call.
        summary_nudge_iter = max(2, self.max_tool_iterations - self.summary_nudge_offset + 1)
        nudge_sent = False

        while True:
            iteration += 1

            # In-turn wall-clock check. The orchestrator only checks
            # max_wall_seconds at the top of each turn loop iteration, so a
            # single tool-heavy researcher turn could run for hours before
            # the next check fires. Honor the deadline here too — return
            # aggregated narrative + a [WALL_TIMEOUT] marker so the caller
            # can record stop_reason="wall_timeout" with full diagnostic
            # state (not killed via SIGKILL by the outer PS watchdog).
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

            # Inject the findings-summary nudge once, just before the model
            # call at iteration `summary_nudge_iter`. We append to both
            # `messages` (for this turn's API call) and `new_messages` (for
            # the persisted conversation history) so the next turn sees the
            # transcript faithfully.
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
                # Pass through Gemini 3.x thought_signature so the next turn's
                # message round-trip carries it back to the model. None for
                # other providers; AnthropicModel strips it before sending.
                if call.thought_signature:
                    tool_use_dict["thought_signature"] = call.thought_signature
                assistant_content.append(tool_use_dict)

            if assistant_content:
                assistant_msg = {"role": "assistant", "content": assistant_content}
                messages.append(assistant_msg)
                new_messages.append(assistant_msg)

            if not tool_calls:
                # Use the aggregated text from all iterations, not just this
                # one — see all_text_parts comment above.
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
