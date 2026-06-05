"""Ablation harness for ResearchGroup evaluation protocol.

Runs multiseed trials across the defined configurations (B2, V1, V2-Full)
as specified in EVALUATION_PROTOCOL.md.

Each run produces a directory `results/{config}/{region}/seed_{N}_{timestamp}/`
containing at minimum a `run_data.json` (always written; the canonical
machine-readable artifact for benchmarks/aggregate_results.py). Markdown
artifacts (research_group_log.md, research_group_summary.md, etc.) are
suppressed when --json-only is set.
"""
from __future__ import annotations

import argparse
import datetime
import os
import sys
from pathlib import Path

# Add project root to path so we can import research_group
REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

# Auto-load .env from repo root if present. The harness then resolves the
# Anthropic API key from (in priority order): --api-key CLI arg, ANTHROPIC_API_KEY
# env var (which now includes anything from .env), error.
try:
    from dotenv import load_dotenv
    load_dotenv(REPO_ROOT / ".env")
except ImportError:
    pass  # python-dotenv is in requirements; this only fires in a broken install

import anthropic

from research_group.b2_baseline import B2Baseline
from research_group.evaluator import Evaluator
from research_group.llm import AnthropicModel, GeminiModel, OpenAIModel
from research_group.orchestrator import ResearchGroupV2
from research_group.researcher import Researcher
from research_group.supervisor import Supervisor
from research_group.tools import ToolExecutor
from research_group.v1_baseline import ResearchGroupV1
from research_group.v1_researcher import V1Researcher
from research_group.v1_supervisor import V1Supervisor


def _build_llm(provider: str, api_key: str | None, model_name: str):
    """Construct a LanguageModel for the requested provider+model.

    Used both for the main LLM (researchers + evaluator) and, when
    --supervisor-model differs from --model, for the V2 supervisors.
    """
    if provider == "anthropic":
        if not api_key:
            print("Error: no Anthropic API key found.", file=sys.stderr)
            sys.exit(1)
        client = anthropic.Anthropic(api_key=api_key)
        return AnthropicModel(client=client, model=model_name)
    if provider == "gemini":
        from google import genai
        if not api_key:
            print("Error: no Gemini API key found (GEMINI_API_KEY).", file=sys.stderr)
            sys.exit(1)
        client = genai.Client(api_key=api_key)
        return GeminiModel(client=client, model=model_name)
    if provider == "nvidia":
        from openai import OpenAI
        if not api_key:
            print("Error: no NVIDIA API key found.", file=sys.stderr)
            sys.exit(1)
        client = OpenAI(
            base_url="https://integrate.api.nvidia.com/v1",
            api_key=api_key
        )
        # Handle DeepSeek reasoning/thinking mode
        extra_body = None
        if "deepseek" in model_name.lower() and "flash" in model_name.lower():
            extra_body = {"chat_template_kwargs": {"thinking": True, "reasoning_effort": "high"}}
        return OpenAIModel(client=client, model=model_name, extra_body=extra_body)
    if provider == "interactive":
        from research_group.llm import InteractiveModel
        return InteractiveModel()
    raise ValueError(f"Unknown provider: {provider}")


