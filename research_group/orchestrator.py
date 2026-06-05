"""ResearchGroup orchestration loop with hierarchical multi-agent cadence."""
from __future__ import annotations

import datetime
import json
import re
from dataclasses import dataclass, field
from pathlib import Path

from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.rule import Rule

from .evaluator import Evaluator
from .researcher import Researcher
from .supervisor import Supervisor

console = Console()


# ---------------------------------------------------------------------------
# Escalation signals
# ---------------------------------------------------------------------------

RESEARCHER_ESCALATIONS = {"[NaN]", "[STUCK]", "[BREAKTHROUGH]", "[DONE]"}
SUPERVISOR_ESCALATIONS = {"[CEILING]", "[PIVOT]", "[RESOURCE]", "[APPROVED]"}


def _detect_escalations(text: str, signal_set: set[str]) -> list[str]:
    """Return any escalation signals found in text."""
    return [s for s in signal_set if s in text]


# ---------------------------------------------------------------------------
# Result dataclass
# ---------------------------------------------------------------------------

@dataclass
class ResearchGroupResult:
    turns_completed: int
    stop_reason: str  # "terminate", "approved", "max_turns", "done", "error"
    output_dir: Path
    log_path: Path
    summary_path: Path
    findings_board_path: Path
    num_researchers: int
    directions_explored: int = 0
    directions_killed: int = 0
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    estimated_cost: float = 0.0
    turn_history: list[dict] = field(default_factory=list)


# ---------------------------------------------------------------------------
# ResearchGroup Orchestrator
# ---------------------------------------------------------------------------

