# Run Summary: run_r2_t2_freeze_l18

## Hypothesis
Reducing the number of trainable layers from three to two (by setting `--freeze-layers 18`) will act as a regularizer, forcing the model to learn more generalizable long-term patterns and improving 120d MAPE.

## Hyperparameters
- **Run Name:** `run_r2_t2_freeze_l18`
- **Learning Rate:** `1e-4`
- **Freeze Layers:** `18`
- **Weight Decay:** `0.01`
- **Epochs:** `50` (stopped early at 45)
- **Tickers:** `^GSPC,AAPL,JNJ,JPM,XOM,PG,CAT,NEE,AMT,WMT`

## Results
- **Final Validation MSE:** `0.010300` (Training was stable)
- **Eval MAPE (US Held-out):**
  - **5d:** 3.6%
  - **14d:** 3.7%
  - **30d:** 5.3%
  - **60d:** 6.1%
  - **120d:** 11.9%
- **Eval DirAcc (US Held-out @ 120d):** Not explicitly calculated in this output.

## Comparison to Best (Run 4)
- **120d MAPE:** `11.9%` vs. `7.40%` (Best) -> **+4.5pp Regression**

## Conclusion
The hypothesis was incorrect. Reducing the number of trainable layers to two resulted in an even larger regression at the 120-day horizon than increasing them to four. The model's performance degraded significantly, confirming that layers 17-19 likely operate as a "tightly coupled minimum unit," as suggested in the task context. Finetuning only two layers provided insufficient capacity for the model to adapt to the new data, leading to poor long-range forecasting. The sweet spot for the number of unfrozen layers appears to be exactly three.
