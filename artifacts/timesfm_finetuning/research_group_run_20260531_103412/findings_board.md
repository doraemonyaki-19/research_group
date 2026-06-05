# Findings Board
(append-only, populated by researchers each turn)


## Turn 1
- R1: rewritten scripts + exp_11 recipe baseline replication → PENDING execution → validates rewrites or triggers debug
- R2: horizon-loss-decay=0.5 vs baseline → PENDING execution → if 120d neutral/positive, try 1.0 next


## Turn 1 — Results (post-eval)
- CRITICAL: finetuning REGRESSES the model. Pretrained 120d MAPE=8.73% beats R1=12.63% and R2=12.00%.
- R2 (decay=0.5) partially helps vs R1 (-0.634pp at 120d) but still 3.27pp below pretrained.
- Only CVX and KO show 120d improvement from finetuning; NVDA/UNH/GS/BA all regress significantly.
- rolling_eval.py had NaN-120d bug (window placement); fixed. All old exp results were contaminated by masks bug.
- PIVOT: finetuning recipe needs fundamental rethink. Investigate catastrophic forgetting vs domain mismatch.

