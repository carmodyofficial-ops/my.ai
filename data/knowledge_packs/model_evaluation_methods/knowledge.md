# Model Evaluation Methods

## Benchmark / eval-set design
- Held-out prompts only; never store benchmark answers in a knowledge pack or training set (contaminates retrieval + inflates scores).
- Match eval distribution to production traffic; sample real user queries into the set, stratify by task type, difficulty, language, safety-sensitivity.
- Size for signal: enough items that a meaningful delta clears the confidence interval; tiny sets (n<50) give noisy, unreproducible deltas.
- Version and freeze eval sets; changing items mid-flight makes runs incomparable. Keep a changelog.
- Contamination check: search training/pretrain corpus for verbatim eval strings; canary strings + n-gram overlap catch leakage.
- Keep a hidden holdout never shown to model authors to detect overfitting to the public eval.

## Metrics -> when to use
- **Classification**: accuracy only when classes balanced; else precision/recall/F1, and PR-AUC over ROC-AUC under heavy imbalance.
- **Confusion-matrix first**: per-class precision/recall exposes what aggregate accuracy hides.
- **Ranking/retrieval**: nDCG, MRR, recall@k, hit@k; always report k.
- **Generation (code/reasoning)**: `pass@k` (unbiased estimator over n>k samples); functional/unit tests beat surface metrics.
- **Text overlap (BLEU/ROUGE/METEOR)**: cheap but weak — reward n-gram overlap, blind to meaning/paraphrase; use only for translation/summarization sanity, never as sole quality gate.
- **Semantic**: BERTScore / embedding cosine capture paraphrase but are model-dependent; report the scorer.
- **Calibration**: ECE (expected calibration error), Brier score, reliability diagrams; a model can be accurate yet badly calibrated. Temperature scaling fixes calibration post-hoc cheaply.
- **Safety/refusal**: track false-refusal rate and unsafe-completion rate as a pair; optimizing one alone regresses the other.

## LLM-as-judge
- Anchor the rubric: explicit 1-5 (or pass/fail) criteria with worded anchors + 2-5 gold-labeled exemplars per score point.
- **Pairwise > pointwise** for quality/preference (more reliable, less scale drift); pointwise for absolute thresholds/rubric compliance.
- Control **position bias**: swap A/B order and average, or randomize; judges favor the first (or last) option.
- Other judge biases to counter: length/verbosity bias, self-preference (a model rates its own family higher), sycophancy, formatting/markdown bias.
- Validate the judge against humans: Cohen's/Fleiss kappa or Spearman correlation on a labeled subset; report agreement before trusting judge scores.
- Use a different/stronger model as judge than the one under test where possible; ensemble or majority-vote judges reduce variance.
- Chain-of-thought before the verdict improves judge reliability; parse the final label, not the reasoning.

## Human eval design
- Write annotation guidelines with edge cases; pilot, then measure **inter-annotator agreement** (kappa/Krippendorff's alpha) — alpha<0.6 means fix the rubric, not the annotators.
- Multiple raters per item + adjudication for disagreements; collect raw labels, not just aggregates.
- Randomize + blind model identity; counterbalance order to kill anchoring/fatigue effects.
- Report rater count, agreement, and rejection criteria alongside scores.

## A/B (online) vs offline eval
- Offline first (fast, cheap, reproducible) to gate; online A/B for real-user impact on the north-star metric.
- A/B: pre-register hypothesis + primary metric; power-analysis the sample size before launch; watch guardrail metrics (latency, cost, safety) not just the win metric.
- Beware novelty effect and cross-arm interference; run full business cycles (>=1 week) to cover weekday/weekend.
- CUPED / stratification reduces variance and shortens experiments.

## Statistical significance
- Report confidence intervals, not just point estimates; bootstrap CIs for non-normal metrics (pass@k, nDCG).
- Paired tests (McNemar for classification, paired bootstrap/permutation for generation) since both models see the same items — far more powerful than unpaired.
- Correct for multiple comparisons (Bonferroni/Benjamini-Hochberg) when scanning many metrics/slices.
- p<0.05 at n=30 is fragile; state effect size + CI so a "win" inside the noise band is visible as such.

## Regression eval sets
- Maintain a curated regression suite of past failures + high-value cases; run every model/prompt change through it as a gate.
- Golden set with expected outputs for deterministic checks; snapshot diffs surface silent regressions.
- Slice metrics (by segment/language/difficulty) — aggregate can rise while a critical slice collapses.

## Gotchas -> Fix
- **Score looks great, users unhappy**: benchmark != task distribution. Fix: sample real production queries into the eval set; slice by segment.
- **New model wins offline, loses in A/B**: offline metric is a poor proxy. Fix: validate the proxy correlates with the online north-star before trusting it.
- **Judge scores drift run-to-run**: temperature/position/version instability. Fix: judge at temp 0, pin judge model+prompt version, swap-and-average positions.
- **Accuracy high, model overconfident**: uncalibrated. Fix: measure ECE, apply temperature scaling, report calibration alongside accuracy.
- **BLEU/ROUGE up but quality flat**: overlap metric gamed by copying. Fix: add semantic + human/LLM-judge checks; never gate on overlap alone.
- **Eval improves suspiciously fast**: contamination/overfitting to the public set. Fix: canary strings, n-gram leak scan, rotate a hidden holdout.
- **Two models "tie"**: underpowered. Fix: increase n, use paired tests, report CI width.
- **High accuracy, one class ignored**: imbalance masked by aggregate. Fix: per-class precision/recall + PR-AUC, confusion matrix.
- **Annotators disagree wildly**: ambiguous rubric. Fix: add anchors + edge-case examples, re-pilot, re-measure kappa.
- **Prompt tweak helps eval, hurts prod**: overfit to eval wording. Fix: hold out a private eval the prompt author never sees.
- **Cherry-picked demo passes, suite fails**: selection bias. Fix: gate on the full regression suite, not curated examples.
