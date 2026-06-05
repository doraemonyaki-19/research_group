# Findings Board


## Turn 1
- R1: Testing horizon-weighted loss (decay=1.0) on the US region using the established best hyperparameter recipe. | Result pending orchestrator execution (SyntaxError fix included in run plan). | Will analyze if the Japan-region findings for horizon-decay generalize across markets once evaluated.
- R2: [Tested whether applying exponential horizon decay (decay=1.0) to MSE loss improves US region MAPE across horizons] | [Result: Pending orchestrator execution; training and evaluation commands provided] | [Implication: If successful, confirms horizon-weighted loss as a robust cross-market optimization strategy]

## Turn 2
- R1: Testing `--linear-decay 0.5` on the US region to fix the 120d regression caused by exponential `horizon-decay=1.0`. | Result pending orchestrator execution (SyntaxError fix included). | If successful, this will validate that milder linear decay provides a better cross-horizon trade-off for the US market than strict exponential decay.
- R2: [Tested whether applying exponential horizon decay (decay=1.0) improves US region MAPE and whether it replicates the Japan 60d "dead zone"] | [Result: Improved 120d MAPE to 12.63% (+0.38pp vs baseline) and 60d MAPE to 7.68% (+0.13pp). No dead zone observed. However, it only beats vanilla finetuning by 0.02pp] | [Implication: Horizon decay is safe cross-market and Japan's dead zone was market-specific, but loss-weighting alone hits a ceiling in the US; we should pivot to cyclical penalties or data tuning]

## Turn 3
- R1: [ERROR] 429 RESOURCE_EXHAUSTED. {'error': {'code': 429, 'message': 'You exceeded your current quota, please check your plan and billing details. For more information on this error, head to: https://ai...
- R2: [ERROR] 429 RESOURCE_EXHAUSTED. {'error': {'code': 429, 'message': 'You exceeded your current quota, please check your plan and billing details. For more information on this error, head to: https://ai...

## Turn 4
- R1: [ERROR] 429 RESOURCE_EXHAUSTED. {'error': {'code': 429, 'message': 'You exceeded your current quota, please check your plan and billing details. For more information on this error, head to: https://ai...
- R2: [ERROR] 429 RESOURCE_EXHAUSTED. {'error': {'code': 429, 'message': 'You exceeded your current quota, please check your plan and billing details. For more information on this error, head to: https://ai...

## Turn 5
- R1: [ERROR] 429 RESOURCE_EXHAUSTED. {'error': {'code': 429, 'message': 'You exceeded your current quota, please check your plan and billing details. For more information on this error, head to: https://ai...
- R2: [ERROR] 429 RESOURCE_EXHAUSTED. {'error': {'code': 429, 'message': 'You exceeded your current quota, please check your plan and billing details. For more information on this error, head to: https://ai...
