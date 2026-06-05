---
name: hyperparameter-search
description: Methodology for ML hyperparameter search and optimization. Use for designing search spaces, choosing search strategies (random / grid / Bayesian / evolutionary / multi-fidelity), allocating compute budget, comparing tuned configurations rigorously, and avoiding common pitfalls (test-set leakage, tuning-induced overfitting, comparing tuned vs untuned). Designed as the Methods supervisor's expertise for V2 ablation runs on hyperparameter-search tasks (T2 in EVALUATION_PROTOCOL.md §2).
allowed-tools: Read Write Edit Bash
license: MIT license
metadata:
    skill-author: research_group project
    skill-version: "0.1.0"
---

# Hyperparameter Search Methodology

## Overview

Hyperparameter search is choosing the values of training-time configuration
(learning rate, batch size, weight decay, regularization strength,
architecture variants, optimizer choice, schedule shape, augmentation
policies, ...) that maximize a held-out objective. The methodology matters
because (a) the search itself can overfit to the validation set,
(b) different search strategies have very different sample efficiency,
(c) "we tuned LR" is often a confound when comparing methods, and
(d) compute is rarely free — wasted trials add up.

## When to Use This Skill

This skill should be used when:
- Designing or critiquing a hyperparameter search procedure for an ML task
- Comparing hyperparameter optimization (HPO) methods (random / grid /
  Bayesian / evolutionary / multi-fidelity)
- Allocating compute budget across trials (parallel vs sequential,
  early-stopping schemes)
- Evaluating whether two trained models can be compared fairly given
  different tuning effort
- Identifying common HPO pitfalls in a research workflow
- Reviewing a Researcher's experimental design from the Methods supervisor
  perspective in a V2 ablation run on a hyperparameter-search task

## 1. Search-Space Design

The search space is the most consequential decision — a poorly chosen
space can make any strategy look bad.

### Per-dimension scale

- **Learning rate**: log-uniform, e.g. `loguniform(1e-5, 1e-1)`. Linear
  scales waste trials on the high-LR tail.
- **Weight decay**: log-uniform, e.g. `loguniform(1e-6, 1e-2)`.
- **Batch size**: discrete log scale, `[16, 32, 64, 128, 256, 512]`.
- **Dropout / label smoothing / augmentation strength**: linear, `[0, 0.5]`.
- **Optimizer choice**: categorical (SGD-momentum, AdamW, Lion, ...).
- **LR schedule**: categorical (cosine, step, OneCycle, none).

### Boundary checks

After a search completes, inspect the marginal distribution of the best
trials. If the optimum lies on the boundary of a range, the range was too
narrow — re-run with a wider window. This is the single most common
search-design failure.

### Conditional spaces

Some hyperparameters only exist conditional on others (e.g.,
`momentum` exists for SGD but not for Adam). Use conditional / hierarchical
search spaces (Optuna's `suggest_*` inside `if optimizer == ...`, Ray Tune's
`tune.sample_from`, etc.) instead of flat spaces with ignored dimensions.

## 2. Search Strategies

### Random search (the default benchmark)

- Sample independently from the joint distribution.
- Embarrassingly parallel.
- Strong baseline that beats grid search in moderate-to-high dimensions
  (Bergstra & Bengio 2012). Always include it as a comparison.

### Grid search

- Use only when (a) the space is small and discrete, (b) you need to
  report the full marginal effect of each dimension. Otherwise prefer
  random or Bayesian.

### Bayesian / model-based search

- **Gaussian Process (GP)**: gold standard for low-dim continuous spaces,
  small budgets (<200 trials).
- **Tree-structured Parzen Estimator (TPE)**: scales better with mixed
  / categorical / conditional spaces. Optuna default.
- **SMAC** (random forests + acquisition function): well-suited to mixed
  spaces.

Bayesian methods exploit observed trials to suggest new ones. They are
NOT embarrassingly parallel — careful when running many parallel workers.

### Multi-fidelity

