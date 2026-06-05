# Run 6: Increased Warmup Epochs

- **Hypothesis:** Increasing the number of warmup epochs from 5 to 10 will allow for a more gradual adaptation to the new data distribution, leading to a better final MAPE.
- **Hyperparameters:**
  - `lr`: 1e-4
  - `freeze-layers`: 17
  - `wd`: 0.01
  - `epochs`: 50
  - `warmup-epochs`: 10
  - `tickers`: "^GSPC, AAPL, JNJ, JPM, XOM, PG, CAT, NEE, AMT, WMT"
- **val_loss:** 0.007394
- **MAPE@120d:** 12.2% (+2.2pp vs. baseline)
- **DirAcc@120d:** (Not captured in this evaluation script)

| Horizon | Eval MAPE | Delta vs Baseline |
|---|---|---|
| 5d | 2.1% | +0.5pp |
| 14d | 4.7% | +0.6pp |
| 30d | 5.3% | -0.9pp |
| 60d | 6.4% | -0.5pp |
| 90d | 12.2% | +0.3pp |
| 120d | 12.2% | +2.2pp |

- **Conclusion:** Regression. Increasing the warmup epochs resulted in a significantly worse MAPE at the 120-day horizon. The hypothesis is rejected.
