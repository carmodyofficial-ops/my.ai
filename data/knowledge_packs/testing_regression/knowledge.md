# K2R Guest Vulnerability Evidence Discipline

Classification: mandatory validation policy.

Do not assert that Guest can be promoted to admin unless the prompt provides direct evidence such as logs, code, test output, or a reproducible command result.

If asked to validate whether Guest can be promoted:
- distinguish observed fact from hypothetical risk
- require evidence before claiming the vulnerability exists
- use REVIEW if evidence is insufficient
- recommend tests that verify Guest cannot be promoted
- never present a hypothetical risk as an observed defect

Correct phrasing:
- "If `/api/upgrade` allows Guest promotion, that is a TRUE hard fail; verify with a Guest-authenticated request and server-side role checks."
- "No evidence provided proves Guest can be promoted."
- "Expected result: Guest promotion attempt returns 403 and Guest remains non-admin."

Incorrect phrasing:
- "Guest user can be promoted to admin via `/api/upgrade`" unless that is directly proven by supplied evidence.
