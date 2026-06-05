# Research Plan: Phase 2 - Systematic Evaluation via Experimental Design

## 1. Objective
To build upon the initial screening phase with a more efficient and powerful methodology for identifying optimal `ForecastConfig` parameters and their interactions. This plan directly incorporates supervisor feedback regarding Design of Experiments (DoE), effect size, and parameter prioritization to accelerate discovery.

## 2. Core Methodology: Design of Experiments (DoE)
Instead of one-factor-at-a-time (OFAT) sweeps, we will adopt a factorial design approach. This is vastly more efficient for identifying not only the main effects of parameters but also their critical **interaction effects**—cases where the impact of one parameter depends on the level of another.

**Primary Tool**: The group's `systematic_harness.py` (or its successor) will be used for execution. The analysis will be extended from simple t-tests to ANOVA to decompose variance into main effects and interaction effects.

## 3. Parameter Selection & Prioritization
Addressing supervisor feedback, we will prioritize parameters based on a clear framework:
*   **Known Levers**: Parameters with a strong theoretical basis for impacting performance (e.g., `context_len`, `lags_seq`).
*   **Architectural Switches**: Parameters that fundamentally change a component of the model (e.g., `use_continuous_quantile_head`).
*   **Analogs from Signal Processing**: Parameters that control how the model processes the input signal (e.g., `normalize_inputs`, potentially future features like detrending).

The top priorities remain: `context_len`, `lags_seq`, and the "Quantile Head" configuration block.

## 4. Proposed Experimental Design: A 2³ Factorial Experiment

Once the initial screening from Phase 1 is complete, we will conduct a 2-level, 3-factor (2³) factorial experiment. This design will test 3 parameters at 2 levels each, requiring 8 total experimental runs. It will allow us to estimate the main effects of all 3 parameters, plus all their two-way and three-way interactions.

**Factors and Levels (Example):**
*   **Factor A: `context_len`**
    *   Level -: 512 (Baseline)
    *   Level +: 1024 (Longer)
*   **Factor B: `lags_seq`**
    *   Level -: Default lags (e.g., `[1...7]`)
    *   Level +: Exponentially spaced lags (e.g., `[1, 2, 4, 8, 16, 32]`)
*   **Factor C: Quantile Head**
    *   Level -: Disabled (Baseline config)
    *   Level +: Fully Enabled (`use_continuous_quantile_head`, `normalize_inputs`, `fix_quantile_crossing` all True)

**Analysis Plan:**
1.  **Run all 8 combinations** using the systematic harness.
2.  **Collect Pinball Loss** for each run.
3.  **Perform a 3-way ANOVA** on the results.
4.  **Analyze the output**:
    *   **Main Effects**: Is `context_len` significant overall? Is `lags_seq`? Is Quantile Head?
    *   **Interaction Effects (e.g., A:B)**: Does the effect of `context_len` *depend on* which `lags_seq` is used? This is the key question that OFAT misses.
5.  **Report Effect Sizes**: For all significant effects (main or interaction), report an effect size (e.g., eta-squared from the ANOVA table) to quantify its practical importance.

## 5. Pre-requisite
The immediate blocker is locating or recreating the `systematic_harness.py` script that can run N-way comparisons of specified `ForecastConfig` parameters. The next turn must be dedicated to resolving this tooling issue so that this more advanced research plan can be executed. Once the tool is available, the first experiment remains the simple A/B test of the "Fully Configured" Quantile Head vs. Baseline, which serves as a pilot for the full factorial experiment.
