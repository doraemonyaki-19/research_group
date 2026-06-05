# Run Summary: run_r2_t3_wd_0.02

## Hypothesis
Increasing weight decay from 0.01 to 0.02 will act as a stronger regularizer, preventing overfitting to short-term noise and improving long-range (120d) MAPE.

## Hyperparameters
- **Run Name:** `run_r2_t3_wd_0.02`
- **Learning Rate:** `1e-4`
- **Freeze Layers:** `17`
- **Weight Decay:** `0.02`
- **Epochs:** `50`
- **Tickers:** `^GSPC,AAPL,JNJ,JPM,XOM,PG,CAT,NEE,AMT,WMT`

## Results
- **Final Validation MSE:** `0.007019` (Training was stable)
- **Eval MAPE (US Held-out):**
  - **5d:** 3.5%
  - **14d:** 3.8%
  - **30d:** 4.9%
  - **60d:** 6.3%
  - **120d:** 13.9%

## Comparison to Best (Run 4)
- **120d MAPE:** `13.9%` vs. `7.40%` (Best) -> **+6.5pp Regression**

## Conclusion
The hypothesis was incorrect. Doubling the weight decay resulted in a catastrophic regression at the 120-day horizon, far worse than any previous experiment. The increased regularization was clearly too strong, preventing the model from learning the necessary long-term patterns. While performance at shorter horizons (30d, 60d) was slightly better than baseline, the severe degradation at 120d makes this a failed experiment. This indicates the original weight decay of 0.01 is likely near the optimal value, and stronger regularization is not the path to improvement.
