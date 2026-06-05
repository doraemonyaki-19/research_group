# ResearchGroup — Evaluation Protocol (pre-registration)

**Date frozen:** 2026-05-01 (original) | **Revised:** 2026-05-01 per board review
**Status:** Pre-registered before ablation runs. Board recommendations from `research_group_publishing_plan_review_may2026.md` incorporated. Any change after this date must be tracked in §11.

---

## 0. Why pre-register

The publishing plan (`PUBLISHING_PLAN.md` §6) makes Phase 3 the binding gate for publication. Without pre-registered metrics and protocol, "v2 beats v1" is post-hoc selection from however many things were measured. This document commits the metrics, the configurations, and the pass/fail criteria *before* any ablation is run, so the headline result cannot be the product of researcher degrees of freedom.

The TimesFM portfolio work in this repo paid an explicit overfit tax (15-50% IS→OOS shrinkage was *the* finding of `sector_routing_results.md`). The same discipline applies here: define the rules, then run.

---

## 1. Hypotheses

Three claims from `PUBLISHING_PLAN.md` §2 are tested:

- **H1 — Generalization.** ResearchGroup transfers from systems optimization to ML training/hyperparameter optimization with non-trivial gains over a no-agent baseline. *(Sanity check — necessary but not sufficient for publication.)*
- **H2 — Hierarchy improves search.** *(Co-headline.)* v2's hierarchical configuration (multiple researchers + 3 specialized supervisors + evaluator with kill authority) outperforms v1's flat 2-agent configuration on at least one of {best result reached, turns to convergence, $ to threshold}.
- **H3 — Skill grounding improves agent quality.** *(Co-headline.)* v2 with skill injection beats v2 without skill injection on best-result-reached. This is the most generalizable contribution — skill injection can be adopted by any agent framework.

H1 is a sanity check. **H2 and H3 are co-headlines.** Either alone is sufficient for the framework story; both together make the strongest paper. H3 is highlighted as the most transferable contribution (per board review: Feynman).

---

## 2. Tasks

| ID | Task | Why | Status |
|---|---|---|---|
| **T1** | TimesFM finetuning, US region (NVDA, UNH, GS, CVX, KO, BA held-out; six S&P training tickers) | Existing application; results already partially known | Primary task; run first |
| **T2** | Small ML benchmark — hyperparameter search on a CIFAR-10 ResNet-18 (or MNIST CNN if CIFAR proves too slow per ablation cell) | Reproducible, cheap, lets us afford more seeds | Primary task; run after T1 pilot |
| ~~**T3**~~ | ~~Re-implementation of upstream's GPU-scheduling task~~ | ~~Direct head-to-head with v1 on its home turf~~ | **CUT per board review (Jobs).** If T1+T2 both pass, T3 adds marginal value. If either fails, T3 won't save the paper. |

**T1 is the headline.** T2 is the variance check: if T1 passes but T2 fails, the headline is "v2 helps for forecasting tasks specifically" — and the fallback paper outline (see `PUBLISHING_PLAN.md` §9a) should be used. If both pass, the headline is "v2 helps generally."

---

## 3. Configurations under test

For each task, the following configurations are run. Configurations are immutable once this document is frozen.

| ID | Config | What it tests |
|---|---|---|
| **B0** | Random / grid search over hyperparameters with the same compute budget as the agent runs | Trivial baseline — answers "is the problem non-trivial?" |
| **B1** | Single-agent loop: one LLM in a loop, no supervisor, no evaluator | Controls for "is it just LLM-in-loop?" |
| **B2** | **Claude Code in agentic mode** — given the same task description and compute budget, no framework, freestyle | Controls for "why not just use the chat tool?" The reviewer's first question. *(Added per board review: Burry)* |
| **V1** | ResearchGroup v1 — 1 researcher + 1 supervisor (re-implemented in this repo, see §3.1) | The load-bearing baseline for H2 |
| **V2-noSkills** | v2 full, but agents prompted without skill injection | Tests H3 (co-headline) |
| **V2-full** | v2 as currently configured (2 researchers, 3 specialized supervisors, evaluator with kill authority, skill injection) | The proposed configuration |

**Configs removed per board review (Jobs):** V2-min, V2-noEval, V2-1res. Rationale: V2-min is a code-base control that adds complexity without testing a headline hypothesis. V2-noEval and V2-1res test secondary architectural choices (kill authority, parallelism) that are not load-bearing for H2 or H3. These can be added in a revision if reviewers request them.

