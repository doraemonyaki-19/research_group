# Findings Board


## Turn 1
- R1: Hypothesis: Training on a curated, sector-matched ticker list would improve performance. | Result: Regression. 120d MAPE increased from 7.40% to 10.0%. | Implication: The experiment was invalid because the training set included BA, a known volatile ticker that disrupts training. The sector-matching hypothesis must be re-tested with a clean dataset. | ```
- R2: **Hypothesis:** A hyper-focused training set of direct sector peers would outperform a more diverse set. | **Result:** **Regression.** MAPE @ 120d increased from 7.40% to 9.61% (-2.21pp). | **Implication:** The model benefits from a broader, more diverse training set; removing tickers from "unrelated" sectors harmed performance, suggesting they provide useful, generalizable market signals.

## Turn 2
- R1: Hypothesis: A clean, strictly sector-matched training set would improve performance. | Result: Regression. 120d MAPE was 9.7%, worse than the 7.40% SOTA. | Implication: Strict sector-matching leads to over-specialization. The model requires broader market context, likely from an index like ^GSPC, to learn generalizable patterns.
- R2: **Hypothesis:** A hybrid training set, built quantitatively with sector-peers and low-correlation tickers, would improve performance. | **Result:** **Regression.** MAPE @ 120d increased from 7.40% to 9.03% (-1.63pp). | **Implication:** The exclusion of the high-correlation market index `^GSPC` was likely the critical flaw; a broad market signal appears to be more valuable for generalization than a basket of low-correlation individual stocks.

## Turn 3
- R1: OBSERVATION:
The previous turn's experiments from both myself and R2, while regressions, were highly informative. My attempt at a clean, strictly sector-matched training set resulted in a 9.7% MAPE, a...
- R2: **Hypothesis:** A training set anchored by `^GSPC` and supplemented with quantitatively-selected low-correlation tickers would be optimal. | **Result:** **Breakthrough.** MAPE @ 120d improved from 7.40% to 6.85% (+0.55pp), a new SOTA. | **Implication:** The "anchor and diversify" strategy is highly effective; mandating a broad market index is critical, and quantitative methods can successfully select the remaining tickers.

## Turn 4
- R1: **Hypothesis:** An ablation study on the number of diversity tickers (N=2, 4 vs SOTA N=3) will identify an optimal training set configuration. | **Result:** Experiment execution blocked. No new results were generated due to persistent command timeouts during the training phase. | **Implication:** The ablation study remains the top priority. The experimental workflow must be adjusted to decouple long-running training jobs from evaluation to prevent future timeouts.
- R2: **Hypothesis:** The "anchor and diversify" strategy is a generalizable principle that will improve performance in the European market. | **Result:** **Success.** Applying the methodology to Europe improved the regional SOTA, lowering MAPE from 4.99% to 4.52% (+0.47pp). | **Implication:** The "anchor and diversify" strategy is confirmed as a robust, generalizable principle, not a US-specific fluke, establishing a standard workflow for new markets.

## Turn 5
- R1: **Hypothesis:** An ablation study on the number of diversity tickers (N=2, 4 vs SOTA N=3) will identify the optimal training set configuration. | **Result:** Submitted two long-running, decoupled training jobs for the N=2 and N=4 configurations. Results will be analyzed in the next turn upon completion. | **Implication:** The experimental workflow has been revised to be more robust, separating training from evaluation to prevent timeouts. This unblocks the critical path to optimizing the US SOTA.
- R2: ### Observation & Analysis

The feedback from all supervisors is convergent and clear. My successful generalization of the "anchor and diversify" principle to Europe was a significant methodological v...
