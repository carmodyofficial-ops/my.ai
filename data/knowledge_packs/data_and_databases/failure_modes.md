# Data and Databases — Failure Modes

## Common Failure Modes

- destructive migrations
- bad indexes
- silent data corruption
- schema drift

## Recovery Pattern

1. Identify what failed.
2. Separate symptom from cause.
3. Check evidence.
4. Pick the smallest safe correction.
5. Validate.
6. Record a lesson if durable.
