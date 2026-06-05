"""
ResearchGroup: Multi-Agent Hierarchical Orchestration

Two ways to run ResearchGroup:

━━━ Option A: Claude Code native (recommended) ━━━

  No Python API key needed — the loop runs via Claude Code's Agent tool.

  1. Open Claude Code in this directory:
       cd C:\\Users\\ylchen\\workspace\\research_group

  2. Type one of:
       run research_group
       run research_group --max-turns 6         (quick test: 2 full evaluator cycles)
       run research_group --researchers 3       (3 parallel researchers)
       run research_group --region europe       (international market)

  Cadence (revised 2026-05-08):
    - Researchers (2-4): every turn (parallel)
    - Supervisors (3: Stats, Domain, Methods): every turn + escalation
    - Evaluator (1): every 3 turns + escalation (kill/redirect/terminate)

  The loop stops when:
    - Evaluator issues [TERMINATE]
    - All 3 supervisors issue [APPROVED] (triggers evaluator final review)
    - max_turns is reached (default: 18)

━━━ Option B: Python API (requires ANTHROPIC_API_KEY) ━━━

  pip install -r requirements.txt
  export ANTHROPIC_API_KEY=sk-...
  python run_research_group.py --region us --max-turns 27 --researchers 2

"""
from __future__ import annotations

import argparse
import datetime
import os
import sys
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description="ResearchGroup optimization loop")
    parser.add_argument("--region", default="us", choices=["us", "china", "japan", "europe"])
    parser.add_argument("--max-turns", type=int, default=27)
    parser.add_argument("--researchers", type=int, default=2)
    parser.add_argument("--model", default="claude-sonnet-4-20250514")
    parser.add_argument("--task", default="Optimize TimesFM finetuning to minimize MAPE on eval tickers.")
    args = parser.parse_args()

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print(__doc__)
        print("Error: ANTHROPIC_API_KEY not set. Use Option A (Claude Code) or set the key.")
        sys.exit(1)

    import anthropic

    from research_group import Evaluator, ResearchGroupV2, Researcher, Supervisor
    from research_group.tools import ToolExecutor

    client = anthropic.Anthropic(api_key=api_key)
    working_dir = Path(r"C:\Users\ylchen\workspace\timesfm")
    executor = ToolExecutor(working_dir)

    # Create researchers
    researchers = [
        Researcher(
            client=client,
            model=args.model,
            executor=executor,
            researcher_id=f"R{i+1}",
        )
        for i in range(args.researchers)
    ]

    # Create 3 specialist supervisors
    supervisors = [
        Supervisor(client=client, model=args.model, role="Stats"),
        Supervisor(client=client, model=args.model, role="Domain"),
        Supervisor(client=client, model=args.model, role="Methods"),
    ]

    # Create evaluator
    evaluator = Evaluator(client=client, model=args.model)

    # Output directory
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = working_dir / "finetune_expts" / f"research_group_run_{timestamp}"

    # Run
    research_group = ResearchGroupV2(
        researchers=researchers,
        supervisors=supervisors,
        evaluator=evaluator,
        user_task=args.task,
        output_dir=output_dir,
        max_turns=args.max_turns,
        region=args.region,
    )

    result = research_group.run()
    print(f"\nResearchGroup complete. Stop reason: {result.stop_reason}")
    print(f"Summary: {result.summary_path}")


if __name__ == "__main__":
    main()