class ResearchGroupV2:
    """ResearchGroup: hierarchical multi-agent optimization loop.

    Cadence (revised 2026-05-08):
    - Researchers: every turn (parallel)
    - Supervisors: every turn + escalation (3 specialists, parallel)
    - Evaluator: every 3 turns + escalation (strategic review, kill authority)

    The denser cadence ~3x the per-turn agent count vs the original 27-turn
    configuration, so the default max_turns drops from 27 to 18 to keep the
    per-cell LLM budget comparable to V1 (~108 calls/cell). 18 is divisible
    by 3 → 6 clean evaluator cycles.
    """

    def __init__(
        self,
        researchers: list[Researcher],
        supervisors: list[Supervisor],
        evaluator: Evaluator,
        user_task: str,
        output_dir: Path | str,
        max_turns: int = 18,
        region: str = "us",
        quiet: bool = False,
        json_only: bool = False,
        run_metadata: dict | None = None,
        max_wall_seconds: int | None = None,
        max_conversation_turns: int = 6,
    ):
        self.researchers = researchers
        self.supervisors = supervisors
        self.evaluator = evaluator
        self.user_task = user_task
        self.output_dir = Path(output_dir)
        self.max_turns = max_turns
        self.region = region
        self.quiet = quiet
        self.json_only = json_only
        self.run_metadata = dict(run_metadata or {})
        self.max_wall_seconds = max_wall_seconds
        # Sliding-window cap on each researcher's conversation history.
        # Without this, conversation grows O(n²) in turns — by turn 10 the
        # per-call token count hit 6.4M in the Phase A pilot, driving a
        # single V2-Full seed to $20+. We keep the first message (user_task)
        # plus the most recent max_conversation_turns turns (each turn =
        # researcher assistant msg + tool results + any injected user msgs).
        # A "turn" in this context ≈ 2-4 messages, so max_conversation_turns=6
        # ≈ last 12-24 messages, enough for coherence without unbounded growth.
        self.max_conversation_turns = max_conversation_turns

        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.log_path = self.output_dir / "research_group_log.md"
        self.summary_path = self.output_dir / "research_group_summary.md"
        self.findings_board_path = self.output_dir / "findings_board.md"
        self.cost_path = self.output_dir / "costs.json"
        self.run_data_path = self.output_dir / "run_data.json"

        # State
        self._findings_board = ""
        self._supervisor_memos: dict[str, str] = {}
        self._evaluator_directive = ""
        self._active_directions: list[str] = []
        self._killed_directions: list[str] = []
        self._escalation_queue: list[str] = []
        self._evaluator_triggered = False
        self._turn_history: list[dict] = []

        self.total_input_tokens = 0
        self.total_output_tokens = 0
        self.total_cost = 0.0

        # Per-researcher conversation histories
        self._researcher_conversations: dict[str, list[dict]] = {
            r.researcher_id: [{"role": "user", "content": user_task}]
            for r in researchers
        }
        # Per-researcher empty-streak: incremented after a turn whose output
        # was empty, reset on a non-empty turn. When > 0 at the START of a
        # researcher's turn, an orchestrator-nudge user message is injected
        # into that researcher's conversation history before take_turn,
        # asking for either a new hypothesis or an explicit [DONE]. This
        # surfaces the implicit-done failure mode (Pro Preview returning
        # silently rather than signalling) per researcher, not just on the
        # all-empty case the stall detector handles.
        self._researcher_empty_streak: dict[str, int] = {
            r.researcher_id: 0 for r in researchers
        }

    # -----------------------------------------------------------------------
    # Main loop
    # -----------------------------------------------------------------------

    def run(self) -> ResearchGroupResult:
        started_at = datetime.datetime.now().isoformat(timespec="seconds")
        # Wall deadline passed into each researcher's tool loop so a
        # single tool-heavy turn can't blow past max_wall_seconds.
        wall_deadline = (
            datetime.datetime.fromisoformat(started_at)
            + datetime.timedelta(seconds=self.max_wall_seconds)
            if self.max_wall_seconds is not None else None
        )
        self._write_log(
            f"# ResearchGroup Run Log\n\n"
            f"Started: {started_at}\n"
            f"Output dir: {self.output_dir}\n"
            f"Max turns: {self.max_turns}\n"
            f"Researchers: {len(self.researchers)}\n"
            f"Region: {self.region}\n\n---\n\n"
        )
        self._write_findings_board("# Findings Board\n\n")
        # Sentinel checkpoint — written BEFORE any researcher runs so a
        # turn-1 hard-kill leaves diagnostic state on disk (the May 2026
        # V1 4h-watchdog regression: empty output dir).
        self._checkpoint_run_data(0, started_at)

        self._print(Rule("[bold blue]ResearchGroup — Multi-Agent Hierarchical Mode[/bold blue]"))
        self._print(f"[dim]Output: {self.output_dir}[/dim]")
        self._print(f"[dim]Max turns: {self.max_turns} | Researchers: {len(self.researchers)} | Region: {self.region}[/dim]\n")

        stop_reason = "max_turns"
        consecutive_all_empty = 0
        STALL_THRESHOLD = 3  # All researchers empty for N turns in a row → broken

        for turn in range(1, self.max_turns + 1):
            elapsed = (datetime.datetime.now() - datetime.datetime.fromisoformat(started_at)).total_seconds()
            if self.max_wall_seconds is not None and elapsed > self.max_wall_seconds:
                print(f"[V2 wall_timeout] elapsed={elapsed:.0f}s exceeds max_wall_seconds={self.max_wall_seconds}; exiting cleanly with checkpoint", flush=True)
                stop_reason = "wall_timeout"
                turn -= 1  # last completed turn
                break
            cost_so_far = (self.total_input_tokens / 1_000_000 * 3.0) + (self.total_output_tokens / 1_000_000 * 15.0)
            print(f"[V2 turn {turn}/{self.max_turns}] elapsed={elapsed:.0f}s cost=${cost_so_far:.2f} tokens={self.total_input_tokens+self.total_output_tokens}", flush=True)
            self._print(Rule(f"[yellow]Turn {turn} / {self.max_turns}[/yellow]"))

            # ── STEP 1: RESEARCHERS (parallel) ─────────────────────
            researcher_outputs = {}
            for researcher in self.researchers:
                rid = researcher.researcher_id
                self._print(f"[bold green]Researcher {rid}[/bold green] thinking...")

                # If this researcher's prior turn was empty, inject a nudge
                # into its conversation BEFORE take_turn. Surfaces the
                # implicit-done failure mode (Pro Preview returning silently
                # rather than signalling [DONE]) at per-researcher granularity.
                if self._researcher_empty_streak[rid] > 0:
                    nudge = {
                        "role": "user",
                        "content": (
                            f"[ORCHESTRATOR] Your previous turn returned no text. "
                            f"You returned empty for "
                            f"{self._researcher_empty_streak[rid]} turn(s) in a row. "
                            f"Either propose a substantively different next "
                            f"experiment (read the findings board for what's "
                            f"already been tested), or signal [DONE] explicitly "
                            f"if you have no remaining viable hypotheses for "
                            f"your assigned exploration. Do not return empty."
                        ),
                    }
                    self._researcher_conversations[rid].append(nudge)

                try:
                    output, new_msgs, in_tok, out_tok = researcher.take_turn(
                        conversation_history=self._truncate_conversation(rid),
                        turn_number=turn,
                        findings_board=self._findings_board,
                        supervisor_memos=self._format_supervisor_memos(),
                        evaluator_directive=self._evaluator_directive,
                        killed_directions=self._format_killed_directions(),
                        region=self.region,
                        on_tool_call=self._on_tool_call,
                        on_tool_result=self._on_tool_result,
                        wall_deadline=wall_deadline,
                    )
                    self.total_input_tokens += in_tok
                    self.total_output_tokens += out_tok
                    self.total_cost += researcher.model.get_cost(in_tok, out_tok)
                except Exception as e:
                    self._print_exception()
                    output = f"[ERROR] {e}"
                    new_msgs = []

                self._researcher_conversations[rid].extend(new_msgs)
                researcher_outputs[rid] = output

                # Update per-researcher empty-streak counter.
                if not output.strip():
                    self._researcher_empty_streak[rid] += 1
                else:
                    self._researcher_empty_streak[rid] = 0

                # Log and display
                self._log_turn(f"Researcher {rid}", turn, output)
                self._print(Panel(
                    Markdown(output[:3000] + ("..." if len(output) > 3000 else "")),
                    title=f"[green]Researcher {rid} (Turn {turn})[/green]",
                    border_style="green",
                ))

                self._turn_history.append({
                    "turn": turn, "role": f"researcher_{rid}", "output": output,
                })

                # Check escalations
                escalations = _detect_escalations(output, RESEARCHER_ESCALATIONS)
                if escalations:
                    self._escalation_queue.extend(escalations)
                    self._print(f"  [bold yellow]Escalation: {escalations}[/bold yellow]")

            # Update findings board
            self._update_findings_board(turn, researcher_outputs)

            # Wall-timeout detection at the researcher level. If any
            # researcher hit its in-turn wall_deadline, exit cleanly with
            # the partial state. This is the last-line-of-defense before
            # the orchestrator's between-turn check (next iteration).
            if any("[WALL_TIMEOUT]" in o for o in researcher_outputs.values()):
                print("[V2 wall_timeout] researcher hit in-turn wall deadline; exiting cleanly", flush=True)
                stop_reason = "wall_timeout"
                break

            # Stall detection: if every researcher returned empty text, count it.
            # Three consecutive all-empty turns means the model is silently
            # no-op'ing (the May 2026 V1 fabrication failure mode) — exit
            # cleanly rather than burn the rest of the budget producing nothing.
            if all(not o.strip() for o in researcher_outputs.values()):
                consecutive_all_empty += 1
                print(f"[V2 stall_warn] all researchers empty turn {turn} ({consecutive_all_empty}/{STALL_THRESHOLD})", flush=True)
                if consecutive_all_empty >= STALL_THRESHOLD:
                    print(f"[V2 researcher_stall] {consecutive_all_empty} consecutive all-empty turns — exiting cleanly with checkpoint", flush=True)
                    stop_reason = "researcher_stall"
                    break
            else:
                consecutive_all_empty = 0

            # Check for [DONE]
            if any("[DONE]" in o for o in researcher_outputs.values()):
                self._print("[bold green]Researcher signalled [DONE] — triggering evaluator.[/bold green]")
                self._evaluator_triggered = True

            # ── STEP 2: SUPERVISORS (every turn OR escalation) ──
            if True or self._escalation_queue:
                combined_researcher_output = "\n\n---\n\n".join(
                    f"### Researcher {rid}\n\n{output}"
                    for rid, output in researcher_outputs.items()
                )
                escalation_text = "\n".join(self._escalation_queue) if self._escalation_queue else ""

                supervisor_outputs = {}
                for supervisor in self.supervisors:
                    self._print(f"[bold cyan]Supervisor ({supervisor.role})[/bold cyan] reviewing...")
                    try:
                        memo, in_tok, out_tok = supervisor.take_turn(
                            researcher_outputs=combined_researcher_output,
                            turn_number=turn,
                            findings_board=self._findings_board,
                            escalation_queue=escalation_text,
                            evaluator_directive=self._evaluator_directive,
                            region=self.region,
                        )
                        self.total_input_tokens += in_tok
                        self.total_output_tokens += out_tok
                        self.total_cost += supervisor.model.get_cost(in_tok, out_tok)
                    except Exception as e:
                        self._print_exception()
                        memo = f"[ERROR] {e}"

                    supervisor_outputs[supervisor.role] = memo
                    self._supervisor_memos[supervisor.role] = memo

                    self._log_turn(f"Supervisor ({supervisor.role})", turn, memo)
                    self._print(Panel(
                        Markdown(memo[:2000] + ("..." if len(memo) > 2000 else "")),
                        title=f"[cyan]Supervisor {supervisor.role} (Turn {turn})[/cyan]",
                        border_style="cyan",
                    ))

                    self._turn_history.append({
                        "turn": turn, "role": f"supervisor_{supervisor.role}", "output": memo,
                    })

                # Clear escalation queue
                self._escalation_queue.clear()

                # Check if ALL supervisors approved
                if all(
                    output.startswith("[APPROVED]")
                    for output in supervisor_outputs.values()
                ):
                    self._print("[bold cyan]All supervisors [APPROVED] — triggering evaluator.[/bold cyan]")
                    self._evaluator_triggered = True

                # Check for supervisor escalations to evaluator
                for role, memo in supervisor_outputs.items():
                    sup_esc = _detect_escalations(memo, SUPERVISOR_ESCALATIONS - {"[APPROVED]"})
                    if sup_esc:
                        self._print(f"  [bold yellow]Supervisor {role} escalation: {sup_esc}[/bold yellow]")
                        self._evaluator_triggered = True

                # Inject supervisor guidance into researcher conversations
                guidance = self._format_supervisor_memos()
                for rid in self._researcher_conversations:
                    self._researcher_conversations[rid].append({
                        "role": "user",
                        "content": f"[Supervisor feedback — Turn {turn}]\n\n{guidance}",
                    })

            # ── STEP 3: EVALUATOR (every 3 turns OR escalation) ────
            if turn % 3 == 0 or self._evaluator_triggered:
                self._print("[bold magenta]Evaluator[/bold magenta] conducting strategic review...")
                try:
                    eval_output, in_tok, out_tok = self.evaluator.take_turn(
                        turn_number=turn,
                        findings_board=self._findings_board,
                        supervisor_memos=self._format_supervisor_memos(),
                        active_directions="\n".join(f"- {d}" for d in self._active_directions) or "(none)",
                        killed_directions=self._format_killed_directions(),
                        region=self.region,
                    )
                    self.total_input_tokens += in_tok
                    self.total_output_tokens += out_tok
                    self.total_cost += self.evaluator.model.get_cost(in_tok, out_tok)
                except Exception as e:
                    self._print_exception()
                    eval_output = f"[ERROR] {e}"

                self._log_turn("Evaluator", turn, eval_output)
                self._print(Panel(
                    Markdown(eval_output[:3000] + ("..." if len(eval_output) > 3000 else "")),
                    title=f"[magenta]Evaluator (Turn {turn})[/magenta]",
                    border_style="magenta",
                ))

                self._turn_history.append({
                    "turn": turn, "role": "evaluator", "output": eval_output,
                })

                # Parse directives
                directives = Evaluator.parse_directives(eval_output)

                for killed in directives["kills"]:
                    if killed in self._active_directions:
                        self._active_directions.remove(killed)
                    self._killed_directions.append(killed)
                    self._print(f"  [bold red]KILLED: {killed}[/bold red]")

                for redirect in directives["redirects"]:
                    self._active_directions.append(redirect)
                    self._print(f"  [bold yellow]NEW DIRECTION: {redirect}[/bold yellow]")

                if directives["terminate"]:
                    self._print("[bold red]Evaluator issued [TERMINATE].[/bold red]")
                    stop_reason = "terminate"
                    self._evaluator_directive = eval_output
                    break

                self._evaluator_directive = eval_output
                self._evaluator_triggered = False

                # Inject evaluator directive into researcher conversations
                for rid in self._researcher_conversations:
                    self._researcher_conversations[rid].append({
                        "role": "user",
                        "content": f"[Evaluator directive — Turn {turn}]\n\n{eval_output}",
                    })

            # Check for [DONE] stop (after evaluator had chance to review)
            if any("[DONE]" in o for o in researcher_outputs.values()) and not self._evaluator_triggered:
                stop_reason = "done"
                break

            # Forensic checkpoint so watchdog-killed runs leave diagnostic state.
            self._checkpoint_run_data(turn, started_at)

        # ── WRAP UP ────────────────────────────────────────────────
        if stop_reason == "max_turns":
            # Final evaluator review
            self._print("[bold magenta]Evaluator[/bold magenta] — final summary...")
            try:
                final_eval, in_tok, out_tok = self.evaluator.take_turn(
                    turn_number=turn,
                    findings_board=self._findings_board,
                    supervisor_memos=self._format_supervisor_memos(),
                    active_directions="\n".join(f"- {d}" for d in self._active_directions) or "(none)",
                    killed_directions=self._format_killed_directions(),
                    region=self.region,
                )
                self.total_input_tokens += in_tok
                self.total_output_tokens += out_tok
                self.total_cost += self.evaluator.model.get_cost(in_tok, out_tok)
                self._log_turn("Evaluator (Final)", turn, final_eval)
                self._turn_history.append({
                    "turn": turn, "role": "evaluator_final", "output": final_eval,
                })
            except Exception:
                self._print_exception()

        # Final cost is already tracked in self.total_cost
        estimated_cost = self.total_cost

        result = ResearchGroupResult(
            turns_completed=turn,
            stop_reason=stop_reason,
            output_dir=self.output_dir,
            log_path=self.log_path,
            summary_path=self.summary_path,
            findings_board_path=self.findings_board_path,
            num_researchers=len(self.researchers),
            directions_explored=len(self._active_directions) + len(self._killed_directions),
            directions_killed=len(self._killed_directions),
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
        self._print(Rule("[bold blue]Run Complete[/bold blue]"))
        self._print(f"Stop reason: [bold]{stop_reason}[/bold]")
        self._print(f"Turns completed: {result.turns_completed}")
        self._print(f"Estimated Cost: ${estimated_cost:.2f}")
        self._print(f"Directions explored: {result.directions_explored}")
        self._print(f"Directions killed: {result.directions_killed}")
        self._print(f"Log: {self.log_path}")
        self._print(f"Summary: {self.summary_path}")

        return result

    # -----------------------------------------------------------------------
    # Helpers
    # -----------------------------------------------------------------------

    def _print(self, *args, **kwargs) -> None:
        if not self.quiet:
            console.print(*args, **kwargs)

    def _print_exception(self) -> None:
        if not self.quiet:
            console.print_exception()

    def _format_supervisor_memos(self) -> str:
        if not self._supervisor_memos:
            return "(none yet)"
        parts = []
        for role, memo in self._supervisor_memos.items():
            parts.append(f"### Supervisor ({role})\n\n{memo}")
        return "\n\n---\n\n".join(parts)

    def _truncate_conversation(self, rid: str) -> list[dict]:
        """Return a sliding-window view of the researcher's conversation.

        Keeps the first message (user_task — the problem statement that must
        always be in context) plus the most recent messages up to
        max_conversation_turns × ~3 messages. The window is expressed in
        wall-clock turns, not raw messages, so it adapts to how much each
        turn actually produced.

        Call this immediately before researcher.take_turn to bound growth.
        """
        full = self._researcher_conversations[rid]
        if len(full) <= 1:
            return full  # only user_task; nothing to truncate yet

        first = [full[0]]  # always keep the user_task
        rest = full[1:]

        # Heuristic: each orchestrator turn adds ~3 messages on average
        # (assistant + tool_results + injected user msgs). Keeping the last
        # max_conversation_turns × 3 messages preserves recent context.
        window = self.max_conversation_turns * 3
        if len(rest) <= window:
            return full  # not yet long enough to need truncation

        trimmed = rest[-window:]
        return first + trimmed

    def _format_killed_directions(self) -> str:
        if not self._killed_directions:
            return "(none)"
        return "\n".join(f"- {d}" for d in self._killed_directions)

    def _update_findings_board(self, turn: int, researcher_outputs: dict[str, str]) -> None:
        """Extract '## Findings for Board' sections and append to findings board."""
        new_entries = []
        for rid, output in researcher_outputs.items():
            # Extract the findings section
            match = re.search(
                r"## Findings for Board\s*\n(.*?)(?=\n## |\Z)",
                output,
                re.DOTALL,
            )
            if match:
                findings = match.group(1).strip()
                # Limit to 5 lines
                lines = findings.split("\n")[:5]
                entry = f"- {rid}: " + " | ".join(line.strip("- ").strip() for line in lines if line.strip())
            else:
                # Fallback: first 200 chars of output
                entry = f"- {rid}: {output[:200]}..."
            new_entries.append(entry)

        section = f"\n## Turn {turn}\n" + "\n".join(new_entries) + "\n"
        self._findings_board += section

        # Trim to last 6000 chars
        if len(self._findings_board) > 6000:
            self._findings_board = "... [earlier turns truncated]\n" + self._findings_board[-5500:]

        # Write to file
        self._write_findings_board(f"# Findings Board\n\n{self._findings_board}")

    def _on_tool_call(self, tool_name: str, tool_input: dict) -> None:
        preview = json.dumps(tool_input)[:200]
        self._print(f"  [dim]→ tool:[/dim] [yellow]{tool_name}[/yellow] {preview}")
        self._append_log(f"  *Tool call:* `{tool_name}` — `{preview}`\n\n")

    def _on_tool_result(self, tool_name: str, result_str: str) -> None:
        preview = result_str[:300]
        self._print(f"  [dim]← result:[/dim] {preview}")
        self._append_log(f"  *Tool result:* `{preview[:200]}`\n\n")

    def _log_turn(self, role: str, turn: int, output: str) -> None:
        header = f"## Turn {turn} — {role}\n\n"
        self._append_log(header + output + "\n\n---\n\n")

    def _write_log(self, content: str) -> None:
        if self.json_only:
            return
        with open(self.log_path, "w", encoding="utf-8") as f:
            f.write(content)

    def _append_log(self, content: str) -> None:
        if self.json_only:
            return
        with open(self.log_path, "a", encoding="utf-8") as f:
            f.write(content)

    def _write_findings_board(self, content: str) -> None:
        with open(self.findings_board_path, "w", encoding="utf-8") as f:
            f.write(content)

    def _write_summary(self, result: ResearchGroupResult) -> None:
        if self.json_only:
            return
        lines = [
            "# ResearchGroup Run Summary\n\n",
            f"**Stop reason:** {result.stop_reason}  \n",
            f"**Turns completed:** {result.turns_completed}  \n",
            f"**Researchers:** {result.num_researchers}  \n",
            f"**Directions explored:** {result.directions_explored}  \n",
            f"**Directions killed:** {result.directions_killed}  \n",
            f"**Estimated Cost:** ${result.estimated_cost:.2f} ({result.total_input_tokens:,} in / {result.total_output_tokens:,} out)  \n",
            f"**Output dir:** {result.output_dir}  \n\n",
            "---\n\n",
        ]

        if self._killed_directions:
            lines.append("## Killed Directions\n\n")
            for d in self._killed_directions:
                lines.append(f"- {d}\n")
            lines.append("\n")

        lines.append("## Turn History\n\n")
        for t in result.turn_history:
            lines.append(f"### Turn {t['turn']} — {t['role'].title()}\n\n")
            lines.append(t["output"][:1200] + ("..." if len(t["output"]) > 1200 else ""))
            lines.append("\n\n")

        with open(result.summary_path, "w", encoding="utf-8") as f:
            f.write("".join(lines))

    def _write_run_data(self, result: ResearchGroupResult, started_at: str, completed_at: str) -> None:
        """Always-on JSON dump of structured run data, regardless of json_only mode.

        This is the canonical machine-readable artifact for downstream
        aggregation. Markdown logs (when present) are derived views of the
        same data; this file is the source of truth for benchmarks/aggregation.
        """
        run_data = {
            "metadata": {
                **self.run_metadata,
                "loop_class": "ResearchGroupV2",
                "region": self.region,
                "max_turns": self.max_turns,
                "num_researchers": len(self.researchers),
                "started_at": started_at,
                "completed_at": completed_at,
            },
            "result": {
                "stop_reason": result.stop_reason,
                "turns_completed": result.turns_completed,
                "directions_explored": result.directions_explored,
                "directions_killed": result.directions_killed,
                "killed_directions": list(self._killed_directions),
                "active_directions": list(self._active_directions),
                "total_input_tokens": result.total_input_tokens,
                "total_output_tokens": result.total_output_tokens,
                "estimated_cost_usd": result.estimated_cost,
            },
            "turn_history": result.turn_history,
        }
        with open(self.run_data_path, "w", encoding="utf-8") as f:
            json.dump(run_data, f, indent=2, default=str)

    def _checkpoint_run_data(self, turn: int, started_at: str) -> None:
        # Forensic snapshot for watchdog-killed runs. Overwritten by the final
        # _write_run_data when the run completes normally.
        estimated_cost = (self.total_input_tokens / 1_000_000 * 3.0) + (self.total_output_tokens / 1_000_000 * 15.0)
        run_data = {
            "metadata": {
                **self.run_metadata,
                "loop_class": "ResearchGroupV2",
                "region": self.region,
                "max_turns": self.max_turns,
                "num_researchers": len(self.researchers),
                "started_at": started_at,
                "completed_at": None,
            },
            "result": {
                "stop_reason": "in_progress",
                "turns_completed": turn,
                "directions_explored": len(self._active_directions) + len(self._killed_directions),
                "directions_killed": len(self._killed_directions),
                "killed_directions": list(self._killed_directions),
                "active_directions": list(self._active_directions),
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

    def _write_costs(self, result: ResearchGroupResult) -> None:
        cost_data = {
            "estimated_cost_usd": result.estimated_cost,
            "total_input_tokens": result.total_input_tokens,
            "total_output_tokens": result.total_output_tokens,
            "turns": result.turns_completed,
        }
        with open(self.cost_path, "w", encoding="utf-8") as f:
            json.dump(cost_data, f, indent=2)
