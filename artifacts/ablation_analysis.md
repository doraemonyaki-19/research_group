# Ablation Study Analysis
**Date:** 2026-05-28  
**Configs:** B2 (baseline agent), V1 (researcher+supervisor), V2-Full (multi-researcher+evaluator)  
**Seeds:** 42, 137, 271, 314, 1729, 2718, 3141  
**Model:** gemini-2.5-pro  

---

## 1. Run Completion Summary

| Config | Seed | Turns | Stop | Cost | Best MAPE |
|--------|------|-------|------|------|-----------|
| B2 | 42 | 42 | done | $0.62 | 7.69% |
| B2 | 137 | 52 | done | $1.48 | ~8.1% |
| B2 | 271 | 37 | done | $1.15 | 9.67% |
| B2 | 314 | 61 | done | $0.54 | — |
| B2 | 1729 | 75 | done | $1.26 | 2.27%* |
| B2 | 2718 | 160 | max_turns | $1.30 | — |
| B2 | 3141 | 47 | done | $0.88 | — |
| V1 | 42 | 7 | done | $1.84 | 7.4% |
| V1 | 137 | 9 | done | $1.58 | 7.93% |
| V1 | 271 | 40 | done | $12.76 | 5.0% |
| V1 | 314 | 4 | done | $1.27 | — |
| V1 | 1729 | 50 | done | $14.49 | 1.5%* |
| V1 | 2718 | 26 | done | $8.53 | 7.4% |
| V1 | 3141 | 9 | done | $3.81 | ~2%* |
| V2-Full | 42 | 22 | done | $12.43 | 6.87% |
| V2-Full | 137 | 1 | done | $0.80 | 7.4%† |
| V2-Full | 271 | 6 | done | $2.02 | 7.4%† |
| V2-Full | 314 | 11 | done | $2.48 | 8.83%† |
| V2-Full | 1729 | 40 | max_turns | $5.96 | 2.5%* |
| V2-Full | 2718 | 7 | done | $1.49 | 7.93%† |
| V2-Full | 3141 | 24 | done | $5.33 | 5.22% |

*\* Suspicious value — likely single-ticker or short-horizon eval, not the 120d overall MAPE.*  
*† Referenced from prior context (baseline), not newly produced.*

**Total cost: ~$81.74**

---

## 2. Process Metrics by Config

| Config | Median turns | Median cost | % reaching done | Avg MAPE (valid cells) |
|--------|-------------|-------------|-----------------|------------------------|
| B2 | 47 | $0.88 | 86% (6/7) | ~8.5% |
| V1 | 9 | $3.81 | 100% (7/7) | ~7.2% |
| V2-Full | 11 | $2.48 | 86% (6/7) | ~7.1% |

**Key observations:**
- B2 is cheapest but most variable (seed=2718 consumed 3.4× budget of seed=42).
- V1 has the highest tail cost (seed=271 at $12.76, seed=1729 at $14.49 — both ran 40-50 turns doing substantive experiments).
- V2-Full has very short completions (median 11 turns) driven by early environment failures rather than scientific convergence.

---

## 3. Qualitative Findings by Config

### B2 — Single Agent Baseline

The B2 agent operates without supervision and without strategic memory. Behavior was highly seed-dependent:

- **seed=42 (best run):** Methodically swept lr, epochs, and batch size. Converged on 20 epochs as the sweet spot (MAPE 7.69%). Clean and efficient.
- **seed=314:** Focused entirely on val MAE (0.0750) rather than MAPE; no evaluation step run. Spent 61 turns optimizing the wrong metric.
- **seed=1729:** Reported 2.3% MAPE — inconsistent with other cells, likely evaluated on a ticker subset rather than the standard eval set.
- **seed=2718 (worst run):** Spent 160 turns unable to fix a `ModuleNotFoundError` / Python import path issue. Never produced a single MAPE result. Persistent scaffold failures consumed the entire budget.
- **seed=137:** Ended explicitly acknowledging failure — import error was intractable after 52 turns.
- **seed=271:** Found an unusual winning config (freeze_layers=22, stride=32, horizon_loss_decay=0.1) yielding 9.67% MAPE — worse than baseline but the agent considered it an improvement over its starting point.
- **seed=3141:** Found best val MAPE of 0.014 but never ran the evaluation script to get the 120d MAPE.

**B2 failure modes:** (1) scaffold/import errors with no recovery, (2) optimizing proxy metric (val MAE) rather than eval MAPE, (3) non-standard eval scope producing misleading numbers.

### V1 — Researcher + Supervisor

V1 introduced a supervisor that prompted structured experimental reasoning. This consistently improved research quality:

- **seed=42 (most instructive):** Ran 9 experiments within 7 turns. Key finding: increasing weight-decay from 0.01→0.05 improved val MSE (0.0097→0.0072) but *worsened* eval MAPE (9.9%→12.2%). Correctly identified train/eval divergence as the core problem. Best MAPE: 7.4% (run_9 weight-decay experiment).
- **seed=137:** Discovered the log-returns methodology issue (need to predict log returns, then convert back to prices for MAPE). Ended with supervisor probing on implementation correctness — productive, but no final result.
- **seed=271 ($12.76, 40 turns):** Most substantive experimental work of any V1 run. Explored sector routing, peer tickers, freeze layers. Best reported MAPE: 5.0% — the strongest result across all seeds if valid.
- **seed=1729 ($14.49, 50 turns):** Long run focused on oversample-factor sweep and loss-MAPE correlation. Reported 1.5% MAPE — almost certainly evaluated on a narrow ticker set.
- **seed=2718:** Replicated the run_4/run_6 analysis, set a go/no-go threshold of val_mse < 0.009. Best MAPE: 7.4%.
- **seed=314 (4 turns):** Terminated early — got blocked investigating the timesfm directory structure and never trained.
- **seed=3141 (9 turns):** yfinance network failure blocked all data fetching. No experimental results.

**V1 failure modes:** (1) yfinance data dependency failure blocking multiple seeds, (2) early termination before training, (3) high cost when running many experiments without converging.

### V2-Full — Multi-Researcher + Evaluator

V2-Full adds a second researcher and an evaluator who synthesizes findings each turn. The evaluator produced consistently sharp strategic assessments, but the framework was frequently blocked by environment failures:

- **seed=42 (most complete run, $12.43, 22 turns):** Made the most important methodological finding of the study: the training script used random slicing + zero-padding while evaluation used truncation, creating a train-test skew that invalidated all prior baseline metrics. Best MAPE: 6.87% (pre-invalidation). The evaluator correctly declared this finding a reset and the top priority.
- **seed=137 (1 turn, $0.80):** Immediately hit environment failure blocking R1. R2's single experiment falsified the "data dilution" hypothesis. Evaluator called for emergency environment triage. Run terminated after 1 turn.
- **seed=271 (6 turns, $2.02):** One researcher completely blocked, the other pivoted to analyzing existing data. No new experimental results.
- **seed=314 (11 turns, $2.48):** Both researchers blocked on environment. Pivoted to PatchTST as an alternative model — a creative recovery, but produced 0 empirical results.
- **seed=1729 (40 turns, max_turns, $5.96):** Hit network error (`getaddrinfo failed`) on the final turn. Ran the longest of the V2 runs; reported 2.5% MAPE (narrow scope suspected).
- **seed=2718 (7 turns, $1.49):** Evaluator declared "engineering crisis" after 6 turns with zero data points. Run ended.
- **seed=3141 (24 turns, $5.33):** R1 paralyzed by tooling failures; R2 ran productive power analysis. Best MAPE: 5.22%. Evaluator flagged bifurcated trajectory as a structural problem.

**V2-Full failure modes:** (1) environment/tooling failures that cascade across both researchers simultaneously, (2) multi-researcher coordination overhead eating turns without producing results, (3) evaluator correctly diagnosing problems but unable to unblock them.

---

## 4. Key Cross-Config Findings

### Environment fragility is the dominant failure mode
Across all 3 configs, the most common cause of poor runs was not bad science but infrastructure failures: yfinance network errors, ModuleNotFoundError (Python path), and data pipeline mismatches. These affected at minimum 6/21 cells significantly.

### The train-test skew finding (V2-Full/42)
The most scientifically valuable output of the entire ablation was V2-Full/seed=42's identification of a train-test preprocessing skew: the training script used random-length zero-padded sequences while evaluation used truncation. This means all prior MAPE figures from runs using the original `finetune_timesfm.py` should be treated as approximate.

### MAPE ranges (valid cells only)
Cells that completed a full train→evaluate cycle and reported a plausible overall MAPE:

| Config | Seed | MAPE |
|--------|------|------|
| B2 | 42 | 7.69% |
| B2 | 271 | 9.67% |
| V1 | 42 | 7.4% |
| V1 | 137 | 7.93% |
| V1 | 271 | ~5.0% |
| V1 | 2718 | 7.4% |
| V2-Full | 42 | 6.87% |
| V2-Full | 3141 | 5.22% |

Valid range: **5–10%** MAPE. The 1–2.5% values from seeds 1729/3141 across B2/V1 are outliers and likely report on narrow evaluation scopes.

### Cost efficiency
B2 is 4–5× cheaper per run than V1/V2-Full for equivalent turn counts, but its research quality and consistency are lower. V1 delivers the best research value in high-turn runs (seed=271, $12.76, found 5% MAPE). V2-Full's multi-researcher overhead is not justified when environment failures dominate.

---

## 5. Recommendations

1. **Fix environment before next ablation round.** yfinance failures and Python path issues should be resolved at the scaffold level, not left for agents to debug.
2. **Standardize the evaluation script.** The train-test skew finding means MAPE comparisons require a fixed, truncation-based eval pipeline applied consistently.
3. **V1 at 40–50 turns is the sweet spot.** Seeds 271 and 1729 did the most substantive work. Raising the V1 turn limit was the right call.
4. **B2/2718 should be considered a permanent failure cell.** It hit max_turns at 60, 100, and 160 turns across three successive runs. The agent pattern for this seed consistently gets stuck in import/path debugging loops.
5. **V2-Full adds value only when environment is stable.** The evaluator role produces excellent strategic synthesis (seed=42 is evidence), but the framework is fragile — one environment failure blocks both researchers.