- **Successive Halving / Hyperband**: train each trial briefly, kill the
  worst, double budget for survivors, repeat.
- **ASHA (asynchronous successive halving)**: parallel-friendly variant
  used by Ray Tune, Vizier.
- **BOHB**: combines Bayesian (TPE) suggestions with Hyperband budget
  allocation. Strong default for moderate compute.

When the per-trial cost is high (large models, slow datasets), multi-fidelity
methods are typically 5-10× more sample-efficient than vanilla random or
Bayesian search.

### Evolutionary / Population-Based Training

- **PBT (Population-Based Training)**: a population of workers periodically
  exploits the best and explores around it during training. Useful when
  schedule hyperparameters (LR over time) themselves are part of the
  search.
- Genetic / CMA-ES algorithms: niche; mostly relevant when the loss
  landscape is rugged and not differentiable.

## 3. Budget Allocation

### Trial budget

A reasonable starting heuristic for N hyperparameters:
- Random / TPE search: ~30N trials
- Bayesian (GP) search: ~10-15N trials
- Multi-fidelity: ~3-5× more nominal trials (most are killed early)

But the binding constraint is usually wall-clock or dollars, not trial count.
Convert your compute budget to "equivalent full-fidelity trials" before
comparing strategies.

### Parallel vs sequential

- Parallel workers reduce wall-clock but increase total compute (trials
  cannot inform each other across the parallel batch).
- For Bayesian / TPE search, keep `parallel < 0.2 × total_trials` to
  preserve sample efficiency.
- For multi-fidelity, parallelism helps because most trials are short.

### Early stopping

Always prune trials whose intermediate validation curves are clearly
worse than the running best. Median-stopping, ASHA brackets, or simple
"stop if val < running median at epoch N" work. Add a minimum-warmup
period (often 10-20% of full training) to avoid stopping legitimately
slow-starting configurations.

## 4. Reproducibility

- Pin all stochastic seeds: framework (PyTorch / TF / JAX), numpy,
  Python `random`, CUDA determinism flags. Document them in the search
  config.
- Pin software versions (PyTorch, CUDA, cuDNN). Different cuDNN versions
  produce different gradients on the same seed.
