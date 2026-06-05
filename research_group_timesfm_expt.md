# TimesFM Finetuning — Experiment Context

This file is injected into researcher and supervisor prompts as `{task_context}`.
It is the authoritative source of file paths, CLI templates, known dead ends, and
current best results. Keep it up to date as experiments progress.

---

## Mission

Finetune TimesFM 2.5 (200M params, PyTorch decoder-only model) on US equity price
series. Goal: minimize MAPE (Mean Absolute Percentage Error) on held-out eval tickers
at multiple forecast horizons. The official primary metric is **120d MAPE** from a
15-window rolling evaluation.

---

## Environment

**Python:** `C:\Users\ylchen\workspace\timesfm\.venv\Scripts\python.exe`
Always use this exact path. Never use bare `python` — the system Python has no packages.

**Working directory (agent cwd):** `C:\Users\ylchen\workspace\research_group\artifacts`

**UTF-8 encoding fix (required for all scripts you write):**
Add these two lines at the top of every Python script before any other I/O:
```python
import sys
sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')
```

**Argparse tip:** When passing arguments with spaces (e.g. `--tickers "AAPL,MSFT"`),
always wrap in quotes inside the PowerShell command string to prevent shell tokenization bugs.

---

## Key Paths

| Item | Path |
|------|------|
| Training script | `C:\Users\ylchen\workspace\timesfm_finetuning\finetune_timesfm.py` |
| Eval script | `C:\Users\ylchen\workspace\timesfm_finetuning\scripts\rolling_eval.py` |
| Pre-trained TimesFM 2.5 checkpoint | `C:\Users\ylchen\workspace\timesfm_finetuning\model` |
| US ticker cache — current data | `C:\Users\ylchen\workspace\research_group\data\us\` |
| US ticker cache — Feb 22 2026 data | `C:\Users\ylchen\workspace\research_group\data\us_feb22\` |
| Japan train data | `C:\Users\ylchen\workspace\timesfm_finetuning\finetune_japan\data\train\` |
| Japan eval data | `C:\Users\ylchen\workspace\timesfm_finetuning\finetune_japan\data\eval\` |
| Europe train data | `C:\Users\ylchen\workspace\timesfm_finetuning\finetune_europe\data\train_v2\` |
| Europe eval data | `C:\Users\ylchen\workspace\timesfm_finetuning\finetune_europe\data\eval\` |
| China train data | `C:\Users\ylchen\workspace\timesfm_finetuning\finetune_china\data\train\` |
| China eval data | `C:\Users\ylchen\workspace\timesfm_finetuning\finetune_china\data\eval\` |
| Experiment checkpoints | `C:\Users\ylchen\workspace\research_group\artifacts\finetune_checkpoints\` |
| Experiment metrics log | `C:\Users\ylchen\workspace\research_group\artifacts\experiment_metrics.csv` |

**Always save new checkpoints under:**
`C:\Users\ylchen\workspace\research_group\artifacts\finetune_checkpoints\<run_name>\`

**Always use `--no-epoch-ckpts`** to avoid saving 880 MB per epoch.

---

## Region: us

- **Eval tickers (held-out):** NVDA, UNH, GS, CVX, KO, BA
- **Diagnostic tickers (training-set held-out windows):** AAPL, MSFT, AMZN, GOOGL, META, JPM
- **Canonical training tickers:** `^GSPC,AAPL,JNJ,JPM,XOM,PG,CAT,NEE,AMT,WMT`
- **Training cache:** `data/us_feb22/` (data through 2026-02-20; matches the original Run 4 dataset)
- **Eval cache:** `data/us/` (current data through 2026-06-01; keeps results comparable across runs)

## Region: japan

- **Eval tickers (held-out):** 8035.T, 6902.T, 4661.T
- **Training data:** `finetune_japan/data/train/` (10 tickers incl. IDX_N225; use `--data-dir`)
- **Stride:** 64

## Region: europe

- **Eval tickers (held-out):** UL, EADSF, VWAGY
- **Training data:** `finetune_europe/data/train_v2/` (17 tickers; use `--data-dir`)
- **Stride:** 32

## Region: china

- **Eval tickers (held-out):** 0388.HK, 2382.HK, 1177.HK
- **Training data:** `finetune_china/data/train/` (all 10 tickers incl. short-history; use `--data-dir`)
- **Stride:** 32 — critical: stride=128 gives only ~230 windows (too few); stride=32 → ~900 windows

---

## Confirmed Baselines — All Regions (fixed rolling_eval.py, 15 windows, 2026-06-01)

### US

| Checkpoint | 120d MAPE | Notes |
|------------|-----------|-------|
| Pretrained (no finetuning) | 8.731% | True zero-shot baseline |
| **run_us_feb22data_20260531** | **8.468%** | **Current best — beats pretrained by 0.263pp** |
| run_us_restored_20260531 | 8.859% | Trained on current data (May 2026); NVDA regressed |

**Per-ticker 120d MAPE (run_us_feb22data_20260531):**

| Ticker | Pretrained | Finetuned | Delta |
|--------|-----------|-----------|-------|
| NVDA | 7.00% | 6.70% | -0.30pp |
| UNH | 13.23% | 16.65% | +3.42pp (regression) |
| GS | 6.41% | 6.20% | -0.21pp |
| CVX | 9.39% | 7.23% | -2.16pp |
| KO | 6.63% | 5.15% | -1.48pp |
| BA | 9.72% | 8.89% | -0.83pp |

5/6 tickers improve. UNH is the persistent problem ticker (CEO assassination + regulatory
shock in 2024–2025). CVX and KO show the largest gains. Training dynamics: best epoch 4,
val_loss 0.012236.

**Note on Feb 22 backup (8.312%):** The prior best checkpoint was deleted. The current
run_us_feb22data_20260531 (8.468%) is the new reference. The 0.16pp gap vs Feb 22 is
attributed to seed sensitivity on UNH; training dynamics are nearly identical (epoch 4 best,
similar val_loss 0.012236 vs 0.012764).

### Japan

| Checkpoint | 120d MAPE | Notes |
|------------|-----------|-------|
| Pretrained (no finetuning) | 12.485% | Fixed eval; prior buggy eval showed 17.94% |
| **run_japan_20260531** | **11.139%** | **Current best — beats pretrained by 1.346pp** |

**Per-ticker 120d MAPE (run_japan_20260531):**

| Ticker | Pretrained | Finetuned | Delta |
|--------|-----------|-----------|-------|
| 8035.T (Tokyo Electron) | 21.306% | 19.001% | -2.305pp |
| 6902.T (Denso) | 5.850% | 4.756% | -1.094pp |
| 4661.T (Oriental Land) | 10.300% | 9.660% | -0.640pp |

All 3 eval tickers improve. Standard MSE loss with stride=64 and warmup=5 works cleanly.
The prior horizon-weighted loss (hdecay=1.0) finding was an artefact of the masks bug.

### Europe

| Checkpoint | 120d MAPE | Notes |
|------------|-----------|-------|
| Pretrained (no finetuning) | 9.008% | Fixed eval |
| run_europe_20260601 | 9.297% | Marginal regression (-0.289pp overall) |

**Per-ticker 120d MAPE (run_europe_20260601):**

| Ticker | Pretrained | Finetuned | Delta |
|--------|-----------|-----------|-------|
| UL (Unilever) | 3.510% | 4.801% | +1.291pp (regression) |
| EADSF (Airbus) | 17.501% | 13.196% | -4.305pp |
| VWAGY (Volkswagen) | 6.012% | 9.893% | +3.881pp (regression) |

EADSF improves strongly (aerospace represented in training set). UL and VWAGY regress —
sector mismatch. Net result marginally worse than pretrained. Best val_loss 0.012377
(epoch 27). Europe is the weakest region.

### China

| Checkpoint | 120d MAPE | Notes |
|------------|-----------|-------|
| Pretrained (no finetuning) | 25.061% | Fixed eval; prior buggy eval showed 18.91% |
| **run_china_20260601** | **19.408%** | **Current best — beats pretrained by 5.653pp** |

**Per-ticker 120d MAPE (run_china_20260601):**

| Ticker | Pretrained | Finetuned | Delta |
|--------|-----------|-----------|-------|
| 0388.HK (HKEX) | 13.034% | 8.321% | -4.713pp |
| 2382.HK (Sunny Optical) | 22.224% | 25.807% | +3.583pp (regression) |
| 1177.HK (Sino Biopharma) | 39.924% | 24.096% | -15.828pp |

2/3 tickers improve. 2382.HK regresses — prior glia_2a showed 6.3% for this ticker,
which was entirely a masks-bug artefact. 1177.HK improvement is very large (-15.8pp).
Best val_loss 0.013984 (epoch 42, all 50 epochs ran). 

### Cross-Regional Summary

| Region | Pretrained | Finetuned | Delta | Win? |
|--------|-----------|-----------|-------|------|
| US | 8.731% | 8.468% | -0.263pp | ✓ |
| Japan | 12.485% | 11.139% | -1.346pp | ✓ |
| Europe | 9.008% | 9.297% | +0.289pp | ✗ |
| China | 25.061% | 19.408% | -5.653pp | ✓ |

---

## Training Script — What Works

**finetune_timesfm.py was restored from the Feb 22 backup (2026-05-31).**
The restored script preserves the winning training loop from Run 4:

- **Random masking is always ON** (hardcoded per paper Sec III-B): samples a random
  context window aligned to the right edge of the context buffer so the model trains
  on variable-length effective contexts in [min_context, max_context].
- **AdamW lr=1e-4, wd=0.01** — the confirmed best optimizer configuration (Run 4).
  SGD was tested in Runs 1 and 2: it cannot move weights at batch_size=8; the paper
  used batch_size=1024 on 8×V100 to make SGD viable. Do not use SGD.
- **Freeze 17/20 transformer layers** — trains only the last 3 transformer layers + output
  head (64M of 231M params). Critical for preventing catastrophic forgetting.
- **16× gradient accumulation** — effective batch size 128. Stabilises gradients.
- **warmup=3 epochs** for US; **warmup=5 epochs** for Japan/Europe/China.
- **MSE loss in log-price space** (paper Eq. 3)
- Saves via `model_wrapper._save_pretrained()` → standard `model.safetensors` format
- Default `--early-stopping 15` is active even without explicit flag. Has no effect on
  checkpoint quality since best is always saved, but terminates training early.

---

## Training Command Template

### US
```powershell
C:\Users\ylchen\workspace\timesfm\.venv\Scripts\python.exe `
  C:\Users\ylchen\workspace\timesfm_finetuning\finetune_timesfm.py `
  --tickers "^GSPC,AAPL,JNJ,JPM,XOM,PG,CAT,NEE,AMT,WMT" `
  --cache-dir "C:\Users\ylchen\workspace\research_group\data\us_feb22" `
  --model-id "C:\Users\ylchen\workspace\timesfm_finetuning\model" `
  --epochs 50 --batch-size 8 --lr 1e-4 --optimizer adamw --weight-decay 0.01 `
  --freeze-layers 17 --accumulation-steps 16 --warmup-epochs 3 `
  --max-context 512 --min-context 128 --horizon 128 `
  --no-epoch-ckpts --seed 42 `
  --save-dir "C:\Users\ylchen\workspace\research_group\artifacts\finetune_checkpoints\<run_name>"
```

