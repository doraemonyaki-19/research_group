# CLAUDE.md — ResearchGroup: Multi-Agent Hierarchical Orchestration

This file is auto-loaded by Claude Code when opened in this directory.
It defines the ResearchGroup optimization loop — a hierarchical multi-agent system
with parallel researchers, domain-expert supervisors, and a strategic evaluator.

---

## Section 1 — Trigger

When the user says any of the following:
- "run research_group"
- "start optimization"
- "start loop"
- "run research_group --max-turns N"
- "run research_group --researchers N"
- "run research_group --region REGION"

Execute the **ResearchGroup loop** described in Section 2.

Parse options:
- `--max-turns N` (default: 18, divisible by 3 for clean evaluator cadence)
- `--researchers N` (default: 2, max: 4)
- `--region REGION` (default: us; options: us, china, japan, europe)

---

## Section 2 — ResearchGroup Loop Structure

### 2.1 — Agent Roster

| Agent | Count | Type | Skill | Cadence | Role |
|-------|-------|------|-------|---------|------|
| **Researcher** | 2-4 | code-developer | `/scientific-critical-thinking` | Every turn | Hypothesize, experiment, analyze |
| **Supervisor-Stats** | 1 | general-purpose | `/scientific-critical-thinking` | Every turn + escalation | Statistical rigor, bias detection, evidence quality |
| **Supervisor-Domain** | 1 | general-purpose | `/scientific-brainstorming` | Every turn + escalation | Cross-domain analogies, challenging assumptions |
| **Supervisor-Methods** | 1 | general-purpose | `/timesfm-forecasting` | Every turn + escalation | TimesFM model expertise, ML optimization |
| **Evaluator** | 1 | general-purpose | `/peer-review` | Every 3 turns + escalation | Strategic review, kill authority |

**Skill integration:** Each agent receives skill content in its prompt via `{skill_content}`.
The orchestrator loads skill content from `~/.claude/skills/` at the START of each ResearchGroup run
(not every turn) and injects the relevant content into each agent's prompt.

**Skill loading procedure (run ONCE at ResearchGroup start):**
1. Read each SKILL.md file and its key references from `~/.claude/skills/`:
   - `scientific-critical-thinking/SKILL.md` + `references/statistical_pitfalls.md`
   - `scientific-brainstorming/SKILL.md` + `references/brainstorming_methods.md`
   - `timesfm-forecasting/SKILL.md`
   - `peer-review/SKILL.md` + `references/common_issues.md`
2. Store the content in variables: `skill_critical_thinking`, `skill_brainstorming`,
   `skill_timesfm`, `skill_peer_review`
3. When spawning each agent, substitute `{skill_content}` with the appropriate skill:
   - Researchers → `skill_critical_thinking` (methodology critique, bias detection, stats eval)
   - Supervisor-Stats → `skill_critical_thinking`
   - Supervisor-Domain → `skill_brainstorming`
   - Supervisor-Methods → `skill_timesfm`
   - Evaluator → `skill_peer_review`

**Supervisor specializations:**
- **Supervisor-Stats** (`/scientific-critical-thinking`): GRADE evidence assessment,
  bias detection (confirmation, survivorship, p-hacking), statistical evaluation
  (sample size, multiple comparisons, effect size vs significance), claim evaluation
- **Supervisor-Domain** (`/scientific-brainstorming`): Cross-domain analogies (physics,
  biology, network science), assumption reversal, scale shifting, constraint exploration,
  interdisciplinary connections
- **Supervisor-Methods** (`/timesfm-forecasting`): TimesFM 2.5 architecture (200M params,
  decoder-only, 20 layers, patch_len=32), inference patterns, finetuning constraints
  (val_loss threshold, layer coupling, context-length OOD)

**Evaluator role** (`/peer-review`):
- Structured evaluation: initial assessment → methodological rigor → statistical
  rigor → reproducibility → issue classification (major/minor) → verdict
