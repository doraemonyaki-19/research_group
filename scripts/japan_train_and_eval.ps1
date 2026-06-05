$ErrorActionPreference = "Stop"
$PYTHON    = "C:\Users\ylchen\workspace\timesfm\.venv\Scripts\python.exe"
$TRAIN     = "C:\Users\ylchen\workspace\timesfm_finetuning\finetune_timesfm.py"
$EVAL      = "C:\Users\ylchen\workspace\timesfm_finetuning\scripts\rolling_eval.py"
$BASE      = "C:\Users\ylchen\workspace\timesfm_finetuning\model"
$SAVE      = "C:\Users\ylchen\workspace\research_group\artifacts\finetune_checkpoints\run_japan_20260531"
$TRAIN_DIR = "C:\Users\ylchen\workspace\timesfm_finetuning\finetune_japan\data\train"
$EVAL_DIR  = "C:\Users\ylchen\workspace\timesfm_finetuning\finetune_japan\data\eval"

Write-Host "===== JAPAN RETRAIN START ====="

& $PYTHON $TRAIN `
    --data-dir $TRAIN_DIR `
    --model-id $BASE `
    --epochs 50 `
    --batch-size 8 `
    --lr 1e-4 `
    --optimizer adamw `
    --weight-decay 0.01 `
    --freeze-layers 17 `
    --accumulation-steps 16 `
    --warmup-epochs 5 `
    --max-context 512 `
    --min-context 128 `
    --horizon 128 `
    --stride 64 `
    --no-epoch-ckpts `
    --seed 42 `
    --save-dir $SAVE

if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: training failed with exit code $LASTEXITCODE"
    exit $LASTEXITCODE
}

Write-Host "`n===== JAPAN EVAL START ====="

& $PYTHON $EVAL `
    --checkpoint "$SAVE\best" `
    --tickers "8035.T,6902.T,4661.T" `
    --horizons "5,14,30,60,90,120" `
    --n-windows 15 `
    --cache-dir $EVAL_DIR `
    --base-model $BASE

Write-Host "`n===== JAPAN TRAIN+EVAL COMPLETE ====="
