# ResearchGroup — Document, Evaluate, Test, Publish: Project Plan

**Date:** 2026-04-29
**Owner:** ylchen
**Status:** Draft, awaiting decision on Strategic Question 1 below

---

## 0. Executive Summary

The ResearchGroup codebase in this directory is a **substantially modified extension** of the upstream ResearchGroup framework (arXiv:2510.27176, Hamadanian et al., MIT CSAIL, Oct 2025). The framing-honest term is "ResearchGroup." The plan below takes it from working-research-code to published-and-cited contribution in roughly **3-4 months of focused effort**, gated by one strategic decision and three empirical milestones.

**The four phases are not sequential.** Documentation and testing run in parallel with evaluation. Evaluation is the binding gate for publication. **The plan stands or falls on Phase 3 (evaluation) producing defensible head-to-head results.**

---

## 1. Asset Inventory

### Code (`research_group/`)
- `research_group/orchestrator.py` (448 LOC) — main loop, state machine, escalation handling
- `research_group/prompts.py` (469 LOC) — researcher / supervisor / evaluator prompt templates
- `research_group/tools.py` (225 LOC) — tool execution layer
- `research_group/researcher.py` (154 LOC) — researcher agent
- `research_group/evaluator.py` (127 LOC) — evaluator agent (kill / redirect / terminate authority)
- `research_group/supervisor.py` (107 LOC) — supervisor agent (3 specializations)
- `research_group/__init__.py` (16 LOC) — public API
- `run_research_group.py` (110 LOC) — CLI entry, both run modes
- **Total: ~1,656 LOC of framework code** + experiment-context markdown

### Documentation (current state)
- `README.md` — describes **upstream** ResearchGroup (paper summary). Does **not** describe v2 modifications.
- `CLAUDE.md` — describes v2 loop structure and prompts; written for Claude Code execution path. Excellent for that path; not a publication-grade architecture doc.
- `research_group_timesfm_expt.md` — experiment context for TimesFM finetuning (region configs, eval tickers, current bests, dead ends).
- `ResearchGroup.pdf` — upstream paper (reference).
- `requirements.txt` — minimal: `anthropic`, `python-dotenv`, `rich`.

### Empirical results (already in hand)
- **30+ ResearchGroup runs** completed across 4 regions (US, China, Japan, Europe), output dirs in `timesfm/finetune_*/research_group_run_*`.
- **Documented improvements (region-best vs baseline):**
  - US: +0.68pp at 120d
  - China: +6.62pp (17.48% → 10.86% MAPE) — strongest result
  - Japan: +2.20pp at 120d (borderline; std 2.88%)
  - Europe: results in `finetune_europe/finetune_expts/research_group_run_20260326/`
- **Findings boards, evaluator memos, supervisor memos** preserved in run dirs — substantial qualitative evidence of agent reasoning patterns.

### What's NOT in the codebase
- Unit or integration tests
- CI configuration
- API reference / type-stub docs
- Architecture diagram
- Comparison/benchmark suite vs upstream ResearchGroup or other frameworks
- License file
- Contribution guide

---

## 2. The Contribution Claim (what makes v2 different from v1)

This is the core argument the publication will rest on. It must be defensible.

| Dimension | ResearchGroup v1 (upstream) | ResearchGroup (this codebase) |
|---|---|---|
| **Application domain** | GPU-cluster LLM-inference scheduling | Generalized to scientific optimization (TimesFM finetuning) |
| **Agent count** | 2 (Researcher + Supervisor) | 4-7 (2-4 Researchers + 3 specialized Supervisors + 1 Evaluator) |
| **Supervision** | Single, generalist supervisor | Three specialized supervisors (Stats / Domain / Methods) writing **independent** memos to prevent anchoring |
| **Authority** | No kill mechanism | Evaluator with explicit **kill / redirect / terminate** authority |
| **Capability injection** | None | Agent Skill integration: each agent loaded with domain-specific skill (scientific-critical-thinking, scientific-brainstorming, peer-review, timesfm-forecasting) |
| **Coordination state** | Single shared context | **Findings board** as append-only shared knowledge state |
| **Escalation** | Implicit | Explicit signals: `[BREAKTHROUGH]`, `[STUCK]`, `[NaN]`, `[CEILING]`, `[PIVOT]`, `[KILL]`, `[TERMINATE]` |
| **Execution model** | Researcher has direct shell access | Orchestrator runs experiments; researchers plan |
| **Multi-context (MCG)** | Best-of-N parallel runs | Same MCG pattern + within-run parallel researchers |

