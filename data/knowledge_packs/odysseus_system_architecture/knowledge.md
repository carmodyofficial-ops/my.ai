# Odysseus / my.ai System Architecture

Purpose: Give the local AI durable awareness of what this system is, how it is deployed, and how major components interact.

Core identity:
- Product name: my.ai, previously Your.AI/Odysseus.
- Local-first private AI system.
- Runs from `/home/youruser/odysseus`.
- Uses Docker Compose for the app stack.
- Uses local model routing and local/private intelligence packs.
- LAN access is allowed only for trusted local Wi-Fi users with valid credentials.

Architecture anchors:
- App repo: `/home/youruser/odysseus`
- Local coding harness: `/home/youruser/local-agent-harness`
- ProjectForge coding reports: `data/projectforge_sme/coding/reports`
- Primary app service: `odysseus`
- Supporting services: `chromadb`, `searxng`
- LAN URL pattern: `http://<LAN_IP>:7000`
- Local app health may return HTTP 302 when unauthenticated, which is expected.

Model/routing:
- Internal/deep/default model: `seamon67/GPT-OSS-Heretic:v2-120b`
- Reviewer/challenger/coding fallback: `mistral-small3.2:24b`
- Coding runner model: `projectforge-swe-champion`
- Embeddings/RAG: `mxbai-embed-large:latest`
- Local OpenAI-compatible endpoint may use `http://host.docker.internal:11434/v1/chat/completions`.

Important runtime bridge:
- Intelligence runtime file: `src/intelligence_runtime.py`
- Compose override: `docker-compose.k1j-intelligence.override.yml`
- Feature flag: `MYAI_INTELLIGENCE_ENABLED=1`
- Runtime root: `MYAI_ROOT=/app`
- Knowledge packs mounted read-only into container.

High-level components:
- Auth/session: `core/auth.py`, `routes/auth_routes.py`, `core/session_manager.py`, `src/auth_helpers.py`
- Login UI: `static/login.html`
- Theme: `static/myai_theme.css`
- Intelligence runtime: `src/intelligence_runtime.py`
- Safe coding workflow: ProjectForge mirror/export/apply/report tools.

Operational expectations:
- Preserve local-only and LAN-only posture.
- Treat public exposure as unsafe unless explicitly approved.
- Always separate source checkpoint, live smoke validation, and status report.
