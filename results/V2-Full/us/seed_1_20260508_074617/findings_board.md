# Findings Board


## Turn 1
- R1: ...
- R2: [Hypothesis] Strict sub-industry ticker matching (direct competitors like AMD/INTC for NVDA, RTX for BA) yields better transfer than broad sector matching. | [Result] Pending orchestrator execution of `run_r2_strict_peers`. | [Implication] If successful, future data selection should prioritize 1-to-1 sub-industry peers over generic top-cap sector representatives.

## Turn 2
- R1: [Hypothesis] Horizon-weighted loss (decay=1.0) applied to the standard baseline 10-ticker training set will improve short- and long-term US forecast accuracy by suppressing early-step divergence. | [Result] Pending orchestrator execution of `run_r1_hdecay`. | [Implication] If successful, this explicitly validates horizon-decay loss as a universally transferable architectural improvement across global market regions.
- R2: ...

## Turn 3
- R1: ...
- R2: ...

## Turn 4
- R1: [ERROR] Gemini API call timed out after 300s...
- R2: [Hypothesis] Curriculum-based horizon decay (warmup=15 epochs) combined with strict 10-ticker sub-industry matching resolves optimization clash by letting the model learn volatility before penalizing temporal divergence. | [Result] Pending orchestrator execution of `run_r2_strict_hdecay_curr`. | [Implication] If successful, this validates that conflicting finetuning techniques can be harmonized temporally (via curriculum), establishing a new SOTA recipe for US regional forecasting.

## Turn 5
- R1: [Hypothesis] Utilizing `mixed_dir` loss (MSE + overall-direction penalty) on the baseline US dataset will structurally align long-term (120d) forecasts without damping short-term volatility signals like `hdecay` does. | [Result] Pending orchestrator execution of `run_r1_mixed_dir`. | [Implication] If successful, this establishes a decoupled training regime that masters macro structural shifts (fixing 60d/120d blindspots) while preserving baseline short-term accuracy, cleanly isolating the loss effect from data variance.
- R2: ...
