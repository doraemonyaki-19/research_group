$PYTHON = "C:\Users\ylchen\workspace\timesfm\.venv\Scripts\python.exe"
$EVAL_SCRIPT = "C:\Users\ylchen\workspace\timesfm_finetuning\scripts\rolling_eval.py"
$PRETRAINED = "C:\Users\ylchen\workspace\timesfm_finetuning\model"
$CKPT = "C:\Users\ylchen\workspace\research_group\artifacts\finetune_checkpoints\run_us_restored_20260531\best"
$LOG = "C:\Users\ylchen\workspace\research_group\scripts\logs\us_eval_20260531.log"

Write-Host "[chainer] Waiting for US training (PID 7732) to finish..."
try { Wait-Process -Id 7732 -ErrorAction Stop } catch { Write-Host "[chainer] PID 7732 already gone, proceeding." }
Write-Host "[chainer] Training done. Starting rolling eval..."

& $PYTHON $EVAL_SCRIPT `
    --checkpoint $CKPT `
    --tickers "NVDA,UNH,GS,CVX,KO,BA" `
    --horizons "5,14,30,60,90,120" `
    --n-windows 15 `
    --cache-dir "C:\Users\ylchen\workspace\research_group\data\us" `
    --base-model $PRETRAINED

Write-Host "[chainer] Eval complete. Results saved to $CKPT\rolling_eval.json"
