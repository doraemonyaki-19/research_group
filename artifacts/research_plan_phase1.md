# Research Plan: Systematic Evaluation of TimesFM ForecastConfig

## 1. Objective
To systematically evaluate the impact of key `ForecastConfig` parameters on TimesFM's zero-shot forecasting performance, as measured by Pinball Loss. The goal is to move beyond single-parameter tests and identify the most impactful parameters and their potential interactions, creating a robust, evidence-based guide for model adaptation.

## 2. Methodology
All experiments will be conducted using the official `unified_harness.py`, which provides statistically rigorous comparisons using Pinball Loss, aggregation over a large number of windows and tickers, Welch's t-test for significance, and effect size reporting.

## 3. Parameter Prioritization
Based on prior experimentation, supervisor feedback, and potential impact on time-series forecasting, we have identified the following parameters as high-priority for investigation:

*   **`context_len`**: The length of historical context provided to the model. This is a fundamental parameter in any time-series model.
*   **`lags_seq`**: The sequence of lagged values to be used as input features. This directly controls the information from the past that the model can use.
*   **Quantile Head Configuration**: The group of parameters (`use_continuous_quantile_head`, `normalize_inputs`, `fix_quantile_crossing`) that are hypothesized to work in concert.

## 4. Phased Research Approach

This research will be conducted in two phases to use compute resources efficiently.

### Phase 1: Parameter Screening (Turns 22-24)
The objective of this phase is to quickly identify which of the high-priority parameters have a statistically significant *main effect* on performance. We will test each parameter individually against the baseline.

**Experiment 1.1: `context_len` Screening**
*   **Hypothesis**: Longer context lengths will generally improve performance, but with diminishing returns.
*   **Configurations**:
    *   Baseline: `context_len = 512` (current default)
    *   Test 1: `context_len = 256` (shorter)
    *   Test 2: `context_len = 1024` (longer)
*   **Analysis**: Compare Pinball Loss of each test configuration to the baseline using the unified harness.

**Experiment 1.2: `lags_seq` Screening**
*   **Hypothesis**: The choice of lags is critical and defaults may be suboptimal.
*   **Configurations**:
    *   Baseline: Default `lags_seq` (requires inspection of harness/model)
    *   Test 1: A sequence of recent lags (e.g., `[1, 2, 3, 4, 5, 6, 7]`)
    *   Test 2: A sequence with exponential spacing to capture seasonality (e.g., `[1, 2, 4, 8, 16, 32]`)
*   **Analysis**: Compare Pinball Loss of each test configuration to the baseline.

**Experiment 1.3: Re-evaluation of "Fully Configured" Quantile Head**
*   **Hypothesis**: The combination of all three quantile-related flags (`use_continuous_quantile_head=True`, `normalize_inputs=True`, `fix_quantile_crossing=True`) provides a statistically significant improvement over the baseline.
*   **Configurations**:
    *   Baseline: All three flags `False`.
    *   Test: All three flags `True`.
*   **Analysis**: Run this one-on-one comparison using the unified harness. This is the deferred experiment from Turn 21.

### Phase 2: Interaction Analysis (Turns 25+)
Based on the results of Phase 1, any parameters that showed a significant main effect will be tested for interactions. This prevents a costly and inefficient full grid search.

**Example Experiment 2.1: `context_len` x `lags_seq` Interaction**
*   **Hypothesis**: The optimal `lags_seq` may depend on the `context_len`. For example, a longer context might benefit from more sparsely distributed lags.
*   **Configurations**: A 2x2 factorial design based on the best-performing values from Phase 1.
    *   Best `context_len` + Best `lags_seq`
    *   Best `context_len` + Baseline `lags_seq`
    *   Baseline `context_len` + Best `lags_seq`
    *   Baseline `context_len` + Baseline `lags_seq`
*   **Analysis**: Use a 2x2 ANOVA to determine if there is a significant interaction effect on Pinball Loss. The unified harness will need to be extended to support this analysis.

## 5. Next Steps
The immediate next step is to begin Phase 1. The first experiment to run is **Experiment 1.3**, the re-evaluation of the "Fully Configured" Quantile Head, as this is the most direct continuation of the group's previous work and will serve as the first official experiment on the new unified harness.
