"""Wearables Gateway — narrow, authenticated backend for glasses companions.

The gateway is the ONLY surface a wearable companion app (a phone paired to
Ray-Ban Meta glasses) talks to. It never exposes Ollama, ProjectForge,
ChromaDB, or SearXNG directly; it reuses the existing AuthMiddleware,
ApiToken device credentials, STT/TTS services, and the agent-loop
conversation runtime with a locked-down toolset.

Route layer: routes/wearables_routes.py (setup_wearables_routes).
Design docs: docs/wearables/.
"""
