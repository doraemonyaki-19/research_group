$ErrorActionPreference = "Stop"
$PYTHON = "C:\Users\ylchen\workspace\timesfm\.venv\Scripts\python.exe"
$EVAL_SCRIPT = "C:\Users\ylchen\workspace\timesfm_finetuning\scripts\rolling_eval.py"
$PRETRAINED = "C:\Users\ylchen\workspace\timesfm_finetuning\model"
$LOG_DIR = "C:\Users\ylchen\workspace\research_group\scripts\logs"
$ARTIFACTS = "C:\Users\ylchen\workspace\research_group\artifacts\finetune_checkpoints"

function Run-Eval {
    param($Label, $Checkpoint, $Tickers, $CacheDir, $ResultsFile)
    Write-Host "`n===== $Label =====" -ForegroundColor Cyan
    $args_list = @(
        $EVAL_SCRIPT,
        "--checkpoint", $Checkpoint,
        "--tickers", $Tickers,
        "--horizons", "5,14,30,60,90,120",
        "--n-windows", "15",
        "--cache-dir", $CacheDir,
        "--base-model", $PRETRAINED,
        "--results-file", $ResultsFile
    )
    & $PYTHON @args_list
    if ($LASTEXITCODE -ne 0) {
        Write-Host "ERROR: $Label failed with exit code $LASTEXITCODE" -ForegroundColor Red
    }
}

# ---- Japan ----
Run-Eval `
    -Label "Japan pretrained baseline" `
    -Checkpoint $PRETRAINED `
    -Tickers "8035.T,6902.T,4661.T" `
    -CacheDir "C:\Users\ylchen\workspace\timesfm_finetuning\finetune_japan\data\eval" `
    -ResultsFile "$ARTIFACTS\pretrained_baseline_japan\rolling_eval.json"

Run-Eval `
    -Label "Japan finetuned (run_glia_t2_r2a, hdecay=1.0)" `
    -Checkpoint "C:\Users\ylchen\workspace\timesfm_finetuning\finetune_japan\checkpoints\run_glia_t2_r2a\best" `
    -Tickers "8035.T,6902.T,4661.T" `
    -CacheDir "C:\Users\ylchen\workspace\timesfm_finetuning\finetune_japan\data\eval" `
    -ResultsFile "C:\Users\ylchen\workspace\timesfm_finetuning\finetune_japan\checkpoints\run_glia_t2_r2a\best\rolling_eval.json"

# ---- Europe ----
Run-Eval `
    -Label "Europe pretrained baseline" `
    -Checkpoint $PRETRAINED `
    -Tickers "UL,EADSF,VWAGY" `
    -CacheDir "C:\Users\ylchen\workspace\timesfm_finetuning\finetune_europe\data\eval" `
    -ResultsFile "$ARTIFACTS\pretrained_baseline_europe\rolling_eval.json"

Run-Eval `
    -Label "Europe finetuned (run_glia_v2_1a, 17 tickers)" `
    -Checkpoint "C:\Users\ylchen\workspace\timesfm_finetuning\finetune_europe\checkpoints\run_glia_v2_1a\best" `
    -Tickers "UL,EADSF,VWAGY" `
    -CacheDir "C:\Users\ylchen\workspace\timesfm_finetuning\finetune_europe\data\eval" `
    -ResultsFile "C:\Users\ylchen\workspace\timesfm_finetuning\finetune_europe\checkpoints\run_glia_v2_1a\best\rolling_eval.json"

# ---- China/HK ----
Run-Eval `
    -Label "China pretrained baseline" `
    -Checkpoint $PRETRAINED `
    -Tickers "0388.HK,2382.HK,1177.HK" `
    -CacheDir "C:\Users\ylchen\workspace\timesfm_finetuning\finetune_china\data\eval" `
    -ResultsFile "$ARTIFACTS\pretrained_baseline_china\rolling_eval.json"

Run-Eval `
    -Label "China finetuned (run_glia_2a, stride=32)" `
    -Checkpoint "C:\Users\ylchen\workspace\timesfm_finetuning\finetune_china\checkpoints\run_glia_2a\best" `
    -Tickers "0388.HK,2382.HK,1177.HK" `
    -CacheDir "C:\Users\ylchen\workspace\timesfm_finetuning\finetune_china\data\eval" `
    -ResultsFile "C:\Users\ylchen\workspace\timesfm_finetuning\finetune_china\checkpoints\run_glia_2a\best\rolling_eval.json"

Write-Host "`n===== ALL REGIONAL EVALS COMPLETE =====" -ForegroundColor Green
