# K2T Mode Answer Contracts

Purpose: lift benchmark-style answers from safe/good to expert/complete by enforcing mode-specific structure.

## Universal answer quality contract

Every benchmark-style answer should include:
- direct classification or answer first
- evidence used
- assumptions and unknowns
- concrete next action
- validation or test plan
- acceptance criteria
- risks / failure modes
- concise final recommendation

Avoid generic answers. Prefer specific, auditable, command-ready, rubric-aligned responses.

## diagnose mode

Required structure:
1. Classification: PASS / REVIEW / FAIL.
2. Observed evidence.
3. What the evidence proves.
4. What the evidence does not prove.
5. Most likely root cause.
6. Safe next commands.
7. Expected output.
8. Decision tree.
9. Rollback / do-not-touch warning.

## review mode

Required structure:
1. Verdict: PASS / REVIEW / FAIL / REJECTED.
2. Scope reviewed.
3. Findings by severity.
4. Evidence for each finding.
5. False-positive checks.
6. Required fixes.
7. Regression tests.
8. Final acceptance gate.

## benchmark_judge mode

Required structure:
1. Score / classification.
2. Rubric mapping.
3. Evidence quotes or summarized evidence.
4. Strengths.
5. Weaknesses.
6. Hard-fail scan.
7. False-positive analysis.
8. Corrected final judgment.

## minimal_safe_patch mode

Required structure:
1. Scope and non-goals.
2. Minimal patch.
3. Why it is safe.
4. Tests to add or run.
5. Rollback plan.
6. Security boundaries preserved.
7. Acceptance criteria.
8. Residual risk.

## risk_register mode

Required structure:
1. Risk ID.
2. Trigger / cause.
3. Impact.
4. Likelihood.
5. Severity.
6. Control / mitigation.
7. Detection signal.
8. Test / validation.
9. Owner.
10. Residual risk.

## turnover mode

Required structure:
1. Purpose.
2. Current state.
3. Architecture / paths / files.
4. What changed.
5. Evidence and validation.
6. Known defects.
7. Operational runbook.
8. Next steps.
9. Do-not-do warnings.

## decision_memo mode

Required structure:
1. Recommendation.
2. Decision context.
3. Options considered.
4. Evidence.
5. Risks.
6. Cost / tradeoff.
7. Implementation path.
8. Acceptance gate.

## calculation_or_validation mode

Required structure:
1. Inputs.
2. Assumptions.
3. Formula.
4. Unit handling.
5. Calculation.
6. Sanity check.
7. Edge cases.
8. Validation result.
