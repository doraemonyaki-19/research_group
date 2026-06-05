"""V1 Baseline Orchestrator — Single-Context Glia (SCG).

This implements the upstream Glia v1 architecture from Hamadanian et al.
(arXiv:2510.27176) §4 and §4.1: a Researcher with shell access plus a
generalist Supervisor that asks Socratic questions, both sharing a single
conversation context.

Each turn alternates:
  1. Researcher acts (chain-of-thought + tool calls + final text).
  2. Supervisor reads the Researcher's output and asks 2-4 Socratic questions.
  3. The Supervisor's questions are appended to the SHARED context, so the
     next turn's Researcher sees them as a user message and responds.

This is intentionally separate from V2 (`orchestrator.py`, `researcher.py`,
`supervisor.py`). V1 and V2 must not share Researcher/Supervisor classes —
otherwise the H2 ablation (hierarchy beats flat-2) is contaminated.
"""
from __future__ import annotations

import datetime
import json
from pathlib import Path

from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.rule import Rule

from .orchestrator import ResearchGroupResult
from .v1_researcher import V1Researcher
from .v1_supervisor import V1Supervisor

console = Console()


class ResearchGroupV1:
    """ResearchGroup V1 — Single-Context Glia: Researcher + generalist Supervisor."""

    def __init__(
        self,
        researcher: V1Researcher,
        supervisor: V1Supervisor,
        user_task: str,
        output_dir: Path | str,
        max_turns: int = 27,
        region: str = "us",
        quiet: bool = False,
        json_only: bool = False,
        run_metadata: dict | None = None,
        max_wall_seconds: int | None = None,
        max_conversation_turns: int = 6,
    ):
        self.researcher = researcher
        self.supervisor = supervisor
        self.user_task = user_task
        self.output_dir = Path(output_dir)
        self.max_turns = max_turns
        self.region = region
        self.quiet = quiet
        self.json_only = json_only
        self.run_metadata = dict(run_metadata or {})
        self.max_wall_seconds = max_wall_seconds
        self.max_conversation_turns = max_conversation_turns

        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.log_path = self.output_dir / "v1_log.md"
        self.summary_path = self.output_dir / "v1_summary.md"
        self.cost_path = self.output_dir / "costs.json"
        self.run_data_path = self.output_dir / "run_data.json"

        self._turn_history: list[dict] = []
        # Single-context: Researcher and Supervisor share this conversation.
        self._conversation: list[dict] = [{"role": "user", "content": user_task}]

        self.total_input_tokens = 0
        self.total_output_tokens = 0
        self.total_cost = 0.0

    # ------------------------------------------------------------------
    # Console helpers (respect quiet)
    # ------------------------------------------------------------------

    def _print(self, *args, **kwargs) -> None:
        if not self.quiet:
            console.print(*args, **kwargs)

    def _print_exception(self) -> None:
        if not self.quiet:
            console.print_exception()

    def run(self) -> ResearchGroupResult:
        started_at = datetime.datetime.now().isoformat(timespec="seconds")
        wall_deadline = (
            datetime.datetime.fromisoformat(started_at)
            + datetime.timedelta(seconds=self.max_wall_seconds)
            if self.max_wall_seconds is not None else None
        )
        self._write_log(
            f"# ResearchGroup V1 (Single-Context Glia) Log\n\n"
            f"Started: {started_at}\n"
            f"Max turns: {self.max_turns}\n"
            f"Region: {self.region}\n\n---\n\n"
        )
        # Sentinel checkpoint so a turn-1 hard-kill leaves diagnostic state.
        self._checkpoint_run_data(0, started_at)

        self._print(Rule("[bold blue]ResearchGroup V1 (Single-Context Glia)[/bold blue]"))

        stop_reason = "max_turns"
        consecutive_empty = 0
        STALL_THRESHOLD = 3

        for turn in range(1, self.max_turns + 1):
            elapsed = (datetime.datetime.now() - datetime.datetime.fromisoformat(started_at)).total_seconds()
            if self.max_wall_seconds is not None and elapsed > self.max_wall_seconds:
                print(f"[V1 wall_timeout] elapsed={elapsed:.0f}s exceeds max_wall_seconds={self.max_wall_seconds}; exiting cleanly with checkpoint", flush=True)
                stop_reason = "wall_timeout"
                turn -= 1
                break
            cost_so_far = self.total_cost
            print(f"[V1 turn {turn}/{self.max_turns}] elapsed={elapsed:.0f}s cost=${cost_so_far:.2f} tokens={self.total_input_tokens+self.total_output_tokens}", flush=True)
            self._print(Rule(f"[yellow]Turn {turn} / {self.max_turns}[/yellow]"))

            # ── Nudge injection (when prior turn was empty) ────────
            # If the researcher returned empty on the previous turn, inject
            # a user message reminding it to either propose a new experiment
            # or explicitly [DONE]. Counters the implicit-done failure mode
            # observed in V1 v11 (silent turns 2-3 between substantive
            # turns 1 and 4). Mirrors V2's per-researcher nudge.
            if consecutive_empty > 0:
                nudge = {
                    "role": "user",
                    "content": (
                        f"[ORCHESTRATOR] Your previous turn returned no text "
                        f"(empty for {consecutive_empty} turn(s) in a row). "
                        f"Either propose a substantively different next "
                        f"experiment (review the conversation for what's "
                        f"already been tested), or signal [DONE] explicitly "
                        f"if you have no remaining viable hypotheses. "
                        f"Do not return empty."
                    ),
                }
                self._conversation.append(nudge)

            # ── Researcher acts ────────────────────────────────────
            self._print("[bold green]Researcher (V1)[/bold green] thinking...")
            try:
                researcher_output, new_msgs, in_tok, out_tok = self.researcher.take_turn(
                    conversation_history=self._truncate_conversation(),
                    region=self.region,
                    wall_deadline=wall_deadline,
                )
                self.total_input_tokens += in_tok
                self.total_output_tokens += out_tok
                self.total_cost += self.researcher.model.get_cost(in_tok, out_tok)
            except Exception as e:
                self._print_exception()
                researcher_output = f"[ERROR] {e}"
                new_msgs = []

            self._conversation.extend(new_msgs)
            self._log_turn(turn, "Researcher", researcher_output)
            self._print(Panel(
                Markdown(researcher_output[:3000] + ("..." if len(researcher_output) > 3000 else "")),
                title=f"[green]Researcher V1 (Turn {turn})[/green]",
                border_style="green",
            ))
            self._turn_history.append({"turn": turn, "role": "researcher", "output": researcher_output})

            # In-turn wall_timeout — the researcher hit its wall_deadline
            # mid-tool-loop. Exit cleanly with the partial state.
            if "[WALL_TIMEOUT]" in researcher_output:
                print("[V1 wall_timeout] researcher hit in-turn wall deadline; exiting cleanly", flush=True)
                stop_reason = "wall_timeout"
                break

            # Empty / stall accounting. Stall is checked first because there
            # is no Supervisor work to do on an empty researcher turn.
            if not researcher_output.strip():
                consecutive_empty += 1
                print(f"[V1 stall_warn] researcher returned empty turn {turn} ({consecutive_empty}/{STALL_THRESHOLD})", flush=True)
                if consecutive_empty >= STALL_THRESHOLD:
                    print(f"[V1 researcher_stall] {consecutive_empty} consecutive empty turns — exiting cleanly with checkpoint", flush=True)
                    stop_reason = "researcher_stall"
                    break
            else:
                consecutive_empty = 0

            # ── Supervisor critiques ───────────────────────────────
            # Fires after EVERY substantive researcher turn, including the
            # one that signals [DONE]. Per Glia §4 the Supervisor's role is
            # to ask "are you really done? did you consider X?" — that
            # critique must reach the run record on the final turn even
            # when termination is imminent. Skip only on empty / error
            # outputs (Supervisor needs something concrete to react to).
            if researcher_output.strip() and not researcher_output.startswith("[ERROR]"):
                self._print("[bold cyan]Supervisor (V1)[/bold cyan] reviewing...")
                try:
                    supervisor_output, in_tok, out_tok = self.supervisor.take_turn(
                        researcher_output=researcher_output,
                        region=self.region,
                    )
                    self.total_input_tokens += in_tok
                    self.total_output_tokens += out_tok
                    self.total_cost += self.supervisor.model.get_cost(in_tok, out_tok)
                except Exception as e:
                    self._print_exception()
                    supervisor_output = f"[ERROR] {e}"

                if supervisor_output and supervisor_output.strip():
                    # Inject Supervisor's questions into the shared context
                    # as a user message so the next Researcher turn responds.
                    supervisor_msg = {
                        "role": "user",
                        "content": f"[SUPERVISOR] {supervisor_output}",
                    }
                    self._conversation.append(supervisor_msg)
                    self._log_turn(turn, "Supervisor", supervisor_output)
                    self._print(Panel(
                        Markdown(supervisor_output[:2000] + ("..." if len(supervisor_output) > 2000 else "")),
                        title=f"[cyan]Supervisor V1 (Turn {turn})[/cyan]",
                        border_style="cyan",
                    ))
                    self._turn_history.append({
                        "turn": turn, "role": "supervisor", "output": supervisor_output,
                    })

            # [DONE] short-circuit AFTER Supervisor — the Supervisor's
            # final-turn critique is now in the record.
            if "[DONE]" in researcher_output:
                self._print("[bold green]Researcher signalled [DONE].[/bold green]")
                stop_reason = "done"
                break

            self._checkpoint_run_data(turn, started_at)

        estimated_cost = (self.total_input_tokens / 1_000_000 * 3.0) + (self.total_output_tokens / 1_000_000 * 15.0)

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

    # ------------------------------------------------------------------
    # File writers (gated on json_only)
    # ------------------------------------------------------------------

    def _truncate_conversation(self) -> list[dict]:
        """Sliding-window view of the shared V1 conversation. Same logic as
        V2's orchestrator._truncate_conversation; keeps user_task plus the
        most recent max_conversation_turns × 3 messages to bound O(n²) cost.
        """
        full = self._conversation
        if len(full) <= 1:
            return full
        first = [full[0]]
        rest = full[1:]
        window = self.max_conversation_turns * 3
        if len(rest) <= window:
            return full
        return first + rest[-window:]

    def _log_turn(self, turn: int, role: str, output: str) -> None:
        if self.json_only:
            return
        with open(self.log_path, "a", encoding="utf-8") as f:
            f.write(f"## Turn {turn} — {role}\n\n{output}\n\n---\n\n")

    def _write_log(self, content: str) -> None:
        if self.json_only:
            return
        with open(self.log_path, "w", encoding="utf-8") as f:
            f.write(content)

    def _write_summary(self, result: ResearchGroupResult) -> None:
        if self.json_only:
            return
        lines = [
            "# ResearchGroup V1 (Single-Context Glia) Run Summary\n\n",
            f"**Stop reason:** {result.stop_reason}  \n",
            f"**Turns completed:** {result.turns_completed}  \n",
            f"**Estimated Cost:** ${result.estimated_cost:.2f} ({result.total_input_tokens:,} in / {result.total_output_tokens:,} out)  \n",
            "---\n\n",
        ]
        with open(result.summary_path, "w", encoding="utf-8") as f:
            f.write("".join(lines))

    def _write_costs(self, result: ResearchGroupResult) -> None:
        cost_data = {
            "estimated_cost_usd": result.estimated_cost,
            "total_input_tokens": result.total_input_tokens,
            "total_output_tokens": result.total_output_tokens,
            "turns": result.turns_completed,
        }
        with open(self.cost_path, "w", encoding="utf-8") as f:
            json.dump(cost_data, f, indent=2)

    def _checkpoint_run_data(self, turn: int, started_at: str) -> None:
        # Forensic snapshot — overwritten by final _write_run_data on clean exit.
        estimated_cost = (self.total_input_tokens / 1_000_000 * 3.0) + (self.total_output_tokens / 1_000_000 * 15.0)
        run_data = {
            "metadata": {
                **self.run_metadata,
                "loop_class": "ResearchGroupV1",
                "region": self.region,
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
                "loop_class": "ResearchGroupV1",
                "region": self.region,
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
