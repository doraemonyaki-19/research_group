# Model Bill of Materials (BOM) for Final Comparison

## 1. Executive Summary

This document provides a definitive specification for the models and configurations to be used in the final baseline comparison. It corrects previous erroneous assumptions and directly addresses supervisor feedback from Turn 14 to ensure the forthcoming experiment is transparent, reproducible, and methodologically sound.

The central correction is the reframing of the experiment: a true `TimesFM 2.5` model with a distinct architecture is not publicly available. Therefore, instead of comparing two different models, this experiment will perform a more controlled and scientifically valid comparison of two different **inference configurations** applied to a single, domain-adapted base model.

## 2. Common Base Model: `TimesFM 1.0 (SP500 Adapted)`

To ensure a fair comparison, both experimental arms will use the exact same underlying model, which has been domain-adapted to the project's dataset.

*   **Source Foundation Model:** `google/timesfm-1.0-200m`. This is the correct 200 million parameter public checkpoint. This resolves the discrepancy noted by the Methods Supervisor regarding the 800M parameter version.
*   **Domain Adaptation Process (Finetuning):**
    *   **Objective:** To adapt the general-purpose foundation model to the specific statistical properties of the `sp500_2022_2024.hf` dataset. This is a standard practice for domain-specific application of foundation models.
    *   **Method:** A single training epoch on the `train` split of the dataset.
    *   **Justification for Single Epoch:** Per the Stats and Methods Supervisors' questions, the goal is **domain adaptation, not exhaustive optimization.** A single pass is sufficient to expose the model to the target data distribution. This avoids the risk of gross overfitting that multiple epochs would introduce, the extent of which will be rigorously tested by the out-of-sample rolling evaluation. It establishes a robust, adapted baseline, not a "perfectly optimized" one.
*   **Final Artifact:** The script will generate a single model artifact named `models/timesfm-1.0-sp500-adapted`.

## 3. Experimental Arms

The comparison will be between two configurations applied to the *same* adapted base model.

### Arm A: Baseline Configuration (`Default Config`)

This represents the standard, out-of-the-box usage of the model.

*   **Model:** `models/timesfm-1.0-sp500-adapted`
*   **Inference Parameters (`ForecastConfig`):**
    *   `context_len`: 256
    *   `patch_len`: 16
    *   `batch_size`: 64

### Arm B: Challenger Configuration (`Robust Config`)

This tests the hypothesis that a configuration with a longer lookback context improves performance. It is explicitly NOT `TimesFM 2.5`.

*   **Model:** `models/timesfm-1.0-sp500-adapted`
*   **Inference Parameters (`ForecastConfig`):**
    *   `context_len`: 512
    *   `patch_len`: 32
    *   `batch_size`: 32 (adjusted for memory)

## 4. Stability and Determinism

In response to the Domain Supervisor's query, the finetuning script will set a fixed random seed to ensure that the generation of `models/timesfm-1.0-sp500-adapted` is deterministic. This ensures that any observed performance difference between Arm A and Arm B is attributable *only* to the difference in inference configurations, not to random variations in model weights.
