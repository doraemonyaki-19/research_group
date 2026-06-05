$ErrorActionPreference = "Stop"
$PYTHON      = "C:\Users\ylchen\workspace\timesfm\.venv\Scripts\python.exe"
$TRAIN       = "C:\Users\ylchen\workspace\timesfm_finetuning\finetune_timesfm.py"
$EVAL        = "C:\Users\ylchen\workspace\timesfm_finetuning\scripts\rolling_eval.py"
$BASE        = "C:\Users\ylchen\workspace\timesfm_finetuning\model"
$SAVE        = "C:\Users\ylchen\workspace\research_group\artifacts\finetune_checkpoints\run_us_feb22data_20260531"
$CACHE_TRAIN = "C:\Users\ylchen\workspace\research_group\data\us_feb22"
$CACHE_EVAL  = "C:\Users\ylchen\workspace\research_group\data\us"

Write-Host "===== US RETRAIN (Feb 22 data, no early stopping) START ====="

& $PYTHON $TRAIN `
    --tickers "^GSPC,AAPL,JNJ,JPM,XOM,PG,CAT,NEE,AMT,WMT" `
    --cache-dir $CACHE_TRAIN `
    --model-id $BASE `
    --epochs 50 `
    --batch-size 8 `
    --lr 1e-4 `
    --optimizer adamw `
    --weight-decay 0.01 `
    --freeze-layers 17 `
    --accumulation-steps 16 `
    --warmup-epochs 3 `
    --max-context 512 `
    --min-context 128 `
    --horizon 128 `
    --no-epoch-ckpts `
    --seed 42 `
    --save-dir $SAVE

if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: training failed with exit code $LASTEXITCODE"
    exit $LASTEXITCODE
}

Write-Host "`n===== US EVAL (current data through May 2026) START ====="

& $PYTHON $EVAL `
    --checkpoint "$SAVE\best" `
    --tickers "NVDA,UNH,GS,CVX,KO,BA" `
    --horizons "5,14,30,60,90,120" `
    --n-windows 15 `
    --cache-dir $CACHE_EVAL `
    --base-model $BASE

Write-Host "`n===== US TRAIN+EVAL COMPLETE ====="