**The claim space:**
1. **Generalization:** v2 demonstrates the ResearchGroup paradigm transfers from systems optimization to ML hyperparameter / training optimization with non-trivial gains.
2. **Hierarchy improves search:** specialized supervisors + an evaluator with kill authority outperforms flat 2-agent ResearchGroup on search efficiency.
3. **Skill grounding improves agent quality:** loading domain-specific skills into agents at run-start improves output quality vs generic prompting.

**These are the three claims the publication should be tested against. Each requires direct empirical comparison against an ablation-scale baseline.**

---

## 3. STRATEGIC DECISION 1 (BLOCKING) — Upstream Relationship

**This decision must be made before public release of any code, paper, or blog post.** It changes the publication path materially.

### The situation

The upstream ResearchGroup paper authors (Hamadanian, Karimi, Nasr-Esfahany, Noorbakhsh, Chandler, ParandehGheibi, Alizadeh, Balakrishnan) are at MIT CSAIL. ylchen is also at/near MIT CSAIL. **Publishing "ResearchGroup" without engagement with the upstream authors carries reputational risk and forfeits potential collaboration.** Conversely, full-disclosure collaboration carries different tradeoffs.

### Three options

| Option | Description | Pros | Cons |
|---|---|---|---|
| **A. Independent v2** | Publish as a clean fork/extension; cite upstream prominently; do not coordinate | Full credit; fastest timeline | Reputational risk if interpreted as overstepping; weaker MIT alignment |
| **B. Collaborate first** | One email / coffee with one upstream author (likely Hamadanian or Alizadeh); propose merge or joint paper | Strongest political position; potentially stronger paper; MIT-internal goodwill | Slower; possible scope-creep; possible rejection of merge |
| **C. Application paper** | Frame as "Hierarchical Multi-Agent ResearchGroup for Scientific ML Optimization" — application-domain paper, not framework upgrade | Lowest conflict; clear narrative; faster than B | Underplays framework contributions; may not pass framework reviewers |

### Recommendation: **Option B via warm introduction (revised per board review: Oppenheimer).**

**Do not cold-email.** The upstream senior authors (Hari Balakrishnan, NAE member, CMT co-founder; Mohammad Alizadeh) are not people you send a cold proposal to. The approach:

