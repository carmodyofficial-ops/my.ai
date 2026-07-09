# Data, Memory, and RAG Policy

Purpose: Keep retrieval and memory useful without compromising privacy or correctness.

Principles:
- Knowledge packs should be read-only unless explicitly updated.
- Memory writes should be deliberate.
- Guest should not manage memory.
- Owner-scoped data must remain owner-scoped.
- Retrieval should improve answers but not override security rules.
- The model must distinguish retrieved facts from assumptions.
- Do not leak private content across users.
- Do not cite or rely on stale data for current-market decisions.

RAG quality:
- Prefer compact, high-signal packs.
- Avoid benchmark answer leakage.
- Include policies, architecture, runbooks, and rubrics.
- Keep benchmark questions separate from benchmark knowledge.
