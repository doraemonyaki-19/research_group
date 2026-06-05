# Run 7: Increased Tickers

- **Hypothesis:** Increasing the number of training tickers from 10 to 15 will improve the model's ability to generalize and result in a lower MAPE.
- **Hyperparameters:**
  - `lr`: 1e-4
  - `freeze-layers`: 17
  - `wd`: 0.01
  - `epochs`: 50
  - `tickers`: "^GSPC, AAPL, JNJ, JPM, XOM, PG, CAT, NEE, AMT, WMT, HD, VZ, C, PFE, MRK"
- **val_loss:** 0.008607
- **MAPE@120d:** 10.3% (+0.4pp vs. baseline)
- **DirAcc@120d:** (Not captured in this evaluation script)

| Horizon | Eval MAPE | Delta vs Baseline |
|---|---|---|
| 5d | 2.0% | +0.4pp |
| 14d | 4.6% | +0.4pp |
| 30d | 5.0% | -1.2pp |
| 60d | 6.4% | -0.5pp |
| 90d | 11.5% | -0.4pp |
| 120d | 10.3% | +0.4pp |

- **Conclusion:** Regression. Increasing the number of tickers resulted in a slightly worse MAPE at the 120-day horizon. The hypothesis is rejected.