### Japan / Europe / China
Use `--data-dir` (not `--tickers`/`--cache-dir`) since regional files use non-standard names.
```powershell
C:\Users\ylchen\workspace\timesfm\.venv\Scripts\python.exe `
  C:\Users\ylchen\workspace\timesfm_finetuning\finetune_timesfm.py `
  --data-dir "<region_train_dir>" `
  --model-id "C:\Users\ylchen\workspace\timesfm_finetuning\model" `
  --epochs 50 --batch-size 8 --lr 1e-4 --optimizer adamw --weight-decay 0.01 `
  --freeze-layers 17 --accumulation-steps 16 --warmup-epochs 5 `
  --max-context 512 --min-context 128 --horizon 128 `
  --stride <64_japan|32_europe|32_china> `
  --no-epoch-ckpts --seed 42 `
  --save-dir "C:\Users\ylchen\workspace\research_group\artifacts\finetune_checkpoints\<run_name>"
```

---

## Evaluation Command Template

```powershell
C:\Users\ylchen\workspace\timesfm\.venv\Scripts\python.exe `
  C:\Users\ylchen\workspace\timesfm_finetuning\scripts\rolling_eval.py `
  --checkpoint "C:\Users\ylchen\workspace\research_group\artifacts\finetune_checkpoints\<run_name>\best" `
  --tickers "<eval_tickers>" `
  --horizons "5,14,30,60,90,120" `
  --n-windows 15 `
  --cache-dir "<eval_cache_dir>" `
  --base-model "C:\Users\ylchen\workspace\timesfm_finetuning\model"
```

