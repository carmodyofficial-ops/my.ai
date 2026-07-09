# my.ai System Architecture Runtime Brief

Updated: 2026-06-22T01:00:24.487450+00:00

## Identity

The system is my.ai/Odysseus: a local-first AI application running from `/home/vc_wrkstn/odysseus`.

The product was previously branded Your.AI and is being changed to my.ai with a light grey/neutral theme.

## Core runtime

Important runtime pieces:

- Main repo: `/home/vc_wrkstn/odysseus`
- Docker compose base: `docker-compose.yml`
- Intelligence override: `docker-compose.k1j-intelligence.override.yml`
- Main app container: `odysseus-odysseus-1`
- Supporting containers: `odysseus-chromadb-1`, `odysseus-searxng-1`
- Intelligence runtime: `src/intelligence_runtime.py`
- Main chat processor: `src/chat_processor.py`
- Auth manager: `core/auth.py`
- Auth routes: `routes/auth_routes.py`
- Login UI: `static/login.html`
- Theme override: `static/myai_theme.css`

## Model routing

Known local model endpoints:

- App internal endpoint: `http://host.docker.internal:11434/v1/chat/completions`
- Host local endpoint often used for benchmarks: `http://127.0.0.1:11434/v1/chat/completions`
- Primary deep model: `seamon67/GPT-OSS-Heretic:v2-120b`
- Coding/runner model path includes ProjectForge and `projectforge-swe-champion`

## Knowledge and intelligence

Knowledge packs live under:

- `data/knowledge_packs`
- `data/projectforge_sme/knowledge_packs/tools`
- `data/projectforge_sme/knowledge_packs/evals`

The intelligence runtime is feature-flagged:

- `MYAI_INTELLIGENCE_ENABLED=1`
- `MYAI_ROOT=/app`

It is intended to be local-only, read-only, fallback-safe, and non-tool-executing.

## ProjectForge safe coding

ProjectForge work is local-only unless the owner explicitly asks to sync to GitHub.

Safe coding artifacts include:

- Patch mirror workflow.
- Patch hygiene validation.
- Controlled live patch apply.
- Reports under `data/projectforge_sme/coding/reports`.
- Safe mirror under `/home/vc_wrkstn/local-agent-harness/swe_style/repos/odysseus_safe_ui_mirror_repo`.

## Security posture

Default posture:

- Local-only.
- LAN access is allowed for trusted Wi-Fi devices with valid credentials.
- Public internet exposure is not allowed by default.
- Admin remains privileged.
- Built-in Guest is immutable and low privilege.

## Answer discipline

When asked to classify terminal output, use:

- PASS
- REVIEW
- FAIL
- REJECTED

Ground conclusions in observed evidence. Do not claim tests, commits, smokes, or deployments passed unless output proves it.