1. **Find a warm introduction** — a mutual colleague, a shared seminar, a CSAIL-internal channel. Budget: 1-2 weeks.
2. **Propose a 30-minute demo, not a paper.** Show them the findings board, the evaluator memos, the supervisor disagreements, and the TimesFM results. Let the work speak before discussing authorship.
3. **Prepare for the most likely outcomes:**
   - *They want to absorb the work* → you become a co-author on ResearchGroup under their umbrella. Good for career (MIT authorship, Balakrishnan's network); you lose sole credit. **Decide now whether you accept this tradeoff.**
   - *Polite indifference* → "go ahead, cite us." You publish Option A, cite heavily.
   - *Hostile* (5-15% probability) → frame as application paper (Option C) with heavy citation.
4. **Decision rule:** If no intro path found in 2 weeks → send a direct but respectful email. If no response to email in 4 weeks (not 2 — faculty timelines are slow) → Option A by default.

**Budget 20-40 hours for this relationship, not 0.5 hours.** This is risk management, not a courtesy.

---

## 4. Phase 1 — Documentation (Weeks 1-6, parallel with all other phases)

### Goal
Produce documentation that lets a (a) reviewer evaluate the work, (b) external user run it on their own task, (c) future contributor extend it.

### Deliverables (trimmed per board review: Jobs)

| # | Deliverable | Effort | Owner | Done when |
|---|---|---|---|---|
| 1.1 | **Updated README.md** — replace v1 summary with v2 architecture, examples, run instructions, citation block | 4-8h | ylchen | A new user can clone, install, run on the included TimesFM task in <30 min |
| 1.2 | **Architecture diagram** — agent topology, data flow, escalation paths | 4h | ylchen | Diagram exists as `docs/architecture.png` and `docs/architecture.md`; explained in README |
| ~~1.3~~ | ~~**API reference**~~ | ~~8-12h~~ | — | **CUT.** 8-12h for 1,656 LOC is poor ROI. No reviewer will check auto-generated docs. |
| 1.4 | **Experiment-context format spec** — generalize beyond TimesFM; document how to write a new `*_expt.md` for a new domain | 4h | ylchen | A reader can write a context file for a new task without reading source |
| ~~1.5~~ | ~~**Migration guide: v1 → v2**~~ | ~~4h~~ | — | **CUT.** No meaningful upstream ResearchGroup user base yet. |
| ~~1.6~~ | ~~**Run-mode comparison**~~ | ~~2h~~ | — | **CUT.** Internal documentation, not a deliverable. |
| 1.7 | **LICENSE** (Apache 2.0 — default; has patent protection MIT lacks) + **CONTRIBUTING.md** | 2h | ylchen | Files exist |
| 1.8 | **Bundle skill content as markdown in repo** — resolve the `~/.claude/skills/` dependency by including skill files as `research_group/skills/*.md` with a loader fallback | 2-4h | ylchen | External users can run v2 without Claude Code or Agent Skill API setup |

### Total Phase 1 effort: ~16-22 hours (was ~30-40h)

---

## 5. Phase 2 — Testing (Weeks 1-4, parallel)

### Goal
Provide a test suite sufficient to (a) prevent regressions during development, (b) signal code quality to reviewers, (c) enable safe refactoring.

### Deliverables

| # | Deliverable | Effort | Done when |
|---|---|---|---|
| 2.1 | **Unit tests** — orchestrator state machine, escalation signal parsing, findings-board append/trim, prompt templating | 12-16h | `pytest` runs in <30s; ≥70% line coverage on `research_group/*.py` (excluding LLM-call paths) |
| 2.2 | **Mock-LLM integration test** — full ResearchGroup run on a tiny problem (mocked Anthropic responses); verify state transitions, log artifacts, summary file written | 8h | `pytest tests/test_full_run_mocked.py` passes; produces all expected artifacts |
| 2.3 | **Smoke test (real LLM)** — single-turn run with real API, gated by `GEMINI_API_KEY` or `ANTHROPIC_API_KEY`; verify the network path works | 4h | `pytest -m smoke` passes when key is set |
| 2.4 | **CI configuration** — GitHub Actions: lint (ruff), unit tests, mock integration test on every PR; smoke test nightly | 4h | Green CI on main; PR template includes test requirement |
| 2.5 | **Pre-commit hooks** — ruff + pytest-fast on changed files | 1h | `pre-commit install` works |

### Total Phase 2 effort: ~30-35 hours

**Note on what's NOT in scope:** end-to-end real-LLM tests on full optimization problems. Those are evaluation runs (Phase 3), not tests.

---

## 6. Phase 3 — Evaluation (Weeks 3-12, the binding gate)

### Goal
Produce defensible head-to-head evidence that v2 outperforms v1 (and reasonable baselines) on at least one task. **Without this, the publication does not exist.**

### 3a. Benchmark task selection

**Recommended: 2-task suite (revised per board review: Jobs — T3 cut permanently).**

| Task | Why | Source | Cost per run |
|---|---|---|---|
| **TimesFM finetuning (the existing application)** | Already have results; simplest re-run | This codebase | ~2-8 GPU-hours |
| **Hyperparameter search on a small ML benchmark** (e.g., CIFAR-10 ResNet-18, or MNIST CNN) | Clean, reproducible, fast — lets you run more seeds | Standard datasets | <30 min |

~~**Re-implement upstream's GPU-scheduling task**~~ — **CUT per board review (Jobs).** If T1+T2 both pass, T3 adds marginal value. If either fails, T3 won't save the paper. Can be added in a revision if reviewers request it.

### 3b. Baselines to compare against (trimmed per board review: Jobs, Burry)

For each task, run 6 configs (was 8):

1. **B0 — Random search / grid search** — trivially weak baseline that demonstrates the problem is non-trivial.
2. **B1 — Single-agent loop** (one researcher, no supervisor, no evaluator) — controls for "is it just LLM agents in a loop?"
3. **B2 — Claude Code in agentic mode** (freestyle, same task description, same compute budget) — controls for "why not just use the chat tool?" *(Added per board review: Burry.)*
4. **V1 — ResearchGroup v1** (as published — 1 researcher + 1 supervisor) — **the most important baseline**; tests whether hierarchy helps.
5. **V2-noSkills — ResearchGroup minus skill injection** — tests H3 (co-headline).
6. **V2-full — ResearchGroup (full)** — the proposed configuration.

**Removed:** v2 minus evaluator, v2 with single supervisor, v2 with 1 researcher. These test secondary architectural choices and can be added in a revision.

### 3c. Metrics

| Metric | What it measures |
|---|---|
| **Best result** | The metric the task optimizes (MAPE for TimesFM; validation accuracy for ML benchmark; latency for systems) |
| **Turns to convergence** | When does improvement plateau (<0.1pp per 3 turns) |
| **Total LLM cost ($)** | Direct dollar cost to reach a given threshold |
| **Insights / kill-correctness** | (Qualitative) does the evaluator's kill decisions align with hindsight? |
| **Variance across seeds** | Run each config 3-5 times with different seeds; report mean ± SE |

### 3d. Multi-seed protocol

**This is non-negotiable for publication.** Single-seed results are not credible.
- **T1: 7 seeds** (revised from 5 per board review: Simons — power 0.6→0.75)
- **T2: 5 seeds**
- Same task budget across configs (max-turns or max-$)
- Pre-register which task / region / horizon is the headline result before running ablations (avoid p-hacking against own data)

### 3e. Deliverables

| # | Deliverable | Effort | Done when |
|---|---|---|---|
| 3.1 | **Benchmark harness** — single script that runs 6 configs on a task, logs everything, computes metrics | 16-24h | One command produces a results CSV + plots |
| 3.2 | **Reproducible TimesFM benchmark** — re-run US region results with seed control (7 seeds × 6 configs = 42 runs) | 20-40 GPU-hours | Multi-seed results tabulated |
| 3.3 | **Small ML benchmark** (Task 2) — full ablation table (5 seeds × 6 configs = 30 runs) | 10-20h compute + 8h analysis | Multi-seed results + plots |
| 3.4 | **ResearchGroup v1 + B2 implementation** — re-implement v1 2-agent protocol + Claude Code freestyle harness | 16-24h | Both run end-to-end on T1 and T2 |
| 3.6 | **Results write-up** — tables, plots, statistical tests (paired t-test or Mann-Whitney) | 12-16h | Draft paper figures + captions ready |

### Total Phase 3 effort: ~50-90 hours of human time + 84-366 GPU-hours (revised)

### Decision gates

**Kill gate (after T1, per board review: Buffett):** If V2-full does not beat V1 by ≥0.25 SE on any of the three primary metrics → ABORT T2 and redirect to documentation + GitHub release. See `EVALUATION_PROTOCOL.md` §7.1.

**Decision gate (after T1+T2):**
- Does v2 beat v1 by ≥1 standard error on ≥2 metrics across ≥2 tasks? → proceed to Phase 4 (full paper).
- Does v2 beat v1 on T1 but not T2? → use the forecasting-specific fallback paper outline (§9a below).
- Does v2 tie v1? → restructure publication as "we show v2 doesn't hurt; offers other benefits (interpretability, kill authority)." Lower-tier venue.
- Does v2 *underperform* v1? → publish as honest negative result + framework documentation; significantly de-prioritize publication.

---

## 7. Phase 4 — Publishing (Weeks 8-16, conditional on Phase 3)

### Venue ladder (parallel paths, choose based on Phase 3 results)

| Venue | Standard | Lead time | Effort | When |
|---|---|---|---|---|
| **arXiv preprint** | None (just review) | 0 (instant) | 1 week of prep | Always — first move |
| **GitHub release + technical blog post** | Engineering audience; informal | 0 | 1-2 weeks | After arXiv; uses same writing |
| **Workshop paper** (NeurIPS / ICML / ICLR workshops on agents, ML4Sys, AutoML) | Light review; smaller audience | 1-3 months | 2-3 weeks of writing | After preprint, if results are solid |
| **Main-track conference** (NeurIPS / ICML / ICLR) | Strong empirical bar | 6-9 months | 4-8 weeks of writing | Only if results are strong AND comparison vs upstream ResearchGroup is direct |
| **Journal** (JMLR, Nature MI) | Strongest review; longest cycle | 9-18 months | 8-12 weeks | Long-term option |

### Recommended path (revised per board review: arXiv at Week 6)

1. **Weeks 1-2:** warm introduction to upstream authors (Strategic Decision 1).
2. **Week 6:** arXiv preprint v0.1 — minimum viable description of v2 + Phase 3 T1 results. **Ship rough. Polish later. The timestamp is the moat.** *(Moved from Week 8-10 per board review: Munger, Jobs.)*
3. **Week 7-8:** GitHub release v0.1 with reproduction artifacts. **Release simultaneously with or before preprint, not after.** *(Per board review: Brin — researchers discover tools on GitHub, not arXiv.)*
4. **Week 8-10:** workshop submission — workshop deadlines 2026 NeurIPS workshops are typically July-Sept. Aim for one of: ML4Sys, NeurIPS Agents, AutoML.
5. **Week 10+:** main-track or journal — only if Phase 3 results are unambiguous wins.

### If upstream is non-responsive (Option A fallback)

Same as above, but every artifact must include a prominent comparison with v1 in the abstract / first figure. Reviewers will compare anyway; better to control the framing.

### Publication artifacts checklist

Before any submission:
- [ ] arXiv-style PDF with figures
- [ ] Frozen GitHub release tagged with paper version
- [ ] Reproduction script that regenerates every figure from raw data
- [ ] Anonymized review version (for double-blind venues)
- [ ] Author response template
- [ ] Pre-registered metrics for the headline claim
- [ ] CITATION.cff in repo

---

## 8. Timeline & Critical Path (revised per board review: 10 weeks, not 16)

```
Week  1  2  3  4  5  6  7  8  9  10
──────────────────────────────────────
UP    ▓▓▓▓     ← upstream warm intro + demo
P1    ▓▓▓▓▓▓                          Documentation (trimmed)
P2    ▓▓▓▓                            Testing
PILOT ▓▓                              T1 single-seed pilot (B0, B2, V1, V2-full)
GATE     ▓  ← PILOT GATE (cost check)
P3a      ▓▓▓▓▓▓▓                      T1 full ablation (6 configs × 7 seeds)
KILL        ▓  ← KILL GATE (abort or proceed to T2)
P3b         ▓▓▓▓▓▓                    T2 ablation (6 configs × 5 seeds)
P4a           ▓▓▓                     arXiv preprint (Week 6!)
P4b              ▓▓                   GitHub release + repo cleanup
P4c              ▓▓▓▓▓               Workshop paper (NeurIPS deadline)
```

### Critical path
**Upstream intro (Weeks 1-2) → T1 pilot (Weeks 1-2) → T1 full ablation (Weeks 3-5) → KILL GATE → T2 (Weeks 5-7) → arXiv preprint (Week 6!)** — everything else can flex.

### Effort budget (revised)
- **Total ylchen effort:** ~116-187 hours (~20-25% reduction from original).
  - Phase 1 (Documentation): 16-22h (was 30-40h)
  - Phase 2 (Testing): 30-35h (unchanged)
  - Phase 3 (Evaluation): 50-90h (was 80-160h)
  - Upstream relationship: 20-40h (was 0.5h)
- **Total compute:** ~84-366 GPU-hours.
- **Total LLM API cost** (estimate at Claude Sonnet 4 / Gemini 3.1 Pro rates): **$300-930** (was $300-1,500).

---

## 9. Risks & Mitigations

| Risk | Probability | Impact | Mitigation |
|---|---|---|---|
| Upstream authors decline collaboration AND object to independent publication | 5-15% | High | Frame v2 as application + extension; ensure prominent v1 citation; prepare to re-frame if needed |
| Phase 3 shows v2 ties or loses to v1 | 25-40% | High | Run pilot ablations early (Week 3-4); use early signal to re-scope publication if needed |
| Insufficient GPU compute for multi-seed runs | 30% | Medium | Use small ML benchmark (Task 2) for ablations; reserve GPU for headline TimesFM runs only |
| API cost overrun | 20% | Medium | Cap each ablation cell at $20 LLM spend; use Haiku for cheap ablation runs, Sonnet for headline |
| Documentation drifts from code during Phase 3 | 50% | Low | Make Phase 1 last to finalize; keep README skeleton until Phase 3 done |
| Reviewers want a third evaluation task (the GPU-scheduling one) | 40% | Medium | Note in paper that T3 was considered and cut for scope; available for revision. Can be added if reviewers require it |
| Publication scoop by another group on hierarchical multi-agent science | 10-20% | High | arXiv preprint at **Week 6** (revised from Week 8) regardless of paper polish |
| Framework breaking change in LLM Provider API mid-evaluation | 5-15% | Medium | Pin SDK version in `requirements.txt`; record API version in run logs; skill content bundled as markdown fallback (Phase 1.8) |

---

## 10. Immediate Actions (this week)

In priority order:

1. **Today / Day 1:** decide on Strategic Decision 1. Draft the upstream-author email. Send it.
2. **Day 1-2:** create a `tests/` directory; write the first unit test (orchestrator escalation-signal parsing) — establishes the testing pattern for everything else.
3. **Day 2-3:** write a 1-page ablation pre-registration document committing to specific metrics and seed protocol *before* running any ablations. Save as `EVALUATION_PROTOCOL.md`. Critical for credibility.
4. **Day 3-5:** run a small Phase 3a pilot — ResearchGroup vs ResearchGroup v1 vs single-agent on a single TimesFM region with 1 seed. Use this to estimate effort and de-risk the full ablation.
5. **Day 5-7:** based on pilot results, decide whether to commit to the full plan or re-scope. If pilot looks good, schedule the multi-seed runs.

---

## 11. Open Questions

- **Naming.** Is "ResearchGroup" the right name, or should it be a distinct name (e.g., "ResearchGroup-H" for hierarchical, or a fresh name)? Decision affects upstream relationship and citation. Recommend resolving in the upstream-author conversation.
- **Domain branding.** Should this be marketed as "general scientific optimization framework" or "ResearchGroup for ML optimization"? The first is venture-relevant (per the Apr 29 strategy meeting); the second is publication-relevant. Both can be true; the publication should pick one frame.
- ~~**Open-sourcing the experiment context (`research_group_timesfm_expt.md`).**~~ **RESOLVED per board review (Brin):** Contains public equities and publicly available price data via yfinance. No proprietary information. Fine to release.
- ~~**Skill content distribution.**~~ **RESOLVED per board review (Brin):** Bundle skill content as markdown files in `research_group/skills/*.md` with a loader fallback. Agent Skill API is the primary path; bundled files are the fallback for external users. See Phase 1 deliverable 1.8.

---

## 9a. Forecasting-Specific Fallback Paper Outline (added per board review: Munger)

**Use this outline if T1 passes but T2 fails.** The headline becomes "Hierarchical multi-agent ResearchGroup for time-series forecasting optimization" — a domain paper, not a general framework paper.

1. **Title:** "Hierarchical Multi-Agent Optimization of Time-Series Foundation Models: A Case Study with TimesFM"
2. **Framing:** Application paper, not framework upgrade. v2 is the tool; TimesFM finetuning is the contribution.
3. **Contribution claims (narrowed):**
   - H1 (generalization from systems → forecasting) — confirmed
   - H2 (hierarchy helps for forecasting) — confirmed on T1
   - H3 (skill injection helps for forecasting) — confirmed on T1
   - *Explicitly note:* "generality beyond forecasting is not demonstrated; T2 results were negative/neutral."
4. **Venue targets:** Workshop (ML4Sys, AI4Science); NOT main-track framework venue.
5. **Advantage:** faster to write, lower review bar, honest about scope.

Having this outline ready means a T2 failure does not create a 2-week scramble to reframe.

---

## 12. Success Definition

This plan succeeds if **at the end of 10 weeks** (revised from 16) the following are true:

- [ ] An arXiv preprint is published describing ResearchGroup with the contribution claims (H2+H3 co-headlines) defended by ≥1-task multi-seed evaluation (≥2-task if T2 passes).
- [ ] The GitHub repo has a clean public release with documentation, tests, CI, and a one-command reproduction.
- [ ] At least one upstream ResearchGroup author has reviewed (formally or informally) the v2 contribution and either co-authored, endorsed, or non-objected to its publication.
- [ ] Phase 3 results are quantitatively consistent (no overclaiming) and the negative results are reported alongside the positive ones.

If any of those four are missing, the project is not done — the plan is recursive on whichever item is unfinished.
