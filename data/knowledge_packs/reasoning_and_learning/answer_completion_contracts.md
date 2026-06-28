# K1Q Answer Completion Contracts

Purpose: prevent locally generated answers from ending before all required artifacts are complete.

## Universal Completion Protocol

1. Identify the requested artifact type.
2. List the required sections internally before drafting.
3. Complete every requested section.
4. Include assumptions when requirements are incomplete.
5. Include risks, validation, rollback, and next actions when the task changes software, infrastructure, process, data, safety, or operations.
6. For code, provide complete runnable code, dependencies, run commands, and tests.
7. For long-context synthesis, account for every named milestone, defect, artifact, and decision.
8. For guarded domains such as health or finance, provide safety boundaries, uncertainty, and escalation guidance.
9. Before finalizing, perform a missing-section check.
10. End with COMPLETE only when the response is complete.

## Failure Modes To Avoid

- Cutting off mid-sentence.
- Omitting the final requested milestone or artifact.
- Providing a plan without validation.
- Providing infrastructure changes without rollback.
- Providing code without tests.
- Providing product plans without metrics, owners, risks, and launch criteria.
- Giving health or finance guidance without guardrails.
