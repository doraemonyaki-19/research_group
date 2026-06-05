## Experiment Summary: run_6_sector_focus_with_index

- **Hypothesis:** Re-introducing the S&P 500 index (`^GSPC`) to a focused, sector-matched training set would provide the optimal balance of specific and general signals, restoring long-horizon performance while preserving mid-horizon gains.

- **Hyperparameters:**
  - `lr`: 1e-4
  - `freeze-layers`: 17
  - `wd`: 0.01
  - `epochs`: 50
  - `tickers`: "^GSPC,AAPL,JNJ,JPM,XOM,PG,CAT"

- **Results:**
  - `val_loss`: 0.009110 (the lowest yet)
  - **Eval MAPE vs Baseline:**
    - 30d: 7.3% (vs 8.4%) -> Improvement
    - 60d: 6.1% (vs 6.5%) -> Improvement
    - 120d: 12.2% (vs 11.5% in this run's baseline, and 7.40% overall best) -> **Significant Regression**

- **Conclusion:** The hypothesis was strongly rejected. Adding the market index did not fix the long-horizon degradation seen in `run_5`. The validation loss was the best recorded so far, but this did not translate into better MAPE, reinforcing the known finding that validation loss is not a reliable indicator of forecast quality. The diversity of the original 10-ticker set appears to be more important for long-horizon forecasting than a more targeted, sector-matched approach.