- Pin data version: dataset preprocessing, splits, augmentation seeds.
- Save the search history (every trial's config + result), not just the
  best. Reviewers will ask for it.
- Re-run the chosen best config from scratch with a different seed to
  estimate genuine performance vs tuning noise.

## 5. Statistical Comparison

### The seed problem

A "1% accuracy improvement" across two models trained with one seed each
is well below the seed-to-seed noise of CIFAR-10 training (~0.3-0.5pp
typical). Always re-train the headline configurations across at least
3-5 seeds.

### Tuning-induced overfitting

The hyperparameter search itself overfits to the validation set. The more
trials you run, the bigger the gap between your reported validation
accuracy and a fresh test accuracy. Two protections:

1. Hold out a *third* split (val for tuning, test for the final number)
   and report both.
2. Bonferroni-style discount: if you tried `N` configurations, your
   validation result has effectively `log(N)` extra observations of
   noise; widen confidence intervals accordingly.

### Comparing methods

- Fix tuning effort across compared methods. "Method A with 100 trials
  vs Method B with 10 trials" is not informative about A-vs-B; it tests
  search effort.
- Report wall-clock per result, dollars per result, AND best-result-vs-budget
  curves — not just the final number.
- Use paired statistics (paired Wilcoxon, paired t) across seeds when
  comparing two methods on the same task.

## 6. Common Pitfalls

| Pitfall | What goes wrong | Mitigation |
|---|---|---|
| **Comparing tuned vs untuned** | Method A with tuning beats Method B with defaults — this is a tuning-effort comparison, not a method comparison | Fix tuning effort or compare best-of-N for both |
| **Test-set leakage** | Tuning on test, then reporting test accuracy | Strict val/test split; never optimize against test |
| **Boundary optima** | Best trial sits on edge of search range | Inspect marginals; widen and re-run |
| **One-seed reporting** | Differences within seed noise | n>=3 seeds for headline; paired stats |
| **Mismatched compute** | Method A given 10× the compute of B | Equate budgets explicitly |
| **Default-baseline comparisons** | "Beats default" is trivial | Compare against a strong baseline that itself was tuned |
| **No early stopping** | Wasted compute on doomed trials | ASHA / median stop / Hyperband |
| **Search over irrelevant dims** | LR matters 10× more than weight decay; spending budget on WD is wasted | Sensitivity analysis; prune low-impact dims |
| **Re-using seeds across trials** | Apparent improvement is just initialization luck | Independent seeds per trial |
| **Comparing across datasets/preprocessing** | Different val sets → different "best" not commensurable | Pin preprocessing exactly |

## 7. Tools

| Tool | Best for |
|---|---|
| **Optuna** | Default for new projects; TPE, ASHA, multi-objective, Python-native, conditional spaces |
| **Ray Tune** | Large-scale parallel; ASHA, PBT, BOHB; integrates with most frameworks |
| **Weights & Biases Sweeps** | Cloud-managed Bayesian / random / grid; nice dashboards |
| **scikit-optimize** | Lightweight GP search for small problems |
| **HyperOpt** | Original TPE implementation |
| **NNI (Microsoft)** | Wide algorithm coverage; less community momentum |
| **Vizier (Google)** | Production-grade; also available open source |
| **Determined** | If you need full experiment infra around HPO |

## 8. Methods-Supervisor Critique Patterns

When supervising an HPO research run, watch for these structural issues:

- **"We picked LR=1e-3 because it works"**: ask whether they searched, over
  what range, and whether the optimum was at a boundary.
- **"Bayesian search found X"**: ask how many trials, what initial random
  seed budget, whether parallelism was capped to preserve sample efficiency.
- **"We compared method A and B"**: ask whether the *tuning budgets* were
  matched, not just the trial counts.
- **"Results across N runs"**: ask whether N is independent reruns of the
  same config or N trials within a search.
- **"Best validation = X%"**: ask whether they have a held-out test set and
  whether they reported it; if not, mention tuning-induced overfitting.
- **"We used the default config from the paper"**: ask whether the paper's
  defaults were tuned for THEIR experimental setup, not the current one.

## 9. CIFAR-10 ResNet — task-specific reference points (T2)

For the EVALUATION_PROTOCOL §2 T2 task (CIFAR-10 ResNet-18 hyperparameter
search), these are typical operating points to ground-truth search results:

- Vanilla SGD-momentum + cosine LR + label smoothing (0.1) +
  RandAugment is a strong baseline and reaches ~94-95% val accuracy.
- Initial LR around `0.1` for SGD with batch size 128, scaled linearly
  with batch size.
- Weight decay around `5e-4`.
- 100-200 epochs typical full training; multi-fidelity HPO methods
  routinely use 10-30 epochs per intermediate trial.
- Per-trial cost: ~5-15 GPU-minutes on a single A100 for full training;
  multi-fidelity reduces effective cost by 5-10×.

Trials reporting accuracy outside ~91-96% on CIFAR-10 ResNet-18 are
suspect: too low usually means a training bug or an extreme-edge LR;
too high usually means test-set leakage or an architecture much larger
than ResNet-18.

## References

- Bergstra & Bengio, "Random Search for Hyper-Parameter Optimization", JMLR 2012.
- Li et al., "Hyperband: A Novel Bandit-Based Approach to Hyperparameter Optimization", JMLR 2018.
- Falkner et al., "BOHB: Robust and Efficient Hyperparameter Optimization at Scale", ICML 2018.
- Jaderberg et al., "Population Based Training of Neural Networks", arXiv 2017.
- Liaw et al., "Tune: A Research Platform for Distributed Model Selection and Training", ICML AutoML 2018.
- Akiba et al., "Optuna: A Next-generation Hyperparameter Optimization Framework", KDD 2019.
