# Analysis and Interpretation Guide for `unified_evaluation_harness_v3.1.py`

## 1. Introduction

This document provides a standardized framework for interpreting the output of the `unified_evaluation_harness_v3.1.py` script. Its purpose is to ensure that all researchers draw consistent, statistically robust, and methodologically sound conclusions from model comparison experiments. The harness provides a "trinity" of evidence for each comparison (overall and stratified): statistical significance (p-value), effect size (rank-biserial correlation), and practical significance (bootstrap confidence interval of the median difference). A holistic interpretation requires synthesizing all three.

## 2. The Trinity of Evidence: A Synthesis Framework

For each comparison group (Overall, Low Volatility, High Volatility), the harness outputs three key pieces of information. They should be interpreted together, not in isolation.

| Metric                        | Question Answered                                         | Interpretation Guidance                                                                                                                              |
| ----------------------------- | --------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------- |
| **P-value** (Mann-Whitney U)  | "Is the observed difference likely due to chance?"        | A p-value < 0.05 indicates a statistically significant difference, meaning the observed difference is unlikely to be random noise. It does **not** indicate the size or importance of the difference. |
| **Effect Size** (Rank-Biserial) | "How large is the difference between the groups?"         | This ranges from -1 to 1. Magnitudes (e.g., |r| > 0.1 is small, |r| > 0.3 is medium, |r| > 0.5 is large) provide context to the p-value. A significant p-value with a tiny effect size may be practically irrelevant. |
| **95% CI of Median Difference** | "What is the plausible range of the true difference?"     | This is the most important metric for practical significance. It estimates the range of the true performance difference between the models (Model B - Model A, where lower is better). |

---

## 3. How to Interpret the Bootstrap Confidence Interval (CI)

The CI of the median difference is the key to understanding the **practical importance** of the results. It represents the plausible range of the true difference in median MAPE between the challenger (Model B) and the baseline (Model A). Since lower MAPE is better, a negative difference indicates improvement.

### Interpreting CI Position:
- **Entirely Negative (e.g., [-0.5, -0.1]):** This is strong evidence of an improvement. We can be 95% confident that the challenger model has a lower median MAPE than the baseline, by an amount between 0.1 and 0.5 percentage points.
- **Entirely Positive (e.g., [0.2, 0.6]):** This is strong evidence of a regression. We can be 95% confident that the challenger model has a *higher* median MAPE than the baseline.
- **Crosses Zero (e.g., [-0.2, 0.3]):** There is no statistically significant difference in the medians. The true difference could plausibly be negative (an improvement), positive (a regression), or zero. This finding is consistent with a p-value > 0.05.

### Interpreting CI Width:
- **Narrow CI (e.g., [-0.15, -0.10]):** A precise estimate. This indicates high confidence in the magnitude of the difference. The result is likely stable and reliable.
- **Wide CI (e.g., [-1.5, 0.8]):** An imprecise estimate. This often occurs with small sample sizes or high variance in the data (common in high-volatility strata). While the median difference might seem large, the true value could be very different. Wide CIs that cross zero suggest the result is inconclusive.

---

## 4. Synthesizing Results Across Volatility Strata

A common scenario is observing conflicting results between the "Overall" comparison and the stratified comparisons. The following framework provides a structured approach to synthesis.

**Scenario 1: Consistent Results Across All Strata**
- **Finding:** Significant improvement Overall, in Low-Vol, and in High-Vol. All CIs are negative.
- **Interpretation:** The challenger model is robustly superior across all market conditions tested. This is the strongest possible outcome.

**Scenario 2: Overall Improvement Driven by a Single Stratum**
- **Finding:** Significant improvement Overall and in High-Vol, but the Low-Vol CI crosses zero.
- **Interpretation:** The challenger model's advantage is primarily in high-volatility assets. It is not demonstrably better or worse for low-volatility assets. **The overall result must be qualified with this context.** The correct conclusion is not "Model B is better," but "Model B is better, particularly for high-volatility assets, while being comparable for low-volatility ones."

**Scenario 3: Contradictory ("Crossover") Results**
- **Finding:** Significant improvement in High-Vol (CI is negative), but a significant *regression* in Low-Vol (CI is positive). The Overall CI might be narrow and cross zero.
- **Interpretation:** This is a critical finding of a performance trade-off. The model is specialized. It excels in one regime at the cost of performance in another. The "Overall" result may be misleadingly neutral. The primary conclusion is about this trade-off, not about general superiority.

**Scenario 4: No Significant Difference Anywhere**
- **Finding:** All CIs (Overall, Low-Vol, High-Vol) cross zero.
- **Interpretation:** There is no evidence to suggest one model is superior to the other in any of the tested conditions. They are practically equivalent.

**Decision Priority:** The stratified results are more informative than the overall result. Always use the stratified findings to add context and nuance to the overall conclusion. An overall claim of superiority is only fully justified if it holds across the relevant strata.

## 5. Answering Domain Questions

As noted by the Domain Supervisor, this granular, statistically robust framework allows us to move beyond simple "which model is better" questions. The harness can be used to test specific domain hypotheses, such as:
- **Micro-feature analysis:** Does a model's performance advantage correlate with specific features of the time series (e.g., stationarity, entropy, kurtosis)?
- **Temporal analysis:** Is the performance difference stable over time, or does it change during specific market events (e.g., recessions, high-interest-rate periods)?

By treating the `(ticker, window)` pairs as individual data points, we can enrich the `detailed_results.csv` with other metrics and use this harness as a foundation for deeper, more explanatory analysis.
