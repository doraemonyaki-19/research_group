# Analysis Addendum: Limitations and Future Work

This document addresses the key methodological and domain-specific questions raised by the supervisors in Turn 15. As directed by the Evaluator, these points are framed here as limitations of the current study and as avenues for future research, to be integrated into the final analysis report.

## 1. Limitations of the Current Experimental Design

The primary goal of the executed experiment was to establish a reproducible, controlled comparison between two inference configurations. To achieve this, certain methodological choices were made that introduce knowable limitations.

### 1.1. Assumption of "Sufficient" Domain Adaptation

*   **Supervisors' Question:** How do we know one epoch of finetuning is sufficient to capture S&P 500 dynamics, and how can this be empirically verified?
*   **Limitation:** The current study treats the one-epoch finetuning of `TimesFM 1.0` as a fixed, deterministic step to create a common, domain-aware baseline (`timesfm-1.0-sp500-adapted`). The experiment is designed to compare Arm A vs. Arm B *given this baseline*. It does **not** empirically measure the impact of the finetuning itself against the original, non-finetuned model. The assumption is that one epoch is sufficient to expose the model to the target data's statistical properties without inducing significant overfitting, but the absolute performance gain from this step is not quantified in this study.

### 1.2. Minimalist Approach to Model Adaptation

*   **Supervisors' Question:** How does this minimalist adaptation handle the complexities of financial data (e.g., non-stationarity)?
*   **Limitation:** The single-epoch adaptation is a broad, untargeted method. It does not explicitly account for specific financial data characteristics like volatility clustering, non-stationarity, or structural breaks. The model learns from these features implicitly, but the adaptation is not specifically designed to address them. The robustness of this minimalist approach is tested by the out-of-sample rolling evaluation, but it remains a limitation that more sophisticated, domain-aware finetuning strategies were not explored.

## 2. Proposed Future Work

The limitations above provide a clear roadmap for valuable follow-on research.

### 2.1. Quantifying the Value of Domain Adaptation

To empirically answer the question of adaptation efficacy, a new three-arm experiment should be conducted:

1.  **Arm 1 (Control):** The original `google/timesfm-1.0-200m` with no finetuning.
2.  **Arm 2 (Current Baseline):** The `timesfm-1.0-sp500-adapted` model (one epoch finetuning).
3.  **Arm 3 (Exploratory):** A model finetuned for multiple epochs (e.g., 3-5) with early stopping.

This would directly measure the performance impact (positive or negative) of the domain adaptation step and help identify the optimal finetuning duration.

### 2.2. Aligning Inference Configurations with Domain Challenges

*   **Supervisors' Question:** How do the 'Default' vs. 'Robust' configurations align with S&P 500 forecasting challenges?
*   **Domain Rationale & Future Work:**
    *   The **'Default' Config (context_len: 256)** represents a standard lookback window, suitable for capturing shorter-term trends and seasonality.
    *   The **'Robust' Config (context_len: 512)** hypothesizes that a longer context window is better suited for financial markets, which exhibit long memory and regime-switching behavior (e.g., shifts between high and low volatility). A longer context allows the model to potentially identify these slower-moving patterns.
    *   **Future experiments** should test this hypothesis explicitly. For example, one could analyze the performance of each configuration conditioned on market volatility (e.g., VIX levels). We could test if the 'Robust' config significantly outperforms the 'Default' config during periods of market stress or trend changes, which would validate its domain-specific utility.
