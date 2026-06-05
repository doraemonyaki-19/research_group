## Experiment Summary: run_6_unfreeze_layer

### Hypothesis
Unfreezing an additional transformer layer (from 17 to 16) will provide the model with more capacity to learn the complex interactions between broad market signals (^GSPC) and specific sector trends, leading to improved long-term forecast accuracy.

### Hyperparameters
- **Run Name:** `run_6_unfreeze_layer`
- **Learning Rate:** 1e-4
- **Freeze Layers:** 16
- **Weight Decay:** 0.01
- **Epochs:** 50
- **Tickers:** `^GSPC, AAPL, JNJ, JPM, XOM, PG, CAT, NEE, AMT, WMT`

### Results
- **Final Validation MSE:** 0.006537

**MAPE on Eval Tickers (US):**
- **5d:** 2.1% (+0.6pp vs baseline)
- **14d:** 4.7% (+0.5pp vs baseline)
- **30d:** 5.4% (-0.8pp vs baseline)
- **60d:** 6.4% (-0.5pp vs baseline)
- **120d:** 12.6% (+2.7pp vs baseline)

**DirAcc on Eval Tickers (US):** (Not provided in the evaluate_regional.py output)

### Comparison to Current Best
- The current best 120d rolling MAPE is 7.40%.
- This run achieved a 120d MAPE of 12.6%, which is a significant **regression**.

### Conclusion
The hypothesis was strongly refuted. While unfreezing an additional layer resulted in a much lower validation MSE, suggesting a better fit to the training data, it led to poor generalization and significant overfitting on the held-out evaluation set. The MAPE at the key 120d horizon was substantially worse than both the baseline and the current best. This experiment validates that `freeze-layers 17` is a critical component of the working recipe, providing necessary regularization. Increasing model capacity via unfreezing more layers is not a viable path for improvement.