def _build_loop(args, llm_model, supervisor_llm, executor, run_metadata, run_out_dir):
    """Construct the loop instance for the requested config.

    Args:
        llm_model: Main LLM — used for researchers (V1, V2) and evaluator (V2).
        supervisor_llm: LLM for V2 supervisors. Often a cheaper / smaller
            model than `llm_model` since supervisors only ask Socratic
            questions. Equal to `llm_model` when --supervisor-model matches
            --model. Unused for V1 (V1's supervisor uses `llm_model`).
    """
    from research_group.task_context import load_task_context
    task_context = load_task_context(args.task_context, region=args.region, model=args.model)

    common = dict(
        user_task=args.task,
        output_dir=run_out_dir,
        max_turns=args.max_turns,
        quiet=args.quiet,
        json_only=args.json_only,
        run_metadata=run_metadata,
        max_wall_seconds=args.max_wall_seconds,
    )

    if args.config == "B2":
        # B2 has no structured prompt template; append task context to the
        # user task so the agent has the same domain knowledge as V1/V2.
        b2_task = args.task
        if task_context and not task_context.startswith("("):
            b2_task = f"{args.task}\n\n## Task Context\n\n{task_context}"
        return B2Baseline(
            model=llm_model,
            executor=executor,
            **{**common, "user_task": b2_task},
        )

    if args.config == "V1":
        # V1 uses its own Researcher and Supervisor classes — Single-Context
        # Glia per arXiv:2510.27176 §4.1. Do NOT substitute V2's Researcher /
        # Supervisor here; that contaminates the H2 ablation.
        researcher = V1Researcher(
            model=llm_model,
            executor=executor,
            task_context_path=args.task_context,
        )
        supervisor = V1Supervisor(
            model=llm_model,
            task_context_path=args.task_context,
        )
        return ResearchGroupV1(
            researcher=researcher,
            supervisor=supervisor,
            region=args.region,
            **common,
        )

    if args.config in ("V2-Full", "V2-noSkills"):
        # V2-noSkills tests H3: same architecture as V2-Full but with skill
        # injection disabled. We implement this by monkey-patching
        # skill_loader.load_skill_content to return empty strings for this
        # process only — no framework changes, no extra flags.
        no_skills = args.config == "V2-noSkills"
        if no_skills:
            import research_group.skill_loader as _sl
            _sl.load_skill_content = lambda _name: ""

        # Parse supervisor_skills CLI arg; must be exactly 3 names matching
        # the (Stats, Domain, Methods) ordering.
        skill_list = [s.strip() for s in args.supervisor_skills.split(",")]
        if len(skill_list) != 3:
            raise ValueError(
                f"--supervisor-skills must be a comma-separated list of 3 "
                f"skill names (Stats, Domain, Methods); got {len(skill_list)}"
            )
        researchers = [
            Researcher(
                model=llm_model,
                executor=executor,
                researcher_id=f"R{i+1}",
                task_context_path=args.task_context,
            )
            for i in range(2)
        ]
        supervisors = [
            Supervisor(
                model=supervisor_llm,
                role=role,
                task_context_path=args.task_context,
                # For V2-noSkills the patch above already makes load_skill_content
                # return "". Passing the real skill_name is harmless; it also
                # makes the metadata transparent about which skill *would* have
                # been loaded.
                skill_name=skill_name,
            )
            for role, skill_name in zip(("Stats", "Domain", "Methods"), skill_list)
        ]
        evaluator = Evaluator(
            model=llm_model,
            task_context_path=args.task_context,
        )
        return ResearchGroupV2(
            researchers=researchers,
            supervisors=supervisors,
            evaluator=evaluator,
            region=args.region,
            **common,
        )

    raise ValueError(f"Unknown config: {args.config}")


