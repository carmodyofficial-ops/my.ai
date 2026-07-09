# Knowledge Pack Routing Policy

## Purpose

The retrieval router maps a user query to the most relevant knowledge packs before my.ai answers or acts.

## Routing Principles

1. Prefer high-priority packs when relevance is similar.
2. Always flag guarded packs.
3. Route system, LAN, auth, local-only, service, and architecture queries to my_ai_system_core.
4. Route reasoning, uncertainty, verification, reflection, memory consolidation, and pondering queries to reasoning_and_learning.
5. Route skill, tool, action, diagnostic, patch, validation, and handoff queries to skills_and_tools.
6. Route RAG, agent, embedding, hallucination, eval, and model workflow queries to ai_engineering.
7. Route source, evidence, citation, freshness, recency, assumption, and research queries to research_methods.
8. Route broad technical queries to the relevant technical domain pack.
9. Route health and finance topics to guarded packs with caution flags.
10. Do not treat routing as final truth; routing is a relevance estimate that should be validated by retrieval and answer quality.

## Output Requirements

A routed query should include:

- query
- selected packs
- relevance score
- reason
- trust level
- priority
- guarded/caution flag
- suggested next action