### 3.1 ResearchGroup v1 re-implementation

The v1 baseline must be re-implemented in this repo to share the harness. The re-implementation is constrained to:
- Two agents (researcher + generalist supervisor)
- No specialized supervisors, no evaluator, no kill authority
- No skill injection
- Same model and same per-turn budget as V2 configurations
- Researcher has shell access (matches upstream paper); orchestrator does not run experiments
- MCG (multi-context ResearchGroup) variant deferred — V1-SCG (single-context) is the comparison

Code lives in `research_group/v1_baseline.py`; tests pin its agent count and absence of evaluator state.

---

## 4. Metrics

### 4.1 Primary metrics (pre-registered, the only ones that determine pass/fail)

| Metric | Aggregation | Direction |
|---|---|---|
| **best_result** — best task-specific score reached during the run (T1: lowest 120d MAPE on held-out; T2: highest val accuracy; T3: lowest mean latency) | per seed, then mean ± SE across seeds | Lower for T1; higher for T2; lower for T3 |
| **turns_to_threshold** — turns required to reach 80% of V2-full's median best_result for that task | per seed, then mean ± SE | Lower is better |
| **dollars_to_threshold** — total LLM API spend to reach the same 80% threshold | per seed, then mean ± SE | Lower is better |

### 4.2 Secondary metrics (reported, not used for decision)

- **Insight rate** — number of distinct hypotheses tested per turn
- **Kill correctness** — for V2-full only: of N evaluator-killed directions, what fraction would a held-out human reviewer also kill (50-direction sample, blind review)
- **Variance** across seeds for best_result (lower is better; signals robustness)
- **Compute footprint** — GPU-hours for the underlying experiment runs

### 4.3 Exploratory metrics (descriptive, no claims attached)

- Findings-board entropy, supervisor-memo length distribution, escalation-signal frequency. Anything else that emerges. Reported in an appendix; cannot drive headline claims.

---

## 5. Seeds & sample sizes

- **Number of seeds per (task × config) cell:** **7 seeds** for T1: `{42, 137, 271, 314, 1729, 2718, 3141}`. **5 seeds** for T2: `{42, 137, 271, 314, 1729}`. *(T1 increased from 5→7 per board review (Simons): buys statistical power from ~0.6 to ~0.75 for paired Wilcoxon at medium effect size. Marginal cost: ~$80-240 LLM + 16-64 GPU-hours.)*
- **What "seed" controls:**
  - LLM sampling temperature seeded via `system_fingerprint` request when supported; otherwise re-runs are independent samples
  - Random initialization of the underlying ML task (where applicable)
  - Order of researcher assignment / hypothesis exploration randomization
  - **Pin Anthropic SDK version, model version, and request-level seed in every run's JSON log.** Cross-version comparisons are not valid. *(Added per board review: Simons.)*
- **Same task budget across configs.** Total turns capped at `max_turns = 18` for v2 configs and `max_turns_v1 = 54` for V1. *(Revised 2026-05-08: V2 reduced from 27 → 18 turns to compensate for the denser supervisor / evaluator cadence — see §11 change log.)* V1 retains 54 turns since its cadence (researcher + supervisor every turn) is unchanged. The per-cell agent-call counts now match: V1 = 54 × 2 = 108 calls; V2 = 18 × ~5.3 ≈ 96 calls. B0 (grid) gets compute-equivalent number of trials. B1 and B2 get `max_turns = 27` (their per-turn cost is unchanged).
- **Pilot first.** Before the full multi-seed run on T1, run a single-seed pilot (seed 42) across **B0, B2, V1, V2-full** only. This is to estimate cost per cell and time per cell. Pilot results do **not** count toward the headline decision; they only inform whether to commit to the full ablation.

---

## 6. Statistical analysis plan

### 6.1 Primary test for H1 (generalization)

V2-full vs B0 (random/grid search) on **best_result**, paired across seeds.
- **Test:** paired Wilcoxon signed-rank (non-parametric; n=7 for T1, n=5 for T2).
- **Pass criterion:** p < 0.05 AND v2-full's mean improvement over B0 ≥ task-specific minimum effect size (T1: 0.5pp MAPE at 120d; T2: 1pp validation accuracy).

### 6.2 Primary test for H2 (hierarchy)

