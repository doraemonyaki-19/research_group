# Post-Execution Audit Plan

This document outlines the procedure for verifying the integrity of the experiment executed by `run_corrected_experiment.sh`. The goal is to ensure that the comparison between Arm A (Default Config) and Arm B (Robust Config) is a scientifically valid controlled experiment before proceeding with statistical analysis.

This plan directly addresses questions raised by the supervisors in Turn 17.

## 1. Audit Objectives

1.  **Confirm Identity of the Base Model:** Verify that both Arm A and Arm B used the exact same finetuned model (`models/timesfm-1.0-sp500-adapted`) as their input.
2.  **Confirm Identity of Core Experimental Parameters:** Verify that other critical parameters, such as the evaluation dataset, were identical across both arms.
3.  **Document the Rationale for Verification:** Explicitly state the statistical implications of any potential discrepancies, as requested by the supervisors.

## 2. Rationale (Responses to Supervisor Questions)

### 2.1. Implications of Non-Identical Base Models (Stats Supervisor Q1)

If the audit were to reveal that the base models used in Arm A and Arm B were not identical, it would **fundamentally invalidate the entire experiment**.

-   **Compromise to Inference:** The core research question is to isolate the effect of the *inference configuration* ('Default' vs. 'Robust'). If the base models differ, we have introduced a massive **confounding variable**. Any observed difference in performance could be attributed to the different models rather than the different configurations.
-   **Biases Introduced:** This would introduce a critical **confounding bias**. We would be unable to disentangle the effect of the treatment (the robust config) from the effect of the uncontrolled variable (the model version). The experiment would no longer be a controlled comparison, and any statistical results (like a t-test) would be meaningless.

### 2.2. Other Critical Parameters for Verification (Stats Supervisor Q2)

Beyond the `model_path`, the following parameters must be confirmed as identical across both arms to ensure a controlled comparison:

-   **`dataset_path`**: Must be identical to ensure both configurations were tested on the same data.
-   **Environment and Dependencies**: While harder to verify post-hoc, the use of a single script (`run_corrected_experiment.sh`) provides confidence in a consistent environment. The most critical aspect is that the model and data were the same.
-   **Random Seeds**: The finetuning script (`scripts/finetune_timesfm_v1.py`) explicitly used `seed 42` for deterministic model generation. The evaluation script (`scripts/rolling_eval_unified.py`) appears to be deterministic by nature and does not expose a seed argument, which is acceptable for an evaluation-only script.

## 3. Audit Procedure

1.  Locate the output directories for Arm A and Arm B within the `experiments/` directory.
2.  Inspect the `args.json` file within each directory. This file should contain the arguments passed to the `rolling_eval_unified.py` script.
3.  Compare the value of the `model_path` key in both files. They must be identical and point to `models/timesfm-1.0-sp500-adapted`.
4.  Compare the value of the `dataset_path` key in both files. They must be identical and point to `data/sp500_2022_2024.hf`.
5.  Report the findings.

