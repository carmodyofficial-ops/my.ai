# my.ai System Core — Architecture

my.ai is the local AI power stack built from the Odysseus/ProjectForge work.

Principles:
- local-first
- LAN-capable on trusted network
- authentication required
- no public exposure by default
- local ProjectForge/Odysseus work should not be synced to GitHub unless explicitly requested
- knowledge, memory, skills, and evals should be validated

High-level components:
- chat interface
- auth/account model
- LAN proxy/service binding
- agent mode
- skills manager
- tool guard
- workspace/run envelope system
- knowledge packs
- memory store
- evaluation reports