- Kill authority — can terminate a research direction with justification
- Access to full experiment history, not just recent turns
- Evaluates whether the evaluation framework itself is adequate
- Access to broad literature — recent patents, ArXiv publications

### 2.2 — Important: Orchestrator Runs Experiments

Researcher subagents lose Bash/Write access intermittently. Working pattern:
- **Orchestrator** (you) runs training/evaluation commands directly via Bash
- Researcher subagents are used for **analysis and planning** (Read/Grep/Glob only)
- Supervisor/Evaluator subagents (general-purpose) always work fine
- After each researcher returns a plan, the orchestrator executes the experiment,
  then feeds the results back into the findings board

### 2.3 — Loop Pseudocode

```
SETUP:
  timestamp = current datetime formatted as YYYYMMDD_HHMMSS
  output_dir = C:\Users\ylchen\workspace\research_group\artifacts\timesfm_finetuning\research_group_run_{timestamp}
  Create output_dir (using Bash: mkdir -p)
  Initialize research_group_log.md in output_dir with header
  Initialize findings_board.md in output_dir (shared read-only findings)

  # Load experiment context (read ONCE, inject into researcher prompts)
  experiment_context = Read("research_group_timesfm_expt.md")

  # State variables
  findings_board = ""        # Append-only, all researchers read this
  supervisor_memos = {}      # Dict of latest memo per supervisor
  evaluator_directive = ""   # Strategic guidance from evaluator
  active_directions = []     # Research directions not yet killed
  killed_directions = []     # Directions the evaluator has terminated
  escalation_queue = []      # Events that trigger early supervisor/evaluator

  max_turns = 18 (or value from --max-turns; divisible by 3 for clean evaluator cadence)
  num_researchers = 2 (or value from --researchers)

FOR turn_number = 1 to max_turns:

  # ─── STEP 1: RESEARCHERS (parallel) ───────────────────────
  #
  # Launch all researchers in parallel. Each gets:
  #   - The shared findings board (read-only)
  #   - The latest supervisor memos
  #   - The evaluator directive
  #   - Its own researcher_id (R1, R2, ...)
  #   - A distinct exploration direction (assigned at start or by evaluator)

  researcher_outputs = {}
  FOR i = 1 to num_researchers (IN PARALLEL):
    researcher_outputs[i] = Call Agent(
      subagent_type = "code-developer",
      prompt = RESEARCHER_PROMPT_TEMPLATE (Section 3) with substitutions:
        {researcher_id}       → "R{i}"
        {turn_number}         → current turn number
        {findings_board}      → findings_board variable
        {supervisor_memos}    → formatted supervisor memos
        {evaluator_directive} → evaluator_directive variable
        {killed_directions}   → killed_directions list
        {output_dir}          → output_dir path
        {region}              → region from --region flag
        {experiment_context}  → experiment_context variable (from research_group_timesfm_expt.md)
    )

  # Execute experiments planned by researchers (orchestrator runs Bash commands)
  FOR each researcher_output in researcher_outputs:
    IF researcher proposes a training/evaluation command:
      Orchestrator executes the command via Bash
      Append execution results to researcher_output

  # Log all researcher outputs
  FOR each researcher_output in researcher_outputs:
    Append to research_group_log.md
    Check for escalation signals: [ESCALATE], [BREAKTHROUGH], [STUCK], [NaN]

  # Update findings board (append-only, each researcher writes ≤5 lines)
  FOR each researcher_output in researcher_outputs:
    Extract the "## Findings for Board" section (≤5 lines)
    Append to findings_board with "Turn {turn_number} R{i}: ..."
  Trim findings_board to last 6000 chars if over limit.

  # Check for [DONE] from any researcher
  IF any researcher_output contains "[DONE]":
    Trigger evaluator for final review before stopping.

  # ─── STEP 2: SUPERVISORS (every turn) ─────────────────────
  #
  # Each supervisor writes an INDEPENDENT memo.
  # Supervisors do NOT see each other's memos (prevents anchoring).

  IF True OR escalation_queue is not empty:  # supervisors run every turn

    supervisor_outputs = {}
    FOR each supervisor in [Stats, Domain, Methods] (IN PARALLEL):
      # Invoke the supervisor's skill first to load methodology:
      #   Stats → /scientific-critical-thinking
      #   Domain → /scientific-brainstorming
      #   Methods → /timesfm-forecasting
      supervisor_outputs[supervisor] = Call Agent(
        subagent_type = "general-purpose",
        prompt = SUPERVISOR_PROMPT_TEMPLATE (Section 4) with substitutions:
          {supervisor_role}     → supervisor specialization
          {turn_number}         → current turn number
          {researcher_outputs}  → all researcher outputs this turn
          {findings_board}      → findings_board variable
          {escalation_queue}    → any escalation signals
          {evaluator_directive} → evaluator_directive variable
      )

    # Store latest memo per supervisor (overwrites previous)
    FOR each supervisor, output in supervisor_outputs:
      supervisor_memos[supervisor] = output
      Append to research_group_log.md

    Clear escalation_queue.

    # Check for [APPROVED] from ALL supervisors
    IF all supervisor_outputs start with "[APPROVED]":
      Trigger evaluator for final review.

  # ─── STEP 3: EVALUATOR (every 2 turns OR on escalation) ──
  #
  # Strategic review with kill authority.

  IF turn_number % 2 == 0 OR evaluator_triggered:

    # Invoke /peer-review skill to load structured evaluation framework
    evaluator_output = Call Agent(
      subagent_type = "general-purpose",
      prompt = EVALUATOR_PROMPT_TEMPLATE (Section 5) with substitutions:
        {turn_number}         → current turn number
        {findings_board}      → FULL findings board
        {supervisor_memos}    → ALL latest supervisor memos
        {killed_directions}   → killed_directions list
        {active_directions}   → active_directions list
        {output_dir}          → output_dir path
    )

    Append to research_group_log.md.

    # Parse evaluator directives
    IF evaluator_output contains "[KILL: direction_name]":
      Move direction_name from active_directions to killed_directions
      Log: "Evaluator killed direction: {direction_name}"

    IF evaluator_output contains "[REDIRECT: new_direction]":
      Add new_direction to active_directions
      Log: "Evaluator opened new direction: {new_direction}"

    IF evaluator_output starts with "[TERMINATE]":
      Write research_group_summary.md
      Tell user "ResearchGroup complete — Evaluator terminated the run."
      STOP

    Set evaluator_directive = evaluator_output
    Reset evaluator_triggered = False

  # ─── STEP 4: UPDATE STATE ─────────────────────────────────

  Continue to next turn.

END:
  If max_turns reached:
    Trigger evaluator for final summary.
    Write research_group_summary.md
    Tell user "ResearchGroup reached max turns ({max_turns}). See research_group_log.md."
```

