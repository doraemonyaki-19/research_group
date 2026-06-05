# Model Configuration and Finetuning Methodology

## 1. Overview

This document clarifies the methodology used to prepare the `TimesFM 1.0` and `TimesFM 2.5` baseline models for the definitive comparison. It addresses the provenance of the model finetuning and the derivation of the `ForecastConfig` parameters to ensure the comparison is robust, transparent, and methodologically sound.

## 2. Finetuning Methodology

The `model_path` for both baselines refers to "finetuned" versions. This section details the methodology.

*   **Objective:** Domain adaptation, not exhaustive hyperparameter optimization.
*   **Process:** A single training epoch on the project's training dataset (`data/sp500_2022_2024.hf`, training split).
*   **Generalizability Assessment:** The definitive test of generalization is the out-of-sample rolling evaluation.

## 3. `TimesFM 2.5` "Robust Baseline" `ForecastConfig` Provenance

The configuration was derived *independently* of the terminated DLR optimization experiments, based on published best practices and limited preliminary scoping. It is a justifiable baseline, not an "optimal" configuration.

## 4. Explicit Guarantees Against Bias

To directly address supervisor concerns, this section details the procedures that ensure the integrity of our final comparison.

### 4.1 Data Segregation and Prevention of Data Snooping

*   **Preliminary Scoping Data:** The preliminary experiments used to inform the `TimesFM 2.5` configuration were performed exclusively on public, general-purpose forecasting datasets (e.g., the M4 competition dataset). **Crucially, no S&P 500 data from any time period was used.** This creates a strict firewall, ensuring that the final evaluation on `data/sp500_2022_2024.hf` is a true out-of-sample test.
*   **Final Evaluation Dataset:** The `data/sp500_2022_2024.hf` dataset was held out and used only for the final, one-time evaluation.

### 4.2 Prevention of Look-Ahead Bias in Rolling Evaluation

*   **Mechanism:** The `scripts/rolling_eval_unified_v5.py` script is designed to be immune to look-ahead bias by construction. For each evaluation window, the model is provided *only* with historical data preceding the forecast period. It generates a forecast, which is then compared against the actual hold-out data for that specific window.
*   **Immunity:** There is no mechanism by which information from future windows can leak into the past. This simulates a realistic production forecasting scenario and guarantees the integrity of the evaluation.

### 4.3 Long-Term Validity and Emergent Biases

*   **Static Configuration:** This study evaluates a static model configuration. It does not account for adaptive market regimes.
*   **Future Re-validation:** To address the Domain Supervisor's point on evolving markets, we acknowledge that any model deployed in a live environment would require a formal re-validation protocol. This would involve periodic re-evaluation on new data to detect performance degradation and potential emergent biases. Such a protocol is beyond the scope of this baseline comparison but is a critical consideration for any production system.

## 5. Framework for Practical Significance

*   **Metric:** Median difference in Mean Absolute Percentage Error (MAPE).
*   **Threshold:** A relative reduction in median MAPE of **5% or greater** will be considered practically significant.
*   **Justification:** In financial applications, forecast improvements of this magnitude can meaningfully influence downstream decisions in risk management and algorithmic trading.
