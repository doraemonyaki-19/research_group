# Final Report: TimesFM 1.0 vs. TimesFM 2.5 Baseline Comparison

**Date:** `YYYY-MM-DD`
**Author(s):** Researcher R1, Researcher R2

## 1. Executive Summary

This report provides the definitive answer to the project's central research question: "Is the TimesFM 2.5 model superior to the TimesFM 1.0 baseline for financial forecasting in our domain?"

*   **Primary Finding:** [1-sentence summary, e.g., "TimesFM 2.5 demonstrates a statistically significant and practically meaningful improvement over TimesFM 1.0, with the advantage being most pronounced in high-volatility market regimes."]
*   **Key Statistic:** [e.g., "Overall, TimesFM 2.5 achieved a reduction in median MAPE of X.XX percentage points (95% CI: [X.XX, Y.YY])."]
*   **Recommendation:** [e.g., "We recommend adopting TimesFM 2.5 as the new official baseline for all future research and production applications."]

---

## 2. Methodology

The comparison was conducted using the canonical `unified_evaluation_harness_v3.1.py`, ensuring a robust, reproducible, and methodologically sound analysis. The key features of this methodology are:

*   **Granular Comparison:** The analysis was performed on the exact same set of `(ticker, window)` pairs for both models, eliminating confounding variables.
*   **Stratification:** Performance was assessed across three groups: Overall, Low Volatility (bottom 25% of assets), and High Volatility (top 25% of assets). Volatility strata were defined by the baseline model's performance.
*   **Statistical Framework:** We employ the "Trinity of Evidence" as defined in the `analysis_interpretation_guide.md`:
    1.  **P-value (Mann-Whitney U):** To test for statistical significance.
    2.  **Effect Size (Rank-Biserial Correlation):** To quantify the magnitude of the difference.
    3.  **95% CI of Median Difference:** To assess the range of practical significance.

The specific model configurations and the methodology for deriving the optimal `ForecastConfig` for TimesFM 2.5 are detailed in `docs/methodology.md`.

---

## 3. Detailed Results

*Paste the complete, formatted output from the `run_final_analysis.sh` script here.*

```
[PASTE SCRIPT OUTPUT HERE]
```

---

## 4. Interpretation and Synthesis

This section synthesizes the raw statistical output into a cohesive narrative, following the framework in the interpretation guide.

### 4.1. Overall Performance

*   **Statistical Significance:** Was the overall p-value < 0.05?
*   **Practical Significance:** What does the 95% CI for the median difference tell us?
    *   *Position:* Does the interval cross zero?
    *   *Width:* How precise is our estimate of the improvement/regression?
    *   *Magnitude:* Is the median difference large enough to be financially meaningful? (e.g., does it exceed typical trading costs or offer a competitive edge?)
*   **Conclusion:** In aggregate, is TimesFM 2.5 better, worse, or comparable to TimesFM 1.0?

### 4.2. Performance in Low-Volatility Regime

*   **Statistical Significance:** Was the p-value < 0.05 in this stratum?
*   **Practical Significance:** What does the 95% CI tell us for these specific assets?
*   **Domain Implication:** For stable, predictable assets, what is the performance trade-off? This represents a lower-risk market regime. Is the new model a safe choice here?

### 4.3. Performance in High-Volatility Regime

*   **Statistical Significance:** Was the p-value < 0.05 in this stratum?
*   **Practical Significance:** What does the 95% CI tell us here? Is the effect stronger or weaker?
*   **Domain Implication:** For volatile, unpredictable assets, how does the model perform? This represents a higher-risk, higher-opportunity market regime. Does the model provide a clear advantage where it matters most?

### 4.4. Synthesized Conclusion

*   **Was the overall result driven by one stratum?** [e.g., "The overall improvement is almost entirely attributable to superior performance in high-volatility assets."]
*   **Are there any performance trade-offs?** [e.g., "We did not observe any statistically significant regression in the low-volatility stratum, suggesting the gains in high-volatility do not come at a cost to performance on stable assets."]
*   **Final Verdict:** [Synthesize the findings from all strata into a single, nuanced conclusion, addressing the original research question.]

---

## 5. Limitations and Next Steps

*   **Data Sparsity:** Were any strata too small for a conclusive analysis (indicated by very wide CIs)?
*   **Model Configuration:** This analysis compared specific, "optimal" configurations. Performance may differ with other settings.
*   **Next Steps:** [e.g., "Future work should explore the drivers of the high-volatility improvement," or "Deploy TimesFM 2.5 as the new baseline and proceed with hyperparameter tuning."]