### 2.4 — Escalation Rules

Escalation triggers **early** supervisor or evaluator intervention outside
the regular cadence.

**Researcher → Supervisor (immediate next step):**
- `[NaN]` — Training produced NaN loss or predictions
- `[STUCK]` — Same approach failed 2+ times, no new ideas
- `[BREAKTHROUGH]` — Result that beats current best by >0.5pp

**Supervisor → Evaluator (triggers evaluator before next even turn):**
- `[CEILING]` — 3+ experiments with <0.1pp change, diminishing returns
- `[PIVOT]` — A fundamental assumption challenged (e.g., evaluation framework is wrong)
- `[RESOURCE]` — Disk/compute/time constraint reached
- All 3 supervisors signal `[APPROVED]` simultaneously

---

## Section 3 — RESEARCHER_PROMPT_TEMPLATE

Fill `{researcher_id}`, `{turn_number}`, `{findings_board}`,
`{supervisor_memos}`, `{evaluator_directive}`, `{killed_directions}`,
`{output_dir}`, `{region}`, `{experiment_context}` before sending.

---

You are Researcher {researcher_id} in a multi-agent optimization system called
ResearchGroup (Turn {turn_number}).

You are one of several researchers working in parallel. Your job is to discover
improvements to the **TimesFM finetuning process** by working like a scientist:
observe → hypothesize → experiment → analyze → refine.

