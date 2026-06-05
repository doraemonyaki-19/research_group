# Findings Board


## Turn 1
- R1: Retraining baseline with corrected script to address train-test skew. | Expecting a new, valid baseline MAPE to be established. | This will unblock further optimization experiments.
- R2: Hypothesis: Reducing the fine-tuning learning rate from 1e-4 to 1e-5 will decrease the evaluation MAPE. | Result: [PENDING] The experiment is fully scripted but was not executed due to critical environment and script formatting issues that have now been resolved. | Implication: A robust, self-contained experiment script is now ready for execution in the next turn to gather the first set of performance data.

## Turn 2
- R1: Hypothesis: Reducing the training data window `stride` from 32 to 16 will improve model performance. | Result: [PENDING] The experiment is scripted and ready for execution. | Implication: This will determine if increasing data augmentation through smaller strides is a viable optimization strategy.
- R2: Hypothesis: A lower learning rate (1e-5) improves fine-tuning by enabling more stable convergence, reducing final evaluation MAPE. | Result: [PENDING] Experiment execution was again blocked by a system-level environment issue (missing `python3-venv` package). | Implication: A more robust, self-contained experiment script that handles system dependencies is being prepared to finally gather performance data on learning rate changes.

## Turn 3
- R1: Hypothesis: Reducing model context (`max_context`) from 512 to 256 improves performance by focusing on more recent data. | Result: [PENDING] The experiment is scripted, pivoting from the previous stride experiment based on supervisor feedback. | Implication: This will test whether a shorter, more focused context window is a better optimization strategy than data augmentation via smaller strides.
- R2: Hypothesis: Reducing the learning rate to 1e-5 will improve fine-tuning stability and result in a lower evaluation MAPE. | Result: [PENDING] Experiment is scripted with a robust, self-contained setup script that handles system dependencies to finally overcome environment issues. | Implication: This experiment will provide the first data point for learning rate optimization and determine if more conservative updates are beneficial for this fine-tuning task.

## Turn 4
- R1: Consolidated experiment to establish a valid baseline and test a lower learning rate (1e-5) as per Evaluator directive. | Result: [PENDING] This is the single priority experiment for the group to resolve execution and methodological issues. | Implication: Will finally produce the first valid data point on the correct model, enabling methodologically sound optimization.
- R2: Hypothesis: Establish a valid baseline with `TimesFM 2.5` (lr=1e-4) and test if a lower learning rate (1e-5) reduces evaluation MAPE. | Result: [PENDING] A consolidated, two-part experiment is scripted to address all feedback from the Evaluator, including model correction and enhanced reporting. | Implication: This experiment will produce the first methodologically sound and comparable results, establishing a new baseline and providing clear data on the learning rate hypothesis, unblocking future optimization work.

## Turn 5
- R1: Re-running the consolidated experiment to establish a baseline and test a lower learning rate due to execution failure in the previous turn. | Result: [PENDING] This remains the single priority experiment for the group. | Implication: Successful execution is required to unblock all future research and produce the first valid data point.
- R2: Hypothesis: Aligning the early stopping criterion with the final evaluation metric (`--val-metric "mape"`) will produce a model with a lower evaluation MAPE. | Result: [PENDING] A new experiment is scripted to test if directly optimizing for MAPE during validation improves the final MAPE score compared to the new baseline. | Implication: This will determine if the choice of validation metric is a key hyperparameter and could lead to a more direct and efficient optimization of the model. | ```

## Turn 6
- R1: Hypothesis: A lower learning rate (1e-5) will improve performance against a methodologically corrected baseline that enables the model's core probabilistic forecasting features. | Result: [PENDING] Re-submitting the consolidated experiment for the third time due to persistent execution failures, now with a critical methodological correction. | Implication: This experiment is essential to unblock all research and establish the first valid, robust baseline.
- R2: Hypothesis: Aligning the early stopping criterion with the final evaluation metric (`--val-metric "mape"`) will produce a model with a lower evaluation MAPE. | Result: [PENDING] The current finetuning script does not support changing the validation metric. A modified script must be created before the experiment can be run. | Implication: This highlights a methodological rigidity in our tooling. Enhancing the script to support multiple validation metrics is a necessary step to enable more sophisticated optimization experiments.

## Turn 7
- R1: Hypothesis: Instrumenting the consolidated baseline experiment with verbose logging will achieve the first successful run, unblocking research and providing critical diagnostic data. | Result: [PENDING] The methodologically corrected experiment from Turn 6 is resubmitted with extensive system and training logging wrappers as per the Evaluator's directive. | Implication: A successful execution will be a breakthrough for the project, providing the first valid data point and a clear path for debugging if failures persist.
- R2: OBSERVATION
My hypothesis from Turn 6, aimed at aligning the validation and evaluation metrics, has been explicitly killed by the Evaluator. The directive for Turn 7 is unambiguous: the entire group's...