V2-full vs V1 on each of {best_result, turns_to_threshold, dollars_to_threshold}, paired across seeds.
- **Test:** paired Wilcoxon signed-rank for each of the three metrics.
- **Pass criterion (per the publishing plan §6 decision rule):** v2 beats v1 by ≥1 SE on **≥2 of 3 metrics** AND across **≥2 of 2 tasks** (T1 and T2).
- **Multiple-comparisons correction:** since 3 metrics × 2 tasks = 6 tests, apply Benjamini-Hochberg FDR control at q=0.10. Headline "win" requires the BH-corrected criterion to hold.

### 6.3 Primary test for H3 (skills)

V2-full vs V2-noSkills on best_result, paired across seeds.
- **Test:** paired Wilcoxon signed-rank.
- **Pass criterion:** p < 0.05 AND v2-full mean > v2-noSkills mean by at least 0.5 SE.

### 6.4 Robustness checks

- **Leave-one-seed-out:** drop each seed in turn; do the qualitative conclusions hold? Reported in appendix.
- **Best-of-N reframing:** for V2-MCG variants in future work, Best-of-N is the right comparison. *Not in scope* for this protocol.

### 6.5 What we will NOT do

- No metric-shopping: only the metrics defined in §4.1 determine pass/fail.
- No post-hoc seed exclusion. If a seed produces an outlier, it stays in the analysis and is reported; an appendix can break it out, but it does not move the headline.
- No mid-run early stopping based on intermediate results to "save compute." Either commit the budget or don't run the cell.

---

## 7. Pilot decision gate

After the §5 pilot (single seed on T1 with B0, B2, V1, V2-full):

| Pilot result | Action |
|---|---|
| V2-full and V1 cost <2× more than budgeted per cell | Proceed to full multi-seed T1. |
| Costs exceed estimate | Reduce T1 seeds from 7 to 5; keep all 6 configs. |
| V2-full crashes / produces unusable output on >25% of pilot turns | Pause and debug; do not run multi-seed until fixed. |
| V2-full underperforms V1 in pilot | Continue full ablation regardless — the pilot is *not* a decision gate on the science, only on the compute. Negative result is still publishable. |

### 7.1 Kill gate (added per board review: Buffett)

**After the full T1 multi-seed ablation (all 6 configs × 7 seeds = 42 runs):**

If V2-full does **not** beat V1 by ≥0.25 SE on **any** of the three primary metrics (best_result, turns_to_threshold, dollars_to_threshold):

→ **ABORT full T2 ablation.** Redirect remaining effort to:
1. Documentation + GitHub release (Phase 1 + Phase 2 deliverables)
2. Publish framework as a negative-result technical report + open-source release
3. Do NOT spend the remaining ~$120-400 and 40 GPU-hours on T2

If V2-full beats V1 by ≥0.25 SE on **at least one** metric → proceed to T2.

**Rationale:** The pilot gate (§7 above) tests compute feasibility. This kill gate tests scientific signal. If T1 shows no signal after 42 runs with 7 seeds, additional tasks will not rescue the hypothesis. The honest move is to publish as documentation + framework contribution, not to search for a task where v2 happens to win.

---

## 8. Stopping rules (run-level)

A single run is stopped before reaching `max_turns` only if:
- Evaluator issues `[TERMINATE]` (defined behavior, expected)
- All three supervisors emit `[APPROVED]` simultaneously (defined behavior)
- An exception interrupts the run (unhealthy; flagged for review)

There are **no other early-stopping conditions**. In particular, there is no "stop because we're not making progress" heuristic — that's the evaluator's job. If the evaluator does not call it, the run continues.

---

## 9. Cost & time budgets

| Task | Cells | Seeds/cell | Est. LLM $ per cell-seed | Est. compute / cell-seed | Total LLM $ | Total compute |
|---|---|---|---|---|---|---|
| T1 | 6 configs | 7 | $5-15 | 2-8 GPU-hours | $210-630 | 84-336 GPU-hours |
| T2 | 6 configs | 5 | $3-10 | <1 GPU-hour | $90-300 | <30 GPU-hours |
| **Total (T1+T2)** | | | | | **$300-930** | **84-366 GPU-hours** |

Cost ceiling: if Phase 3 LLM spend exceeds **$1,200**, pause and re-evaluate. Compute ceiling: if GPU-hours exceed **400**, same.