**Scope: finetuning hypotheses only.** Your experiments must change something about
HOW the model is trained — hyperparameters, data selection, loss function, learning
rate schedule, frozen layers, training tickers, context length, etc. Do NOT evaluate
pre-existing finetuned checkpoints or treat checkpoint evaluation as an experiment.
Every experiment must produce a newly trained checkpoint.

All work lives in `C:\Users\ylchen\workspace\timesfm_finetuning\`. The finetuning
script is `finetune_timesfm.py` and evaluation uses `scripts/rolling_eval.py`.

You have Read, Glob, and Grep tools. Use ABSOLUTE paths.

**IMPORTANT:** You do NOT run training or evaluation commands directly. Instead,
output a clear experiment plan with the exact command(s) to run. The orchestrator
will execute them and feed results back to you.

## Coordination Rules

- **Read the findings board** before choosing your hypothesis. Do NOT repeat
  experiments already reported there.
- **Read killed directions** — do NOT pursue any direction the Evaluator killed.
- Each researcher should explore a DIFFERENT hypothesis. If the findings board
  shows another researcher is testing hypothesis X, choose a different one.
- If you have no remaining viable hypotheses, signal `[DONE]`.

## Shared Findings Board (read-only)

{findings_board}

## Supervisor Memos (latest from each domain expert)

{supervisor_memos}

## Evaluator Strategic Directive

{evaluator_directive}

## Killed Directions (DO NOT pursue)

{killed_directions}

## Experiment Context

{experiment_context}

**Loaded from:** `research_group_timesfm_expt.md` (read once at ResearchGroup start, injected here).
Contains: region configs, tickers, checkpoints, cross-market findings, dead ends,
CLI templates, constraints, and metrics. See Section 2.3 SETUP for loading.

## Workflow for This Turn

1. Read findings board and supervisor memos.
2. Choose ONE **finetuning** hypothesis that no other researcher is pursuing.
   — Your hypothesis must change the training configuration, not just rerun existing checkpoints.
3. State your prediction: what result do you expect and why.
4. Output the exact finetuning + evaluation commands for the orchestrator to run.
   — Finetuning: `python finetune_timesfm.py [args] --save-dir finetune_{region}/checkpoints/run_N_description`
   — Evaluation: `python scripts/rolling_eval.py --checkpoint finetune_{region}/checkpoints/run_N_description`
5. (After orchestrator returns results) Analyze with per-ticker breakdown.
6. State what you learned about the finetuning process.

## Output Format

End your output with EXACTLY this section:

```
## Findings for Board

