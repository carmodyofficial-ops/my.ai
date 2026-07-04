<p align="center">
  <img src="docs/odysseus-wordmark.png" alt="Odysseus" width="280">
</p>

<p align="center">
  A self-hosted AI workspace for chat, agents, research, documents, email, notes, calendar, and local model workflows.
</p>

<p align="center">
  <a href="#quick-start">Quick Start</a> ·
  <a href="docs/setup.md">Setup Guide</a> ·
  <a href="CONTRIBUTING.md">Contributing</a> ·
  <a href="ROADMAP.md">Roadmap</a>
</p>

<p align="center">
  <a href="https://repology.org/project/odysseus-ai/versions"><img src="https://repology.org/badge/vertical-allrepos/odysseus-ai.svg" alt="Packaging status"></a>
</p>

<p align="center">
  <img src="docs/odysseus.jpg" alt="Odysseus interface">
</p>

---

## Quick Start

> `dev` is the default branch and gets the newest changes first. Use [`main`](https://github.com/carmodyofficial-ops/my.ai/tree/main) if you want the more curated branch.

```bash
git clone https://github.com/carmodyofficial-ops/my.ai.git
cd odysseus
cp .env.example .env
docker compose up -d --build
```

Open `http://localhost:7000` when the containers are healthy. The first admin password is printed in `docker compose logs odysseus`.

Native installs, GPU notes, Windows/macOS instructions, HTTPS, and configuration live in the [setup guide](docs/setup.md).

## Features

- **Chat + Agents** — local/API models, tools, MCP, files, shell, skills, and memory.
- **Cookbook** — hardware-aware model recommendations, downloads, and serving.
- **Deep Research** — multi-step web research with source reading and report generation.
- **Compare** — blind side-by-side model testing and synthesis.
- **Documents** — writing-first editor with AI edits, suggestions, Markdown, HTML, CSV, and syntax highlighting.
- **Email** — IMAP/SMTP inbox with triage, tags, summaries, reminders, and reply drafts.
- **Notes, Tasks + Calendar** — reminders, todos, scheduled agent tasks, and CalDAV sync.
- **Extras** — gallery/image editor, themes, uploads, web search, presets, sessions, and 2FA.

## AI Model Stack

This deployment runs entirely on local, self-hosted models — no cloud providers are configured. Models are served over two OpenAI-compatible endpoints and selected per turn by the built-in auto model-router.

| Endpoint | Host | Kind | Models |
|---|---|---|---|
| `b1c40fa2` | `host.docker.internal:11434` | Ollama (local) | `seamon67/GPT-OSS-Heretic:v2-120b`, `Qwen/Qwen3-32B`, `gpt-oss:20b`, `mistral-small3.2:24b`, `qwen3-coder:30b`, `deepseek-r1:32b`, `qwen3.6:27b`, `mxbai-embed-large` (embeddings) |
| `632e40fc` | `host.docker.internal:8787` | OpenAI-compatible (local) | `projectforge-swe-champion` |

**Role assignments**

- **Default chat** — `seamon67/GPT-OSS-Heretic:v2-120b`
- **Utility** (summarization, naming, routing) — `projectforge-swe-champion`
- **Embeddings** — `mxbai-embed-large` (HTTP lane; FastEmbed `all-MiniLM-L6-v2` fallback)
- **Auto model-routing** — ON; the prompt is classified per turn (coding / complex / simple) and the model is delegated automatically.

## Demo

A full hover-to-play tour lives on the landing page: [`docs/index.html`](docs/index.html).

## Contributing

Help is welcome. The best entry points are fresh-install testing, provider setup bugs, mobile/editor polish, docs, and small focused refactors. See [CONTRIBUTING.md](CONTRIBUTING.md) and [ROADMAP.md](ROADMAP.md).

## Security

Odysseus is a self-hosted workspace with powerful local tools. Keep auth enabled, keep private data out of Git, and do not expose raw model/service ports publicly. Deployment details are in the [setup guide](docs/setup.md#security-notes).

## Star History

<a href="https://www.star-history.com/?repos=carmodyofficial-ops%2Fmy.ai&type=date&legend=top-left">
 <picture>
   <source media="(prefers-color-scheme: dark)" srcset="https://api.star-history.com/chart?repos=carmodyofficial-ops/my.ai&type=date&theme=dark&legend=top-left" />
   <source media="(prefers-color-scheme: light)" srcset="https://api.star-history.com/chart?repos=carmodyofficial-ops/my.ai&type=date&legend=top-left" />
   <img alt="Star History Chart" src="https://api.star-history.com/chart?repos=carmodyofficial-ops/my.ai&type=date&legend=top-left" />
 </picture>
</a>

## License

AGPL-3.0-or-later -- see [LICENSE](LICENSE) and [ACKNOWLEDGMENTS.md](ACKNOWLEDGMENTS.md).
