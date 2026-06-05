## Experiment Summary: run_7_relevant_diversity

### Hypothesis
Refining the training set's diversity to be more "relevant" will improve performance. This was tested by replacing tickers from unrelated sectors (NEE - Utilities, AMT - Real Estate) with additional large-cap tickers from sectors represented in the evaluation set (MSFT - Technology, BAC - Financials).

### Hyperparameters
- **Run Name:** `run_7_relevant_diversity`
- **Learning Rate:** 1e-4
- **Freeze Layers:** 17
- **Weight Decay:** 0.01
- **Epochs:** 50
- **Tickers:** `^GSPC, AAPL, MSFT, JNJ, JPM, BAC, XOM, PG, CAT, WMT`

### Results
- **Final Validation MSE:** 0.009963

**MAPE on Eval Tickers (US):**
- **5d:** 2.4% (+0.9pp vs baseline)
- **14d:** 4.6% (+0.4pp vs baseline)
- **30d:** 5.5% (-0.7pp vs baseline)
- **60d:** 6.4% (-0.5pp vs baseline)
- **120d:** 12.1% (+2.2pp vs baseline)

### Comparison to Current Best
- The current best 120d rolling MAPE is 7.40%.
- This run achieved a 120d MAPE of 12.1%, which is a **severe regression**.

### Conclusion
The hypothesis was strongly refuted. Replacing out-of-sector tickers with more "relevant" in-sector tickers significantly harmed the model's performance, especially at the 120-day horizon. This suggests that the broad, cross-sector diversity of the original baseline training set is a crucial feature, not a bug. It likely acts as a form of regularization, preventing the model from overfitting to the specific dynamics of the dominant sectors in the training data. Attempts to manually "improve" this diversity by narrowing its scope are counterproductive.