*Budget revised per board review: fewer configs (8→6) but more seeds on T1 (5→7). T3 removed. Net effect: comparable total cost, better statistical power on headline task.*

---

## 10. Deliverables

- `benchmarks/run_ablation.py` — single-command harness; takes a task ID + config matrix; produces a results CSV
- `benchmarks/results/{task}/{config}/seed{N}.json` — raw per-run logs (full turn history, costs, timings)
- `benchmarks/results_aggregate.csv` — cell × metric table
- `benchmarks/figures/` — fig 1 (best_result distribution per config), fig 2 (turns_to_threshold), fig 3 (dollars_to_threshold)
- `benchmarks/REPORT.md` — narrative results, decision-gate verdicts, what changed (§11)

---

## 11. Change log (must be updated for any post-registration change)

A change after this protocol is frozen is acceptable only if it (a) makes the comparison more rigorous (e.g., adding a test) or (b) corrects a clear bug. Removing a test or changing a pass criterion in a way that favors V2-full **without** loosening it for v1 is forbidden.

| Date | Change | Why | Affects headline? |
|---|---|---|---|
| 2026-05-01 | Configs reduced 8→6: dropped V2-min, V2-noEval, V2-1res; added B2 (Claude Code freestyle) | Board review (Jobs: focus; Burry: missing baseline) | No — makes comparison more rigorous by adding a practical baseline |
| 2026-05-01 | T1 seeds increased 5→7 | Board review (Simons: statistical power 0.6→0.75) | No — increases rigor |
| 2026-05-01 | T3 cut permanently | Board review (Jobs: marginal value if T1+T2 pass) | No — reduces scope, does not weaken remaining tests |
| 2026-05-01 | Kill gate added after T1 full ablation (§7.1) | Board review (Buffett: explicit abort criterion) | No — adds rigor |
| 2026-05-01 | H3 promoted to co-headline with H2 | Board review (Feynman: most generalizable contribution) | Yes — reframes the paper's contribution hierarchy |
| 2026-05-08 | V2 cadence: supervisors every turn (was every 3); evaluator every 3 turns (was every 9). V2 max_turns: 27 → 18 to keep per-cell agent-call count comparable to V1 (~108 calls/cell). | Pilot showed V2 underused supervisor/evaluator critique at the 1-in-3 / 1-in-9 cadence — most stalls and direction errors went uncaught until late. Denser cadence increases per-turn rigor; fewer turns keeps cost flat. | No — total per-cell agent-call budget unchanged; H2/H3 comparisons stay symmetric across configs because V1's cadence and budget are unchanged. |

---

## 12. Reviewer questions this protocol pre-empts

- *"How did you pick these specific metrics?"* → §4 was frozen 2026-05-01.
- *"Why this many seeds?"* → §5; T1 uses n=7 (power ~0.75 for medium effect at paired Wilcoxon); T2 uses n=5. We report SE and CI, not just p-value.
- *"Why these specific ablations?"* → §3; each strips one architectural feature from V2-full to isolate its contribution. Board review trimmed to the minimal matrix testing all three hypotheses.
- *"What if v2 doesn't win?"* → §6 and §7.1; the decision rule, the publishing-plan §6 gate, and the post-T1 kill gate explicitly cover negative-result handling.
- *"Did you cherry-pick the task?"* → T1 is the existing application (so yes, results were partially known); T2 is a clean held-out task that was selected before any v2-vs-v1 result existed.
- *"Why not compare against Claude Code / other agent tools?"* → B2 (Claude Code freestyle) is in the matrix. Broader framework comparisons (FutureHouse, Anthropic AAR) are deferred to follow-up; see §13.

---

## 13. Anti-checklist (things this protocol does NOT pretend to do)

- It does not establish that v2 is "better" in any absolute sense — only that it is better than the specific configurations tested under the specific metrics defined.
- It does not address whether v2 is more interpretable, easier to deploy, or cheaper to operate at scale. Those are claims for separate evaluation.
- It does not test against newer agent frameworks (e.g., FutureHouse aviary, Anthropic AAR) that have appeared since the v2 design was frozen. Those comparisons belong in a follow-up.
- It does not establish causal mechanism: even if V2-full beats V1, this protocol cannot distinguish "the hierarchy helps" from "the hierarchy plus the prompts plus the orchestrator-runs-experiments pattern jointly help." Mechanism teasing-apart is what the ablations *attempt* but only partially achieve.
