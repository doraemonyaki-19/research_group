# ResearchGroup v2: Hierarchical Multi-Agent Scientific Optimization

ResearchGroup v2 is a framework for automated scientific search and system optimization. It extends the paradigm from the original [Glia paper (Hamadanian et al., arXiv:2510.27176)](https://arxiv.org/abs/2510.27176) with a hierarchical multi-agent architecture, three specialized supervisor roles, and per-agent skill injection.

**Status:** Research preview. Empirical results are being validated against the protocol in [`EVALUATION_PROTOCOL.md`](EVALUATION_PROTOCOL.md). See [`PUBLISHING_PLAN.md`](PUBLISHING_PLAN.md) for the publication roadmap.

---

## What's new vs upstream Glia

| Dimension | Upstream Glia (v1) | ResearchGroup v2 |
|---|---|---|
| **Application** | GPU-cluster LLM-inference scheduling | Generalized to ML training/hyperparameter optimization (e.g., TimesFM finetuning) |
| **Agents** | 2 (1 researcher + 1 supervisor) | 4–7 (2–4 parallel researchers + 3 specialized supervisors + 1 evaluator) |
| **Supervision** | Single generalist | Three specialists writing **independent** memos (prevents anchoring) |
| **Authority** | None | Evaluator with explicit **`[KILL]` / `[REDIRECT]` / `[TERMINATE]`** directives |
| **Capabilities** | Plain prompts | Skill injection at run-start (`scientific-critical-thinking`, `scientific-brainstorming`, `peer-review`, `timesfm-forecasting`) |
| **Coordination** | Shared context | Append-only **findings board** as persistent shared knowledge |
| **Escalation** | Implicit | Explicit signals (`[BREAKTHROUGH]`, `[STUCK]`, `[NaN]`, `[CEILING]`, `[PIVOT]`, `[APPROVED]`) |
| **Execution** | Researcher has direct shell access | Researchers plan; orchestrator runs experiments |

---

## Architecture

### Agents

1. **Researchers (parallel, 2–4)** — formulate hypotheses, plan experiments, analyze results. Have Read/Glob/Grep tools; the orchestrator dispatches Bash commands they request.

2. **Supervisors (3 specializations, parallel)**
   - **Stats** (`scientific-critical-thinking`) — statistical rigor, sample sizes, bias detection, GRADE evidence assessment.
   - **Domain** (`scientific-brainstorming`) — cross-domain analogies, assumption reversal, scale shifting, constraint exploration.
   - **Methods** (`timesfm-forecasting` for the TimesFM task; substitutable per task) — model architecture, training dynamics, transfer-learning constraints.

   All three write *independent* memos every turn; no supervisor reads another's output. This is deliberate — supervisor diversity is the value, anchoring is the failure mode.

3. **Evaluator** (`peer-review`) — strategic authority. Reads the full findings board and all supervisor memos. Has `[KILL: <direction>]`, `[REDIRECT: <description>]`, and `[TERMINATE]` authority. Fires every 3 turns or on escalation.

### Cadence

| Agent | Default cadence | Escalation triggers |
|---|---|---|
| Researchers | Every turn (parallel) | n/a |
| Supervisors (×3) | Every turn | `[NaN]`, `[STUCK]`, `[BREAKTHROUGH]`, `[DONE]` from any researcher |
| Evaluator | Every 3 turns | `[CEILING]`, `[PIVOT]`, `[RESOURCE]` from any supervisor; or all 3 supervisors `[APPROVED]` |

### Data flow

- **Experiment context** (`*_expt.md`) — task description loaded once at run-start, injected into researcher prompts.
- **Findings board** — append-only structured log of validated insights; trimmed to a bounded char budget; readable by all agents.
- **Conversation histories** — per-researcher; supervisor memos are *injected* as user-role messages between turns rather than persisted in the LLM context.

---

## Installation

```bash
git clone https://github.com/<your-org>/research_group.git
cd research_group
pip install -e .
pip install -e ".[dev]"   # for tests + linting
```

Requires Python ≥ 3.10. The Anthropic SDK and Google GenAI SDK are in the runtime deps; `pytest` and `ruff` are dev-only.

### Skills

Skill content is loaded once at run-start. Two layouts are supported:

- **Bundled** — skills live in `research_group/skills/` (default for the Python harness).
- **Claude Code native** — skills resolve from `~/.claude/skills/` when running via the Claude Code agent path described in `CLAUDE.md`.

If a required skill is missing, the agent runs with no skill content (logged as a warning).

---

## Usage

### A. Python API — for benchmarking and unattended runs

The benchmarking harness in `benchmarks/run_ablation.py` is the primary entry point for evaluation runs:

```bash
export GEMINI_API_KEY=AIza...
python benchmarks/run_ablation.py --provider gemini --config V2-Full --seeds 7 --region us

# Or run with Anthropic models:
export ANTHROPIC_API_KEY=sk-...
python benchmarks/run_ablation.py --provider anthropic --model claude-3-7-sonnet-20250219 --config V2-Full --seeds 7 --region us
```

Outputs land in `results/{config}/{region}/seed_{N}_{timestamp}/` containing `research_group_log.md`, `findings_board.md`, and `research_group_summary.md`.

For a single run with custom configuration, instantiate `ResearchGroupV2` directly:

```python
import os
from pathlib import Path
from google import genai
from research_group.llm import GeminiModel
from research_group.orchestrator import ResearchGroupV2
from research_group.researcher import Researcher
from research_group.supervisor import Supervisor
from research_group.evaluator import Evaluator
from research_group.tools import ToolExecutor

client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
llm_model = GeminiModel(client=client, model="gemini-3.1-pro-preview")
executor = ToolExecutor(working_dir=Path("path/to/experiment/working/dir"))

researchers = [
    Researcher(model=llm_model, executor=executor, researcher_id=f"R{i+1}")
    for i in range(2)
]
supervisors = [
    Supervisor(model=llm_model, role=role)
    for role in ("Stats", "Domain", "Methods")
]
evaluator = Evaluator(model=llm_model)

result = ResearchGroupV2(
    researchers=researchers,
    supervisors=supervisors,
    evaluator=evaluator,
    user_task="Optimize TimesFM finetuning to minimize MAPE on eval tickers.",
    output_dir=Path("results/run_001"),
    max_turns=18,
    region="us",
).run()

print(f"Stop: {result.stop_reason}; turns: {result.turns_completed}")
print(f"Tokens: in={result.total_input_tokens}, out={result.total_output_tokens}")
```

### B. Claude Code native — for interactive / step-by-step runs

Open a Claude Code session in the project directory and use the loop defined in `CLAUDE.md`:

```bash
claude
```

Then prompt: `run research_group --max-turns 27 --researchers 2 --region us`

In native mode, Claude Code's Agent tool dispatches subagent calls; no `ANTHROPIC_API_KEY` is required from your environment. Results are written under `C:\Users\ylchen\workspace\timesfm\finetune_expts\research_group_run_<timestamp>\`.

---

## Tasks supported out of the box

- **TimesFM regional finetuning** — see `research_group_timesfm_expt.md`. Four regions (US, China, Japan, Europe) with rolling-window evaluation.

To define a new task, write a new `<task>_expt.md` describing the optimization target, available data, evaluation metric, and known dead-ends. See [`docs/experiment_context_spec.md`](docs/experiment_context_spec.md).

---

## Repository layout

```
research_group/
├── benchmarks/             # Ablation harness (run_ablation.py + results aggregation)
├── docs/                   # Architecture, experiment-context spec, design notes
├── research_group/         # The framework package
│   ├── llm.py              # Generic LLM provider abstraction (Anthropic & Gemini)
│   ├── researcher.py       # Researcher agent (with token tracking)
│   ├── supervisor.py       # Supervisor agent (Stats/Domain/Methods)
│   ├── evaluator.py        # Evaluator agent (with kill/redirect/terminate parsing)
│   ├── v1_baseline.py      # Re-implementation of upstream 2-agent Glia
│   ├── b2_baseline.py      # Single-agent "Claude Code freestyle" baseline
│   ├── prompts.py          # System prompt templates
│   ├── skill_loader.py     # Skill content loader
│   ├── skills/             # Bundled fallback skills
│   └── tools.py            # ToolExecutor + tool definitions
├── tests/                  # Unit + mocked-integration + smoke tests
├── EVALUATION_PROTOCOL.md  # Pre-registered evaluation protocol (frozen 2026-05-01)
├── PUBLISHING_PLAN.md      # 16-week publication plan
├── CLAUDE.md               # Claude Code native-mode trigger and loop spec
└── pyproject.toml          # Project metadata, pytest + ruff config
```

---

## Evaluation status

The pre-registered evaluation against upstream Glia and a Claude-Code-freestyle baseline is in progress. See `EVALUATION_PROTOCOL.md` for the protocol (frozen 2026-05-01) and `benchmarks/REPORT.md` for results once the multi-seed run completes.

Headline hypotheses under test:
- **H1 — Generalization:** v2 transfers from systems optimization to ML training optimization.
- **H2 — Hierarchy improves search:** v2's hierarchy beats v1's flat 2-agent setup on at least one of {best result, turns to convergence, $ to threshold}.
- **H3 — Skill grounding improves agent quality:** skill injection beats no-skills ablation.

A post-T1 kill gate (`EVALUATION_PROTOCOL.md` §7.1) governs whether T2 ablations proceed.

---

## Testing

```bash
pytest                  # unit + mocked integration; ~2s
pytest -m smoke         # smoke tests (require ANTHROPIC_API_KEY)
ruff check .            # lint
```

CI runs unit tests + lint on every PR (see `.github/workflows/ci.yml`).

---

## Citation

If you use ResearchGroup v2 in your research, please cite both the upstream Glia paper and this repository:

```bibtex
@article{hamadanian2025glia,
  title={Glia: A Human-Inspired AI for Automated Systems Design and Optimization},
  author={Hamadanian, Pouya and Karimi, Pantea and Nasr-Esfahany, Arash and Noorbakhsh, Kimia and Chandler, Joseph and ParandehGheibi, Ali and Alizadeh, Mohammad and Balakrishnan, Hari},
  journal={arXiv preprint arXiv:2510.27176},
  year={2025}
}
```

A v2 preprint citation will be added upon publication.

---

## License

See [`LICENSE`](LICENSE).
