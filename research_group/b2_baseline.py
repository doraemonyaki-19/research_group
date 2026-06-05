"""B2 Baseline Orchestrator (Claude Code Freestyle).

This implements a raw, un-architected loop where the LLM is simply given
tools and the prompt, and asked to solve the problem without any of the
ResearchGroup specialized roles, frameworks, or coordination logic.
"""
from __future__ import annotations

import datetime
import json
from pathlib import Path

from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.rule import Rule

from .llm import LanguageModel
from .orchestrator import ResearchGroupResult
from .tools import TOOL_DEFINITIONS, ToolExecutor

console = Console()

B2_SYSTEM_PROMPT = """\
You are an expert AI software engineer and researcher.
Your goal is to optimize the target metric described in the user's prompt.
You have access to tools to read files, run bash commands, and execute code.

Work autonomously to run experiments and find the best solution.
If you believe you have found the best possible solution and can improve no further,
output the exact string: [DONE]
"""

class B2Baseline:
    """B2 Baseline: Raw LLM loop."""

    def __init__(
        self,
        model: LanguageModel,
        executor: ToolExecutor,
        user_task: str,
        output_dir: Path | str,
        max_turns: int = 27,
        quiet: bool = False,
        json_only: bool = False,
        run_metadata: dict | None = None,
        max_wall_seconds: int | None = None,
        max_conversation_turns: int = 6,
    ):
        self.model = model
        self.executor = executor
        self.user_task = user_task
        self.output_dir = Path(output_dir)
        self.max_turns = max_turns
        self.quiet = quiet
        self.json_only = json_only
        self.run_metadata = dict(run_metadata or {})
        self.max_wall_seconds = max_wall_seconds
        self.max_conversation_turns = max_conversation_turns

        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.log_path = self.output_dir / "b2_log.md"
        self.summary_path = self.output_dir / "b2_summary.md"
        self.cost_path = self.output_dir / "costs.json"
        self.run_data_path = self.output_dir / "run_data.json"

        self._turn_history: list[dict] = []
        self._conversation: list[dict] = [{"role": "user", "content": user_task}]

        self.total_input_tokens = 0
        self.total_output_tokens = 0
        self.total_cost = 0.0

    def _print(self, *args, **kwargs) -> None:
        if not self.quiet:
            console.print(*args, **kwargs)

    def _print_exception(self) -> None:
        console.print_exception()

    def run(self) -> ResearchGroupResult:
        started_at = datetime.datetime.now().isoformat(timespec="seconds")
        self._write_log(
            f"# B2 Baseline (Freestyle) Log\n\n"
            f"Started: {started_at}\n"
            f"Max turns: {self.max_turns}\n\n---\n\n"
        )

        self._print(Rule("[bold blue]B2 Baseline (Freestyle)[/bold blue]"))

        stop_reason = "max_turns"

        for turn in range(1, self.max_turns + 1):
            elapsed = (datetime.datetime.now() - datetime.datetime.fromisoformat(started_at)).total_seconds()
            if self.max_wall_seconds is not None and elapsed > self.max_wall_seconds:
                print(f"[B2 wall_timeout] elapsed={elapsed:.0f}s exceeds max_wall_seconds={self.max_wall_seconds}; exiting cleanly with checkpoint", flush=True)
                stop_reason = "wall_timeout"
                turn -= 1  # last completed turn
                break
            cost_so_far = (self.total_input_tokens / 1_000_000 * 3.0) + (self.total_output_tokens / 1_000_000 * 15.0)
            print(f"[B2 turn {turn}/{self.max_turns}] elapsed={elapsed:.0f}s cost=${cost_so_far:.2f} tokens={self.total_input_tokens+self.total_output_tokens}", flush=True)
            self._print(Rule(f"[yellow]Turn {turn} / {self.max_turns}[/yellow]"))

            try:
                response = self.model.generate(
                    messages=self._truncate_conversation(),
                    system=B2_SYSTEM_PROMPT,
                    tools=TOOL_DEFINITIONS,
                    max_tokens=16384,
                )

                self.total_input_tokens += response.input_tokens
                self.total_output_tokens += response.output_tokens
                self.total_cost += self.model.get_cost(response.input_tokens, response.output_tokens)

                text_parts = []
                if response.text:
                    text_parts.append(response.text)
                    assistant_content = [{"type": "text", "text": response.text}]
                else:
                    assistant_content = []

                tool_calls = response.tool_calls
                for call in tool_calls:
                    assistant_content.append({
                        "type": "tool_use",
                        "id": call.id,
                        "name": call.name,
                        "input": call.input,
                    })

                if assistant_content:
                    self._conversation.append({"role": "assistant", "content": assistant_content})

                final_text = "\n".join(text_parts).strip()
                self._log_turn(turn, final_text)

                if final_text:
                    self._print(Panel(
                        Markdown(final_text[:3000] + ("..." if len(final_text) > 3000 else "")),
                        title=f"[green]B2 Agent (Turn {turn})[/green]",
                        border_style="green",
                    ))

                self._turn_history.append({"turn": turn, "role": "b2_agent", "output": final_text})

                if "[DONE]" in final_text:
                    stop_reason = "done"
                    break

                self._checkpoint_run_data(turn, started_at)

                if tool_calls:
                    tool_results = []
                    for call in tool_calls:
                        result_str = self.executor.execute(call.name, call.input)
                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": call.id,
                            "name": call.name,
                            "content": result_str,
                        })
                    self._conversation.append({"role": "user", "content": tool_results})
                else:
                    # If no tools were used and didn't say [DONE], prompt to continue or stop
                    self._conversation.append({
                        "role": "user",
                        "content": "Please continue your work, or output [DONE] if you are finished."
                    })

            except Exception:
                self._print_exception()
                stop_reason = "error"
                break

        # Final cost is already tracked in self.total_cost
        estimated_cost = self.total_cost

        result = ResearchGroupResult(
            turns_completed=turn,
            stop_reason=stop_reason,
            output_dir=self.output_dir,
            log_path=self.log_path,
            summary_path=self.summary_path,
            findings_board_path=self.output_dir / "dummy.md",
            num_researchers=1,
            total_input_tokens=self.total_input_tokens,
            total_output_tokens=self.total_output_tokens,
            estimated_cost=estimated_cost,
            turn_history=self._turn_history,
        )

        self._write_summary(result)
        self._write_costs(result)
        self._write_run_data(
            result,
            started_at=started_at,
            completed_at=datetime.datetime.now().isoformat(timespec="seconds"),
        )
        return result

    def _truncate_conversation(self) -> list[dict]:
        """Sliding-window cap — same logic as V1/V2 orchestrators."""
        full = self._conversation
        if len(full) <= 1:
            return full
        first = [full[0]]
        rest = full[1:]
        window = self.max_conversation_turns * 3
        if len(rest) <= window:
            return full
        return first + rest[-window:]

    def _log_turn(self, turn: int, output: str) -> None:
        if self.json_only:
            return
        with open(self.log_path, "a", encoding="utf-8") as f:
            f.write(f"## Turn {turn}\n\n{output}\n\n---\n\n")

    def _write_log(self, content: str) -> None:
        if self.json_only:
            return
        with open(self.log_path, "w", encoding="utf-8") as f:
            f.write(content)

    def _write_summary(self, result: ResearchGroupResult) -> None:
        if self.json_only:
            return
        lines = [
            "# B2 Run Summary\n\n",
            f"**Stop reason:** {result.stop_reason}  \n",
            f"**Turns completed:** {result.turns_completed}  \n",
            f"**Estimated Cost:** ${result.estimated_cost:.2f} ({result.total_input_tokens:,} in / {result.total_output_tokens:,} out)  \n",
            "---\n\n",
        ]
        with open(result.summary_path, "w", encoding="utf-8") as f:
            f.write("".join(lines))

    def _checkpoint_run_data(self, turn: int, started_at: str) -> None:
        # Forensic snapshot for watchdog-killed runs. Overwritten by the final
        # _write_run_data when the run completes normally.
        estimated_cost = (self.total_input_tokens / 1_000_000 * 3.0) + (self.total_output_tokens / 1_000_000 * 15.0)
        run_data = {
            "metadata": {
                **self.run_metadata,
                "loop_class": "B2Baseline",
                "max_turns": self.max_turns,
                "num_researchers": 1,
                "started_at": started_at,
                "completed_at": None,
            },
            "result": {
                "stop_reason": "in_progress",
                "turns_completed": turn,
                "directions_explored": 0,
                "directions_killed": 0,
                "killed_directions": [],
                "active_directions": [],
                "total_input_tokens": self.total_input_tokens,
                "total_output_tokens": self.total_output_tokens,
                "estimated_cost_usd": estimated_cost,
            },
            "turn_history": list(self._turn_history),
        }
        try:
            with open(self.run_data_path, "w", encoding="utf-8") as f:
                json.dump(run_data, f, indent=2, default=str)
        except Exception:
            self._print_exception()

    def _write_run_data(self, result: ResearchGroupResult, started_at: str, completed_at: str) -> None:
        """Always-on JSON dump for downstream aggregation."""
        run_data = {
            "metadata": {
                **self.run_metadata,
                "loop_class": "B2Baseline",
                "max_turns": self.max_turns,
                "num_researchers": 1,
                "started_at": started_at,
                "completed_at": completed_at,
            },
            "result": {
                "stop_reason": result.stop_reason,
                "turns_completed": result.turns_completed,
                "directions_explored": 0,
                "directions_killed": 0,
                "killed_directions": [],
                "active_directions": [],
                "total_input_tokens": result.total_input_tokens,
                "total_output_tokens": result.total_output_tokens,
                "estimated_cost_usd": result.estimated_cost,
            },
            "turn_history": result.turn_history,
        }
        with open(self.run_data_path, "w", encoding="utf-8") as f:
            json.dump(run_data, f, indent=2, default=str)

    def _write_costs(self, result: ResearchGroupResult) -> None:
        cost_data = {
            "estimated_cost_usd": result.estimated_cost,
            "total_input_tokens": result.total_input_tokens,
            "total_output_tokens": result.total_output_tokens,
            "turns": result.turns_completed,
        }
        with open(self.cost_path, "w", encoding="utf-8") as f:
            json.dump(cost_data, f, indent=2)
