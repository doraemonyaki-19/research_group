# ResearchGroup Run Log
Started: 2026-05-31 10:34:53
Region: us | Max turns: 18 | Researchers: 2

---

## Turn 1 — Researcher R1

**Hypothesis:** Rewrite validation + clean baseline replication using exp_11 recipe (--seed 42, full flag set)
**Verified fixes:** log transform in __getitem__, masks=zeros, optimizer selection, exp-transform in eval
**Proposed run:** run_t1r1_baseline

### Commands (to execute)
Training: finetune_timesfm.py with --tickers "^GSPC,AAPL,JNJ,JPM,XOM,PG,CAT,NEE,AMT,WMT" --lr 1e-4 --optimizer adamw --wd 0.01 --freeze-layers 17 --warmup-epochs 5 --early-stopping 15 --stride 32 --seed 42
Eval: rolling_eval.py --tickers NVDA,UNH,GS,CVX,KO,BA --horizons 5,14,30,60,90,120 --n-windows 15

### Findings for Board
- Hypothesis: rewritten scripts with exp_11 recipe reproduce ~7.7% 120d MAPE baseline.
- PENDING — commands proposed, awaiting execution.
- Success validates rewrites; failure means debug before any further experiments.

---

## Turn 1 — Researcher R2

**Hypothesis:** --horizon-loss-decay 0.5 improves short-horizon MAPE by down-weighting long-horizon gradient noise
**Analysis:** decay=0.5 gives ~1.6x near/far weight ratio; renormalized so loss scale unchanged; clean ablation vs baseline
**Proposed run:** run_t1r2_hdecay05

### Commands (to execute)
Training: same as R1 but add --horizon-loss-decay 0.5
Eval: same eval setup as R1

### Findings for Board
- Tested --horizon-loss-decay 0.5 (moderate exponential down-weighting of horizon 60-128) vs. uniform MSE
- PENDING — commands proposed, awaiting execution.
- If 120d MAPE degrades >15% vs baseline, abandon; if positive/neutral at 120d, escalate to decay=1.0.

---

## Turn 1 — Supervisor (Stats)

**MEMO — Supervisor-Stats (Turn 1)**

Power problem: 6 tickers × 15 windows = 90 forecast episodes, but if windows are temporally overlapping the effective n may be ~15. A 1pp MAPE difference is marginally detectable at best (~60-75% power assuming independence).

**Question 1:** What is the actual temporal overlap structure of the 15 evaluation windows across 6 tickers? Has anyone computed the effective number of independent forecast episodes?

**Question 2:** Seed-to-seed MAPE variance from exp_1-exp_11 runs — was the 15% abandonment threshold for R2 derived from that distribution or chosen arbitrarily? If seed variance is ~5-8pp, the threshold is indistinguishable from noise.

**On historical priors:** exp_1-exp_11 MAPE numbers are contaminated by the rolling_eval.py masks bug. The 7.7% target should be treated as provisional until R1 confirms it under the corrected evaluation.

---

## Turn 1 — Supervisor (Domain)

**MEMO — Supervisor-Domain (Turn 1)**

**On horizon weighting:** R2's decay hypothesis assumes near-term forecasts are "more actionable," but if the downstream use case is 120-day positioning then suppressing the 120d gradient means explicitly training the model to be wrong about what we care about. The question is: is 120d MAPE high-variance because the market is unpredictable at that horizon, or because the model lacks inductive bias to distinguish regime from noise? Down-weighting the loss papers over the second problem without testing the first.

**Question 1:** If the investment use case is 120d position sizing, why is near-term accuracy being prioritized in training? Does "actionable" mean daily rebalancing, or does it mean the forecast is used at deployment for a multi-month decision?

**Question 2:** NVDA has 3-5x the realized volatility of AAPL or PG. Does the model's RevIN normalization span enough distributional range in training to generalize to high-volatility tickers? Is there an analogue for NVDA in the training set?

**Question 3:** RevIN applied to log(price) normalizes levels, not incremental returns. Two tickers with identical return processes but different price levels will receive different normalization. Is the model learning price momentum (a levels effect) rather than return structure?

---

## Turn 1 — Supervisor (Methods)

**MEMO — Supervisor-Methods (Turn 1)**

**Question 1:** TimesFM output_patch_len=128 produces all 128 horizon steps from a single forward pass. When you apply position-dependent weights to that patch and reduce to a scalar, does the gradient back through the output projection actually differ in direction versus magnitude? Or does the decay simply rescale the scalar, leaving gradient direction unchanged? R2 should verify whether early-horizon positions receive meaningfully larger gradient signal at the projection weights.

**Question 2:** Are layers 17-19 the final transformer blocks, or is there a separate output projection head above them? If the final projection (model-dim → output-patch-dim) is a distinct module, "train last 3 transformer layers" and "train the output head" are different experiments. Has the research confirmed which named parameters are actually updated?

**Question 3:** MSE on log-prices penalizes symmetric log-errors equally; MAPE on prices does not. Before adding complexity, does the research have a diagnostic showing *where* the current model's MAPE errors concentrate — at low-price regimes, high-price regimes, or horizon position? That diagnostic determines whether loss-function alignment or horizon weighting is the higher-leverage intervention.

---

## Turn 1 — Results

### Completed experiments

| Run | val_mse | 5d | 30d | 60d | 120d | DirAcc120 |
|-----|---------|-----|-----|-----|------|-----------|
| Pretrained (no FT) | n/a | 2.22% | 4.74% | 6.29% | **8.73%** | 49.9% |
| R1 baseline (uniform MSE) | 0.00623 | 2.36% | 5.34% | 8.20% | **12.63%** | 50.4% |
| R2 hdecay05 (decay=0.5) | 0.00707 | 2.41% | 5.73% | 8.15% | **11.99%** | 49.2% |

### Per-ticker 120d MAPE

| Ticker | Pretrained | R1 baseline | R2 hdecay |
|--------|-----------|-------------|-----------|
| NVDA | 7.00% | 11.67% | 10.24% |
| UNH | 13.23% | 23.39% | 21.97% |
| GS | 6.41% | 11.64% | 12.06% |
| CVX | 9.39% | 8.55% | 8.44% |
| KO | 6.63% | 5.84% | 5.66% |
| BA | 9.72% | 14.71% | 13.64% |

### Key finding
FINETUNING IS REGRESSING THE MODEL. Pretrained (8.731%) beats both finetuned checkpoints by 3-4pp at 120d.
- Decay=0.5 partially mitigates regression vs uniform MSE (-0.634pp vs R1) but still 3.27pp worse than pretrained
- Only CVX and KO show improvement from finetuning at 120d; all other tickers regress significantly
- UNH is the worst: pretrained=13.23% vs finetuned=23.39% (UNH had extraordinary events in 2024-2025)
- All previous exp_1..exp_11 results were contaminated by rolling_eval.py masks bug (all context zeroed → constant prediction)
- The old "baseline" of ~8.7% was actually the pretrained model correctly evaluated — finetuning never helped

### Rolling eval fix
rolling_eval.py had a window placement bug: end_idx started at len(series) so end_idx+120 > len(series) always → all 120d MAPEs were NaN. Fixed: anchor i=0 at len(series)-max_h.

---