Eval tickers and cache dirs per region:
- US: `--tickers "NVDA,UNH,GS,CVX,KO,BA"` `--cache-dir data\us`
- Japan: `--tickers "8035.T,6902.T,4661.T"` `--cache-dir finetune_japan\data\eval`
- Europe: `--tickers "UL,EADSF,VWAGY"` `--cache-dir finetune_europe\data\eval`
- China: `--tickers "0388.HK,2382.HK,1177.HK"` `--cache-dir finetune_china\data\eval`

**rolling_eval.py (rewritten 2026-05-31, `--results-file` flag added 2026-06-01). Key design:**
- Feeds log-transformed context; exp-transforms predictions back to price space
- Mask = `torch.zeros(..., dtype=bool)` = full context given (no masking at inference)
- Rolling window anchor: `end_idx = (len(series) - max_h) - i * step`
- Loads checkpoint via `from_pretrained(base_model)` + `load_state_dict(load_file(ckpt))`
- `--results-file <path>` overrides default output location (`<checkpoint>/rolling_eval.json`)

---

## Cross-Market Findings

- **Sector matching is critical:** Training tickers must be in same sectors as eval tickers.
  Europe's weakness (UL/VWAGY regression) is due to sector mismatch; EADSF (aerospace) improves.
- **Data dilution:** More tickers from unrelated sectors hurts, not helps.
- **Val loss ≠ forecast quality:** Low val_loss doesn't guarantee low MAPE.
- **Val loss threshold:** Checkpoints with val_loss > 0.015 produce NaN at inference.
  Exception: China reached 0.013984 after 50 epochs — consistently slow to converge.
