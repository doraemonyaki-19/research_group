## Experiment Summary: run_5_sector_focus

### Hypothesis
A more focused training set, with tickers closely matched to the evaluation set's sectors and excluding a broad market index, will reduce data dilution and improve forecast accuracy.

### Hyperparameters
- **Run Name:** `run_5_sector_focus`
- **Learning Rate:** 1e-4
- **Freeze Layers:** 17
- **Weight Decay:** 0.01
- **Epochs:** 50 (Early stopping triggered)
- **Tickers:** `AAPL, MSFT, JNJ, PFE, JPM, BAC, XOM, SLB, PG, CAT`

### Results
- **Final Validation MSE:** 0.011599

**MAPE on Eval Tickers (US):**
- **5d:** 2.2% (+0.7pp vs baseline)
- **14d:** 4.0% (-0.1pp vs baseline)
- **30d:** 5.2% (-1.1pp vs baseline)
- **60d:** 6.6% (-0.2pp vs baseline)
- **120d:** 9.8% (-0.1pp vs baseline)

**DirAcc on Eval Tickers (US):** (Not provided in the evaluate_regional.py output)

### Comparison to Current Best
- The current best 120d rolling MAPE is 7.40%.
- This run achieved a 120d MAPE of 9.8%, which is a **regression**.

### Conclusion
The hypothesis was not supported. While the focused, sector-matched training set led to MAPE improvements at mid-range horizons (30-90d), it caused a significant regression at the 5d horizon and did not improve upon the 120d benchmark. The removal of the market index and other diverse tickers may have weakened the model's ability to capture general, short-term market dynamics, even if it improved performance on sector-specific, mid-term trends. This suggests that some diversity in the training data is beneficial.
