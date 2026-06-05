# Run Summary: run_r2_t1_unfreeze_l16

## Hypothesis
Finetuning an additional layer (unfreezing layer 16, for 4 total finetuned layers) will allow the model to learn more complex patterns and improve MAPE compared to the baseline of 3 finetuned layers.

## Hyperparameters
- **Run Name:** `run_r2_t1_unfreeze_l16`
- **Learning Rate:** `1e-4`
- **Freeze Layers:** `16`
- **Weight Decay:** `0.01`
- **Epochs:** `50` (stopped early at 44)
- **Tickers:** `^GSPC,AAPL,JNJ,JPM,XOM,PG,CAT,NEE,AMT,WMT`

## Results
- **Final Validation MSE:** `0.006612` (Training was stable)
- **Eval MAPE (US Held-out):**
  - **5d:** 3.6%
  - **14d:** 3.9%
  - **30d:** 5.2%
  - **60d:** 6.8%
  - **120d:** 10.7%
- **Eval DirAcc (US Held-out @ 120d):** 0.49

## Comparison to Best (Run 4)
- **120d MAPE:** `10.7%` vs. `7.40%` (Best) -> **+3.3pp Regression**

## Conclusion
The hypothesis was incorrect. Unfreezing an additional layer resulted in a significant regression at the primary 120-day horizon. While there were minor improvements at mid-horizons (30d, 60d), the degradation at the longest horizon is critical. The increased number of trainable parameters appears to have led to overfitting or instability in long-range forecasts, even though the training process itself remained stable (low val_mse). This approach is not viable.
