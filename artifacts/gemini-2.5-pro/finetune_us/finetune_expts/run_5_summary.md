# Run 5: Lower Learning Rate

- **Hypothesis:** A slightly lower learning rate (8e-5 vs. 1e-4) will lead to more stable training and a better final MAPE.
- **Hyperparameters:**
  - `lr`: 8e-5
  - `freeze-layers`: 17
  - `wd`: 0.01
  - `epochs`: 50
  - `tickers`: "^GSPC, AAPL, JNJ, JPM, XOM, PG, CAT, NEE, AMT, WMT"
- **val_loss:** 0.009802
- **MAPE@120d:** 10.8% (+0.9pp vs. baseline)
- **DirAcc@120d:** (Not captured in this evaluation script)

| Horizon | Eval MAPE | Delta vs Baseline |
|---|---|---|
| 5d | 2.0% | +0.5pp |
| 14d | 4.2% | +0.0pp |
| 30d | 5.3% | -0.9pp |
| 60d | 6.2% | -0.7pp |
| 90d | 11.8% | -0.2pp |
| 120d | 10.8% | +0.9pp |

- **Conclusion:** Regression. The lower learning rate resulted in a worse overall MAPE at the 120-day horizon. While there were slight improvements at intermediate horizons, the longest-term forecast, which is the primary metric, suffered. The hypothesis is rejected.