def main():
    parser = argparse.ArgumentParser(description="ResearchGroup Ablation Harness")
    parser.add_argument("--config", required=True, choices=["B2", "V1", "V2-Full", "V2-noSkills"], help="Configuration to evaluate")
    parser.add_argument("--seeds", type=int, default=1, help="Number of seeds to run starting from --start-seed")
    parser.add_argument("--start-seed", type=int, default=1, help="Index of the first seed (default: 1)")
    parser.add_argument("--region", default="us", choices=["us", "china", "japan", "europe"])
    parser.add_argument("--max-turns", type=int, default=27)
    parser.add_argument(
        "--max-wall-seconds",
        type=int,
        default=None,
        help="Maximum wall-clock seconds for the run. The orchestrator checks this "
        "at the top of each turn and exits cleanly with a final checkpoint if exceeded. "
        "This is the preferred timeout mechanism (vs an external SIGKILL) because it "
        "preserves run_data.json for diagnostics. Default: no wall-clock cap.",
    )
    parser.add_argument("--provider", default="gemini", choices=["anthropic", "gemini", "nvidia", "interactive"], help="LLM provider to use")
    parser.add_argument("--model", default="gemini-2.5-flash", help="Main model name for V1/V2 researchers and the V2 Evaluator (e.g. gemini-3.1-pro-preview or claude-sonnet-4-20250514).")
    parser.add_argument(
        "--supervisor-model",
        default="gemini-2.5-flash",
        help="Model name for V2 Supervisors only. Defaults to gemini-2.5-flash "
        "since Supervisors ask Socratic questions and don't need a frontier "
        "model. Use the same value as --model to disable per-agent model "
        "split (e.g., for tighter reproducibility). Cost reduction with the "
        "split is ~5-10x on supervisor calls.",
    )
    parser.add_argument("--task", default="Optimize TimesFM finetuning to minimize MAPE on eval tickers.")
    parser.add_argument(
        "--task-context",
        default=r"C:\Users\ylchen\workspace\research_group\artifacts\finetune_prompt.md",
        help="Path to a markdown file with task-specific knowledge (mission, "
        "constraints, file paths, CLI templates, dead ends, metrics) injected "
        "into agent system prompts via the {task_context} placeholder. Per "
        "PUBLISHING_PLAN.md §6, swap this path to evaluate against non-TimesFM "
        "tasks (e.g., CIFAR-10 ResNet, MNIST CNN). Set to empty string to use "
        "no task context (mostly for testing).",
    )
    parser.add_argument(
        "--supervisor-skills",
        default="scientific-critical-thinking,scientific-brainstorming,timesfm-forecasting",
        help="Comma-separated list of three Claude Code skill names for the "
        "(Stats, Domain, Methods) supervisors, in that order. The defaults are "
        "TimesFM-appropriate. For T2 (hyperparameter search per "
        "EVALUATION_PROTOCOL.md §2), override Methods to a relevant expert "
        "(e.g. 'cifar-classification' or 'hyperparameter-search'). Stats and "
        "Domain skills are task-agnostic methodology; usually keep their "
        "defaults across tasks.",
    )
    parser.add_argument("--out-dir", default="results")
    parser.add_argument("--quiet", action="store_true", help="Suppress rich console output (banners, panels, rules)")
    parser.add_argument("--json-only", action="store_true", help="Skip markdown log/summary; only write run_data.json + costs.json + findings_board.md")
    parser.add_argument(
        "--api-key",
        default=None,
        help="Anthropic API key. Overrides ANTHROPIC_API_KEY env var and .env file. "
        "If unset, falls back to env var, then to .env in repo root.",
    )
    args = parser.parse_args()

    # Resolve API key once; pass into LLM builders.
    if args.provider == "anthropic":
        api_key = args.api_key or os.environ.get("ANTHROPIC_API_KEY")
    elif args.provider == "gemini":
        api_key = args.api_key or os.environ.get("GEMINI_API_KEY")
    elif args.provider == "nvidia":
        api_key = args.api_key or os.environ.get("NVIDIA_API_KEY")
    else:
        api_key = None  # interactive provider doesn't need a key

    # Capture SDK version for reproducibility (EVALUATION_PROTOCOL.md §5:
    # "Pin Anthropic SDK version, model version, and request-level seed
    # in every run's JSON log. Cross-version comparisons are not valid.")
    if args.provider == "anthropic":
        import anthropic as _ant
        sdk_version = f"anthropic=={_ant.__version__}"
    elif args.provider == "gemini":
        try:
            from google import genai as _genai
            sdk_version = f"google-genai=={_genai.__version__}"
        except AttributeError:
            sdk_version = "google-genai==unknown"
    elif args.provider == "nvidia":
        import openai as _oai
        sdk_version = f"openai=={_oai.__version__}"
    else:
        sdk_version = "interactive"

    # Main LLM — researchers (V1, V2) + V2 evaluator.
    llm_model = _build_llm(args.provider, api_key, args.model)

    # Supervisor LLM — V2 only. Reuse the main LLM if the model matches.
    if args.supervisor_model and args.supervisor_model != args.model:
        supervisor_llm = _build_llm(args.provider, api_key, args.supervisor_model)
    else:
        supervisor_llm = llm_model

    working_dir = Path(r"C:\Users\ylchen\workspace\research_group\artifacts")
    executor = ToolExecutor(working_dir)

    base_out_dir = Path(args.out_dir) / args.config / args.model.replace("/", "_").replace("\\", "_") / args.region
    base_out_dir.mkdir(parents=True, exist_ok=True)

    seed_indices = list(range(args.start_seed, args.start_seed + args.seeds))
    print(
        f"Starting evaluation for {args.config} in {args.region} region "
        f"(seeds {seed_indices[0]}..{seed_indices[-1]}; "
        f"quiet={args.quiet}; json_only={args.json_only})"
    )

    for seed in seed_indices:
        # Resumability: skip if any existing seed_{seed}_* dir already has run_data.json
        existing = sorted(base_out_dir.glob(f"seed_{seed}_*"))
        if any((d / "run_data.json").exists() for d in existing):
            print(f"[{args.config} seed {seed}] SKIP — run_data.json already exists in {existing[-1].name}")
            continue

        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        run_out_dir = base_out_dir / f"seed_{seed}_{timestamp}"

        print(f"\n[{args.config} seed {seed}] -> {run_out_dir}")

        run_metadata = {
            "config": args.config,
            "seed": seed,
            "provider": args.provider,
            "model": args.model,
            "supervisor_model": args.supervisor_model,
            "sdk_version": sdk_version,
            "region": args.region,
        }

        loop = _build_loop(args, llm_model, supervisor_llm, executor, run_metadata, run_out_dir)
        result = loop.run()
        print(
            f"[{args.config} seed {seed}] done. "
            f"stop={result.stop_reason} turns={result.turns_completed} "
            f"cost=${result.estimated_cost:.2f}"
        )


if __name__ == "__main__":
    main()