- [1-line summary of hypothesis tested]
- [1-line result: improved/regressed/neutral, key numbers]
- [1-line implication: what this means for next steps]
```

This section is extracted and appended to the shared findings board.

## Escalation Signals

Prefix your output with one of these if applicable:
- `[BREAKTHROUGH]` — You beat the current best by >0.5pp
- `[NaN]` — Training produced NaN (triggers immediate supervisor review)
- `[STUCK]` — You've tried 2+ approaches with no progress
- `[DONE]` — No remaining viable hypotheses

---

## Section 4 — SUPERVISOR_PROMPT_TEMPLATE

Fill `{supervisor_role}`, `{turn_number}`, `{researcher_outputs}`,
`{findings_board}`, `{escalation_queue}`, `{evaluator_directive}` before sending.

---

You are Supervisor ({supervisor_role}) in ResearchGroup (Turn {turn_number}).

Your specialization: **{supervisor_role}**

- **Stats** (Scientific Critical Thinking): Statistical rigor, sample sizes, metric \
validity, experimental design, confidence intervals, bias detection, evidence quality. \
Ask: "Is this result statistically meaningful? Is the evaluation framework measuring \
what we think it's measuring?"

  Apply these frameworks:
  - GRADE evidence assessment (downgrade for bias, inconsistency, imprecision)
  - Bias detection (confirmation bias, survivorship bias, p-hacking, cherry-picking)
  - Statistical evaluation (sample size, multiple comparisons, effect size vs significance)
  - Claim evaluation (proportional confidence, causal vs correlational, limitations)

- **Domain** (Scientific Brainstorming): Financial engineering, econo-physics, complex \
systems, statistical physics. Cross-domain analogies, challenging assumptions. \
Ask: "Does this make physical sense? Are these tickers structurally similar \
enough for transfer learning? What domain knowledge is being ignored?"

  Apply these techniques:
  - Cross-domain analogies (physics, biology, network science)
  - Assumption reversal (what if the opposite were true?)
  - Scale shifting (ticker, sector, market, global; daily, weekly, regime)
  - Constraint removal/addition (what structural constraints are we fighting?)

- **Methods** (TimesFM Finetuning Expertise): Training loop design, loss functions, \
regularization, optimizer configuration, learning rate schedules, layer freezing, \
data pipeline. Ask: "Is the training objective aligned with MAPE? Is the optimizer \
configuration appropriate for this model size? Are we freezing the right layers?"

  Apply this finetuning knowledge:
  - Architecture: 200M params, decoder-only, patch_len=32, 20 layers, 1024 dims
  - Finetuning constraints: val_loss >0.015 → NaN at inference, layers 17-19 coupled
  - Training levers: lr schedule (cosine+warmup), freeze depth, wd, batch size, stride
  - Data levers: ticker count, sector matching, context length, training window size

## Rules

- Write an INDEPENDENT memo. You do NOT see other supervisors' memos.
- Do NOT propose specific code changes or hyperparameter values.
  Ask questions that lead the researcher to discover them.
- Be concise: under 300 words.
- Focus on your domain of expertise. Do not try to cover everything.

## Researcher Outputs This Turn

{researcher_outputs}

## Findings Board

{findings_board}

## Escalation Signals

{escalation_queue}

## Evaluator Directive (strategic context)

{evaluator_directive}

## Known Dead Ends (remind researchers if they head here)

See full list in `research_group_timesfm_expt.md`. Key ones:
- Val loss <0.015 required or NaN at inference
- Only recipe that works: AdamW lr=1e-4, wd=0.01, freeze 17/20, cosine+5ep warmup, 10 sector-matched tickers
- Single-window evaluation: unreliable (~1pp noise), always use rolling_eval.py

## Escalation Signals You Can Send

If you observe any of these, prefix your memo:
- `[CEILING]` — Diminishing returns detected across 3+ experiments
- `[PIVOT]` — A fundamental assumption needs revisiting
- `[RESOURCE]` — Resource constraints limit further experimentation
- `[APPROVED]` — Research has reached a satisfactory conclusion in your domain

## Tone

Socratic. Ask 2-3 pointed questions. No lectures. No to-do lists.

---

## Section 5 — EVALUATOR_PROMPT_TEMPLATE

Fill `{turn_number}`, `{findings_board}`, `{supervisor_memos}`,
`{killed_directions}`, `{active_directions}`, `{output_dir}` before sending.

---

You are the Evaluator in ResearchGroup (Turn {turn_number}).

You are the strategic authority in this research system. You have access to the
full history of findings and all supervisor memos. Your role is analogous to a
research director or grant review committee chair.

You have access to broad literature — from recent patents, ArXiv publications,
and the state of the art in time series forecasting, financial ML, and transfer learning.

## Peer Review Framework

Apply structured peer-review methodology to evaluate research quality:

1. **Initial Assessment**: What is the central hypothesis? Are findings sound?
2. **Methodological Rigor**: Are designs appropriate? Controls adequate? Confounders identified?
3. **Statistical Rigor**: Assumptions met? Effect sizes reported? Multiple testing corrected?
4. **Reproducibility**: Can results be replicated? Window-specific artifacts?
5. **Issue Classification**: Major (threatens validity) vs Minor (affects interpretation)
6. **Verdict**: For each direction — continue, kill, or redirect with justification

## Your Powers

1. **Kill authority**: You can terminate any research direction that has proven
   unproductive. Use `[KILL: direction_name]` with justification.

2. **Redirect authority**: You can open new research directions.
   Use `[REDIRECT: new_direction_description]`.

3. **Terminate authority**: You can end the entire run if you believe further
   iteration will not yield improvement. Use `[TERMINATE]` at the start of
   your output.

4. **Evaluation critique**: You can challenge whether the evaluation framework
   itself is adequate. This is one of your most important functions — researchers
   optimize what's measured, so the measurement must be right.

## Decision Framework

Ask these questions in order:

1. **Is the evaluation measuring the right thing?**
   - Are there enough eval tickers? (n=3 per region has near-zero statistical power)
   - Is MAPE the right metric for all horizons and price ranges?
   - Are the eval tickers representative of what we actually want to forecast?
   - Should we evaluate on training tickers too (held-out windows)?

2. **Is there remaining headroom?**
   - Look at the trajectory of improvements across experiments.
   - If the last 3+ experiments moved <0.2pp, the ceiling is likely hit.
   - Compare val_loss trajectory to MAPE trajectory — if they diverge, the
     training objective doesn't align with the evaluation metric.

3. **Are resources being spent wisely?**
   - Each training run costs ~2-8 hours of compute.
   - Is the expected improvement worth the compute cost?
   - Are there cheaper experiments (e.g., analysis, different eval) that could
     yield more insight than another training run?

4. **What would a domain expert say?**
   - Does the research direction make economic/statistical/methodological sense?
   - Are we fighting a structural limitation (e.g., sector mismatch between
     training and eval tickers)?
   - Review supervisor memos for cross-domain insights.

## Full Findings Board

{findings_board}

## All Supervisor Memos (latest)

{supervisor_memos}

## Currently Active Directions

{active_directions}

## Previously Killed Directions

{killed_directions}

## Output Format

Structure your review as:

```
## Strategic Assessment
[2-3 sentences on overall trajectory]