- **Random masking is required:** Without it, model overfits to fixed 512-step context and regresses 3–4pp.
- **Stride matters for window count:** China needs stride=32 (~900 windows) to cross the
  val_loss<0.015 threshold. stride=128 gives only ~230 windows — insufficient.
- **Buggy rolling_eval.py invalidated all pre-2026-05-31 regional results.** Prior Japan
  "improvement" from hdecay=1.0 was a masks-bug artefact; standard MSE works fine.
  Prior China "improvement" of +6.9pp at 120d was similarly inflated.
- **Training on current vs historical data matters for US:** Training on data through
  May 2026 caused NVDA to regress (+3.2pp vs pretrained). Use us_feb22 cache for
  reproducible US experiments.

---

## Known Dead Ends (do NOT retry)

- **No random masking:** Removing random masking causes 3–4pp regression (confirmed May 31).
  The paper's variable-context training is essential, not optional.
- **SGD optimizer:** Cannot move weights at batch_size=8 regardless of LR. Runs 1 (lr=5e-4)
  and 2 (lr=5e-3) both produced zero inference change. AdamW is required.
- **Adam without weight decay:** Run 3 showed catastrophic overfitting (train 0.014→0.0003,
  val 0.016, heavy degradation on UNH/GS/BA). Weight decay is essential.
- **100+ diverse tickers:** Dilutes signal → regression. Confirmed across US Runs 5, 6, 6b.
- **Continuing from finetuned checkpoint:** Accumulated over-adaptation (US Run 5).
- **13+ tickers at lr=1e-4:** Risk of NaN weights.
- **BA in training set:** Too volatile, disrupts shared training distribution.
- **context=1024:** Regression (patch-position OOD for finetuned model).
- **Single-layer finetuning:** NaN — layers 17-19 are tightly coupled minimum unit.
- **Equal-weight ensemble:** Worse than best single checkpoint.
- **Single-window evaluation:** Unreliable (~1pp noise). Always use 15 rolling windows.
- **rolling_eval.py with `torch.ones_like` masks:** Silently zeroed all context (FIXED 2026-05-31).
  All pre-fix regional results (Japan hdecay, China glia_2a) are invalid — do not reference.
- **xreg at 60d+:** Diverges.
- **Non-uniform layer selection:** No benefit over monotonic freeze.
- **Japan horizon-weighted loss (hdecay=1.0):** Appeared to improve under buggy eval;
  standard MSE with stride=64 is simpler and produces genuine improvement (confirmed 2026-06-01).
- **China train_long (6 long-history tickers):** val_loss 0.036 — fails to reach valid basin.
  Use all 10 tickers with stride=32.
- **Training on current data for US:** Using data through May 2026 causes NVDA regression.
  Always use us_feb22 cache for US training.

---

## Constraints

- Do NOT delete existing checkpoints under `artifacts/finetune_checkpoints/`.
- Do NOT modify model architecture files in `timesfm/src/timesfm/timesfm_2p5/` or `timesfm/src/timesfm/torch/`.
- You MAY modify `timesfm_finetuning/finetune_timesfm.py` (e.g. add new loss terms).
- You MAY write new helper scripts — save them to `artifacts/` with descriptive names.
- Always use `--no-epoch-ckpts` when training.
- Label experiments clearly: `finetune_checkpoints/run_<region>_<date>/`

---

## Metrics

- **Primary: MAPE** (lower is better). Report at horizons 5, 14, 30, 60, 90, 120 days.
- **Secondary: DirAcc** (higher is better).
- Always report BOTH metrics with per-ticker breakdown.
- Use 15-window rolling evaluation for definitive comparisons, not single-window.
- **US target:** beat 8.468% 120d MAPE (run_us_feb22data_20260531).
- **Japan target:** beat 11.139% 120d MAPE (run_japan_20260531).
- **Europe target:** beat 9.008% 120d MAPE (pretrained baseline — finetuning currently regresses).
- **China target:** beat 19.408% 120d MAPE (run_china_20260601).