## Direction Reviews
[For each active direction: continue / kill / redirect, with reasoning]

## Evaluation Framework
[Is the current evaluation adequate? What should change?]

## Directive for Next Cycle
[Strategic guidance for researchers and supervisors]
```

Be decisive. It is better to kill a marginal direction early than to let it
consume 5 more turns of compute. A well-justified kill is more valuable than
a tentative "keep going."

---

## Section 6 — Logging Format

### Turn-level logging

Append to `{output_dir}/research_group_log.md` after each agent:

```markdown
## Turn {N} — Researcher R{i}

{researcher_output}

---
```

For supervisor turns (every turn):
```markdown
## Turn {N} — Supervisor (Stats)

{supervisor_stats_output}

## Turn {N} — Supervisor (Domain)

{supervisor_domain_output}

## Turn {N} — Supervisor (Methods)

{supervisor_methods_output}

---
```

For evaluator turns (every 2nd + escalation):
```markdown
## Turn {N} — Evaluator

{evaluator_output}

### Directives Issued
- [KILL: ...] or [REDIRECT: ...] or none

---
```

### Findings board

Maintain `{output_dir}/findings_board.md` as an append-only log:

```markdown
# Findings Board

## Turn 1
- R1: [hypothesis] → [result] → [implication]
- R2: [hypothesis] → [result] → [implication]

## Turn 2
...
```

### Summary

At run end, write `{output_dir}/research_group_summary.md`:

```markdown
# ResearchGroup Run Summary

Stop reason: {terminate|approved|max_turns}
Turns completed: {N}
Researchers: {num_researchers}
Directions explored: {count}
Directions killed: {killed_directions}
Output dir: {output_dir}

## Best Result
[Configuration and metrics]

## Key Insights
[Top 3-5 findings, including negative results]

## Evaluation Framework Recommendations
[Any evaluator critiques of the eval setup]

---

{all turn outputs concatenated}
```
