"""Inject substantive, system-specific reference knowledge into coding turns.

Maps a coding query to relevant knowledge packs (curated allowlist), reads a
bounded excerpt of the right file, and returns a clean REFERENCE block to add as
a system message on coding turns. Read-only, fast (direct file reads — no
subprocess, no benchmark selector), fallback-safe (returns "" on any problem),
and a no-op for plain implement prompts (no noise).

Packs served:
- complete worked EXAMPLE GAMES (a full Roblox game, a full web/canvas game) for
  pattern-matching on "build a game" prompts (larger budget, highest priority);
- platform references (Roblox/Luau, web/canvas frontend);
- guard/strategy packs (debugging precision, testing in this docker setup, ...);
- authored topic references (software-eng, devops, data, AI-app);
- language-idiom packs (Python, JS/TS); infra packs (k8s, networking/security, linux).

Only authored content is read (reference.md / knowledge.md) — never the hollow
auto-generated stubs (overview.md/core_concepts.md = "Procedures to expand").
"""

from __future__ import annotations

import json
import os
from pathlib import Path

_ROOT = Path(os.environ.get("MYAI_ROOT") or ("/app" if Path("/app").exists() else "/home/youruser/odysseus"))
_PACKS = _ROOT / "data/knowledge_packs"

_DEFAULT_PACK_CHARS = 1400
_MAX_TOTAL_CHARS = 6000

# Curated allowlist. Order = priority (first matches fill the budget first). Each
# entry: id, display title, the file(s) to read (first existing wins), optional
# per-pack char budget, and trigger substrings (matched against the lowered query).
_CODING_KNOWLEDGE = [
    # Complete example games — highest priority on build-a-game prompts.
    {
        "id": "roblox_example_game",
        "title": "Complete Roblox game example (Coin Collector)",
        "files": ["knowledge.md"],
        "max_chars": 4000,
        "triggers": ["build a roblox", "make a roblox", "create a roblox",
                     "roblox game", "roblox obby", "obby", "tycoon",
                     "coin collector", "simulator game", "roblox script for a"],
    },
    {
        "id": "web_example_game",
        "title": "Complete web game example (Breakout, one file)",
        "files": ["knowledge.md"],
        "max_chars": 4000,
        "triggers": ["build a web game", "make a web game", "make a game",
                     "build a game", "breakout", "platformer", "snake game",
                     "browser game", "html game", "create a game", "pong"],
    },
    # Creative coding (p5.js / Canvas / generative art). Re-scoped 2026-07-08
    # from generic "creative problem-solving" to generative art — the old
    # catch-all triggers ("design", "how should", "approach") injected art
    # content into ordinary design questions, so they went too.
    {
        "id": "creative_coding",
        "title": "Creative coding (p5.js/Canvas/generative art)",
        "files": ["knowledge.md"],
        "max_chars": 2000,
        "triggers": ["p5.js", "p5js", "creative coding", "generative art",
                     "perlin noise", "flow field", "particle system",
                     "canvas 2d", "processing sketch", "createcanvas",
                     "fragment shader", "glsl", "colormode", "hsb color",
                     "creategraphics", "blendmode", "generative"],
    },
    # Platform references (specific mechanics).
    {
        "id": "roblox_luau_game_dev",
        "title": "Roblox / Luau game development",
        "files": ["knowledge.md"],
        "max_chars": 4200,
        "triggers": ["roblox", "luau", "datastore", "remoteevent", "remote event",
                     "localscript", "modulescript", "leaderstats", "humanoid",
                     "starterplayer", "serverscriptservice", "replicatedstorage",
                     "game pass", "lua game", "studio"],
    },
    {
        "id": "web_frontend_game_dev",
        "title": "Web game (HTML5 canvas)",
        "files": ["knowledge.md"],
        "max_chars": 2600,
        "triggers": ["web game", "canvas", "html5", "game loop", "requestanimationframe",
                     "sprite", "spritesheet", "phaser", "pixijs", "object pool"],
    },
    # High-frequency guard packs.
    {
        "id": "terminal_debugging_precision_guard",
        "title": "Terminal debugging precision (this environment)",
        "files": ["knowledge.md"],
        "triggers": ["debug", "bug", "error", "traceback", "exception", "fails",
                     "failing", "broken", "crash", "stack trace", "not working",
                     "returns none", "exit code", "stderr", "http 5", "http 4",
                     "diagnose", "why does", "why is"],
    },
    {
        "id": "testing_strategy_and_regression_design",
        "title": "Testing & regression design (docker/mounted-host)",
        "files": ["knowledge.md"],
        "triggers": ["test", "tests", "pytest", "unit test", "regression",
                     "coverage", "assert", "verify", "validation", "smoke", "tdd"],
    },
    # Language idioms.
    {
        "id": "python_idioms",
        "title": "Python idioms & gotchas",
        "files": ["reference.md"],
        "max_chars": 1900,
        "triggers": ["python", "pythonic", ".py", "django", "flask", "fastapi",
                     "pandas", "numpy", "pip install", "dataclass", "asyncio"],
    },
    {
        "id": "javascript_typescript_idioms",
        "title": "JavaScript / TypeScript idioms & gotchas",
        "files": ["reference.md"],
        "max_chars": 1900,
        "triggers": ["javascript", "typescript", ".js", ".ts", "node", "react",
                     "vue", "npm ", "async/await", "promise", "es6", "jsx"],
    },
    # More language idioms (Wave A capability build).
    {"id": "go_idioms", "title": "Go idioms & gotchas", "files": ["knowledge.md"], "max_chars": 2400,
     "triggers": ["golang", "goroutine", "go routine", ".go", "go func", "go module", "go program", "go code"]},
    {"id": "rust_idioms", "title": "Rust idioms & gotchas", "files": ["knowledge.md"], "max_chars": 2400,
     "triggers": ["rust", "cargo", "borrow checker", "rustc", ".rs", "tokio", "ownership", "lifetime"]},
    {"id": "java_kotlin_idioms", "title": "Java / Kotlin idioms & gotchas", "files": ["knowledge.md"], "max_chars": 2400,
     "triggers": ["java", "kotlin", "jvm", ".java", ".kt", "spring boot", "gradle", "maven", "android"]},
    {"id": "c_cpp_idioms", "title": "C / C++ idioms & gotchas", "files": ["knowledge.md"], "max_chars": 2400,
     "triggers": ["c++", "cpp", ".cpp", ".hpp", "std::", "stl", "smart pointer", "unique_ptr", "raii", "malloc", "segfault"]},
    {"id": "csharp_dotnet_idioms", "title": "C# / .NET idioms & gotchas", "files": ["knowledge.md"], "max_chars": 2400,
     "triggers": ["c#", "csharp", ".net", "dotnet", ".cs", "linq", "asp.net", "nuget", "blazor"]},
    {"id": "sql_deep", "title": "Advanced SQL (windows / CTEs / query plans)", "files": ["knowledge.md"], "max_chars": 2400,
     "triggers": ["window function", "cte", "recursive query", "query optimization", "explain analyze", "upsert", "query plan", "sql join", "advanced sql"]},
    {"id": "bash_scripting_deep", "title": "Robust Bash scripting", "files": ["knowledge.md"], "max_chars": 2400,
     "triggers": ["bash script", "shell script", "pipefail", "getopts", "parameter expansion", "shellcheck", "here-doc", "bash function"]},
    # Core CS topics (Wave A capability build).
    {"id": "git_version_control", "title": "Git / version control", "files": ["knowledge.md"], "max_chars": 2600,
     "triggers": ["git", "rebase", "merge conflict", "git commit", "cherry-pick", "git reset", "git stash", "reflog", "git bisect", "version control", "undo commit"]},
    {"id": "api_design", "title": "API design (REST / GraphQL)", "files": ["knowledge.md"], "max_chars": 2200,
     "triggers": ["api design", "rest api", "endpoint", "graphql", "http api", "openapi", "api versioning", "pagination", "idempotency key"]},
    {"id": "data_structures_and_algorithms", "title": "Data structures & algorithms", "files": ["knowledge.md"], "max_chars": 2200,
     "triggers": ["algorithm", "data structure", "big-o", "big o", "time complexity", "hashmap", "linked list", "binary search", "dynamic programming", "bfs", "dfs", "heap", "sorting", "leetcode"]},
    {"id": "concurrency_and_async", "title": "Concurrency & async", "files": ["knowledge.md"], "max_chars": 2200,
     "triggers": ["concurrency", "concurrent", "async", "mutex", "deadlock", "race condition", "thread pool", "parallel", "semaphore", "atomic"]},
    {"id": "regex", "title": "Regular expressions", "files": ["knowledge.md"], "max_chars": 2200,
     "triggers": ["regex", "regular expression", "regexp", "pattern match", "re.compile", "re.match", "re.sub", "lookahead", "capture group"]},
    {"id": "performance_optimization", "title": "Performance optimization", "files": ["knowledge.md"], "max_chars": 2000,
     "triggers": ["performance", "optimize", "optimization", "slow code", "speed up", "profiling", "bottleneck", "make it faster", "too slow"]},
    {"id": "system_design_patterns", "title": "Design patterns & architecture", "files": ["knowledge.md"], "max_chars": 2200,
     "triggers": ["design pattern", "solid", "factory pattern", "strategy pattern", "observer pattern", "decorator pattern", "system design", "microservice", "cqrs", "hexagonal", "architecture pattern"]},
    {"id": "secure_coding", "title": "Secure coding (OWASP for devs)", "files": ["knowledge.md"], "max_chars": 2200,
     "triggers": ["secure coding", "security vulnerability", "sql injection", "xss", "csrf", "ssrf", "owasp", "sanitize input", "idor", "path traversal", "secure"]},
    # General-purpose (Wave B) — broadly useful on coding turns too.
    {"id": "writing_and_communication", "title": "Technical writing & communication", "files": ["knowledge.md"], "max_chars": 2000,
     "triggers": ["documentation", "readme", "commit message", "pr description", "code comment", "docstring", "write docs", "technical writing", "write a comment", "write up"]},
    {"id": "research_methods", "title": "Investigation & research methods", "files": ["knowledge.md"], "max_chars": 2000,
     "triggers": ["research", "investigate", "investigation", "look into", "evaluate options", "compare options", "due diligence", "find out which"]},
    {"id": "reasoning_and_learning", "title": "Structured reasoning & rapid learning", "files": ["knowledge.md"], "max_chars": 2000,
     "triggers": ["first principles", "think through", "reason about", "break down the problem", "trade-off analysis", "how should i approach", "decision framework", "learn a new"]},
    {"id": "product_management", "title": "Product management (request -> spec)", "files": ["knowledge.md"], "max_chars": 2000,
     "triggers": ["requirements", "user story", "acceptance criteria", "scope the", "mvp", "prioritize", "feature spec", "product requirements", "prd"]},
    # Frameworks (Wave A tail).
    {"id": "react_nextjs", "title": "React + Next.js", "files": ["knowledge.md"], "max_chars": 2400,
     "triggers": ["react", "next.js", "nextjs", "jsx", "tsx", "usestate", "useeffect", "use client", "server component", "app router", "react hook"]},
    {"id": "fastapi_django", "title": "FastAPI + Django", "files": ["knowledge.md"], "max_chars": 2400,
     "triggers": ["fastapi", "django", "pydantic", "queryset", "@app.get", "drf", "uvicorn", "makemigrations", "select_related", "response_model"]},
    {"id": "node_express", "title": "Node.js + Express", "files": ["knowledge.md"], "max_chars": 2400,
     "triggers": ["express", "node.js", "nodejs", "middleware", "req.body", "res.json", "worker_threads", "express route", "next(err)"]},
    {"id": "web_frontend", "title": "Web frontend (HTML/CSS/DOM)", "files": ["knowledge.md"], "max_chars": 2400,
     "triggers": ["css", "flexbox", "css grid", "dom ", "queryselector", "addeventlistener", "semantic html", "accessibility", "aria", "localstorage", "event delegation", "fetch api"]},
    # Distilled from official docs (license-verified — see each pack's manifest.json).
    {"id": "docker", "title": "Docker & containers", "files": ["knowledge.md"], "max_chars": 2600,
     # "container" alone matched CSS/DOM queries ("grid item overflows its
     # container") and displaced the CSS pack from the budget — scope it.
     "triggers": ["docker", "dockerfile", "containerize", "container image", "docker compose", "docker run", "multi-stage", ".dockerignore", "entrypoint", "docker image"]},
    {"id": "typescript", "title": "TypeScript (types/generics/narrowing)", "files": ["knowledge.md"], "max_chars": 2600,
     "triggers": ["typescript", "tsconfig", "type annotation", "interface vs type", "generic type", "utility type", "discriminated union", "type narrowing", ".d.ts", "tsc"]},
    {"id": "pandas_numpy", "title": "pandas + NumPy (data science)", "files": ["knowledge.md"], "max_chars": 2600,
     "triggers": ["pandas", "numpy", "dataframe", "ndarray", "groupby", ".loc", ".iloc", "vectorize", "broadcasting", "read_csv", "data science"]},
    {"id": "github_actions", "title": "GitHub Actions (CI/CD)", "files": ["knowledge.md"], "max_chars": 2600,
     "triggers": ["github actions", "ci/cd", "ci cd", "workflow yml", ".github/workflows", "continuous integration", "runs-on", "actions/checkout", "pipeline yaml"]},
    {"id": "postgresql", "title": "PostgreSQL specifics", "files": ["knowledge.md"], "max_chars": 2600,
     "triggers": ["postgresql", "postgres", "psql", "jsonb", "timestamptz", "on conflict", "pg_stat", "pgbouncer", "explain analyze"]},
    {"id": "tailwindcss", "title": "Tailwind CSS", "files": ["knowledge.md"], "max_chars": 2600,
     "triggers": ["tailwind", "tailwindcss", "utility-first", "@apply", "tailwind.config", "tailwind class"]},
    {"id": "svelte", "title": "Svelte (runes + classic)", "files": ["knowledge.md"], "max_chars": 2600,
     "triggers": ["svelte", "sveltekit", "$state", "svelte runes", "reactive declaration", ".svelte", "writable store"]},
    {"id": "vite", "title": "Vite (build tool)", "files": ["knowledge.md"], "max_chars": 2400,
     "triggers": ["vite", "vite.config", "import.meta.env", "vitejs", "vite plugin", "vite dev server"]},
    {"id": "fastapi", "title": "FastAPI (Python web)", "files": ["knowledge.md"], "max_chars": 2600,
     "triggers": ["fastapi", "@app.get", "pydantic", "response_model", "apirouter", "httpexception", "uvicorn", "oauth2passwordbearer"]},
    # Algorithmic / bot trading (Freqtrade framework cloned at ~/algo-trading/freqtrade).
    {"id": "algorithmic_trading_bots", "title": "Algorithmic trading bots", "files": ["knowledge.md"], "max_chars": 3400,
     "triggers": ["trading bot", "algo trading", "algorithmic trading", "trading strategy", "position sizing", "stop loss", "market making", "mean reversion", "momentum strategy", "crypto bot", "trading signal", "kelly criterion", "trading risk management"]},
    {"id": "freqtrade", "title": "Freqtrade (trading bot framework)", "files": ["knowledge.md"], "max_chars": 3400,
     "triggers": ["freqtrade", "populate_indicators", "populate_entry_trend", "istrategy", "hyperopt", "trading bot framework", "freqtrade strategy", "dry-run trade"]},
    {"id": "backtesting_and_strategy_validation", "title": "Backtesting & strategy validation", "files": ["knowledge.md"], "max_chars": 3000,
     "triggers": ["backtest", "backtesting", "walk-forward", "sharpe ratio", "out-of-sample", "overfitting strategy", "strategy validation", "max drawdown", "monte carlo backtest", "look-ahead bias"]},
    {"id": "crypto_market_structure", "title": "Crypto market structure & microstructure", "files": ["knowledge.md"], "max_chars": 3600,
     "triggers": ["funding rate", "perpetual futures", "perps", "liquidation", "order book", "market structure", "crypto market", "stablecoin", "basis trade", "maker taker", "slippage", "depeg"]},
    {"id": "crypto_trading_edges", "title": "Where real edges exist in crypto trading", "files": ["knowledge.md"], "max_chars": 3700,
     "triggers": ["trading edge", "market neutral", "funding arbitrage", "is this profitable", "trading alpha", "cash and carry", "statistical arbitrage", "long-biased", "what is the edge", "profitable trading"]},
    {"id": "trend_following_and_momentum", "title": "Trend-following & momentum", "files": ["knowledge.md"], "max_chars": 3700,
     "triggers": ["trend following", "momentum strategy", "time-series momentum", "trailing stop", "chandelier exit", "donchian", "regime filter", "let winners run", "vol targeting", "managed futures"]},
    {"id": "godot_unity", "title": "Godot + Unity game dev", "files": ["knowledge.md"], "max_chars": 2400,
     "triggers": ["godot", "unity", "gdscript", "monobehaviour", "gameobject", "_process", "fixedupdate", "prefab", "game engine", "node2d", "coroutine"]},
    # Authored topic references.
    {
        "id": "software_engineering",
        "title": "Software engineering reference",
        "files": ["reference.md"],
        "triggers": ["refactor", "refactoring", "design", "architecture",
                     "api design", "function design", "error handling", "naming",
                     "abstraction", "tech debt", "clean code", "best practice",
                     "code review", "review the"],
    },
    {
        "id": "devops_and_infrastructure",
        "title": "DevOps & infrastructure",
        "files": ["reference.md"],
        # "container" alone matched CSS/DOM queries — scope it (see docker entry).
        "triggers": ["docker", "dockerfile", "compose", "containerize", "container image",
                     "deploy", "ci ", "pipeline", "shell script", "bash script", "nginx",
                     "healthcheck", "build image"],
    },
    {
        "id": "data_and_databases",
        "title": "Data & databases",
        "files": ["reference.md"],
        "triggers": ["sql", "database", "sqlite", "postgres", "query", "schema",
                     "migration", "sqlalchemy", " orm", "index", "table", "join",
                     "select ", "insert "],
    },
    {
        "id": "ai_engineering",
        "title": "LLM app engineering",
        "files": ["reference.md"],
        "triggers": ["llm", "openai", "embedding", "rag", "vector", "prompt",
                     "tool calling", "function calling", "agent loop", "streaming",
                     "chat completion", "model api", "anthropic"],
    },
    # Infra references.
    {
        "id": "kubernetes_and_cloud_native",
        "title": "Kubernetes & cloud-native",
        "files": ["reference.md"],
        "triggers": ["kubernetes", "k8s", "kubectl", "pod", "deployment yaml",
                     "helm", "cluster", "ingress", "statefulset"],
    },
    {
        "id": "networking_and_security",
        "title": "Networking & security",
        "files": ["reference.md"],
        "triggers": ["dns", "tls", "ssl", "firewall", "port-forward", "port forward",
                     "cors", "xss", "csrf", "ssrf", "sql injection", "security review",
                     "vulnerab", "tcp", "socket", "reverse proxy"],
    },
    {
        "id": "linux_os_operations",
        "title": "Linux / shell operations",
        "files": ["reference.md"],
        "triggers": ["linux", "chmod", "systemd", "permission denied", "ssh ",
                     "cron", "ubuntu", "bash script", "shell command", "journalctl",
                     "file permission", "kill -9"],
    },
    # Domain reference — VA disability compensation (38 CFR Parts 3-4 / VA.gov, public domain).
    {"id": "va_disability_compensation", "title": "VA disability compensation (ratings & framework)",
     "files": ["knowledge.md"], "max_chars": 4600,
     "triggers": ["va disability", "disability compensation", "va compensation",
                  "service connected", "service connection", "service-connected",
                  "va rating", "disability rating", "rating percentage", "vasrd",
                  "38 cfr part 4", "c&p exam", "diagnostic code", "combined rating",
                  "bilateral factor", "tdiu", "individual unemployability",
                  "ptsd rating", "tinnitus rating", "sleep apnea rating",
                  "migraine rating", "back rating", "veterans affairs disability",
                  "100% va", "p&t rating"]},
    {"id": "va_benefits_and_claims", "title": "VA benefits & claims (health/education/loan/pension/appeals)",
     "files": ["knowledge.md"], "max_chars": 5000,
     "triggers": ["va benefits", "gi bill", "post-9/11 gi bill", "montgomery gi bill",
                  "va home loan", "certificate of eligibility", "va pension",
                  "aid and attendance", "champva", "vr&e", "chapter 31", "chapter 33",
                  "chapter 35", "va health care", "va healthcare", "pact act",
                  "va claim", "file a va claim", "intent to file", "va appeal",
                  "higher-level review", "supplemental claim", "board appeal",
                  "notice of disagreement", "burial benefits", "survivor benefits",
                  "yellow ribbon", "veteran readiness", "dic"]},
    # Lower-priority guards.
    {
        "id": "engineering_quality_bar",
        "title": "Engineering quality bar",
        "files": ["knowledge.md"],
        "triggers": ["quality", "diff review", "before commit", "acceptance",
                     "claim success", "is it done", "production ready"],
    },
    {
        "id": "projectforge_safe_coding_workflow",
        "title": "Safe local coding/patch workflow",
        "files": ["knowledge.md"],
        "triggers": ["patch", "apply patch", "commit", "dev mirror", "destructive",
                     "rewrite", "rollback", "backup", "safe workflow"],
    },
]


# --- registry/manifest discovery lane (the revived pack router) -------------
# The original registry-driven pack router lived in src/intelligence_runtime.py,
# which was deleted (898 lines of dormant code) — leaving every non-allowlisted
# pack unreachable on a chat turn. This lane restores routing on the LIVE
# retriever: it auto-includes any pack that has a SUBSTANTIVE served file, routing
# on the pack manifest's own `triggers` (+ the shared semantic lane). It is
# manifest-driven, so a new domain pack serves as soon as it has content + triggers
# — no code change. Quality- and safety-gated:
#   * hollow auto-generated stubs are skipped (content gate), so a pack only serves
#     once it has real content;
#   * guard/policy/contract packs and system/governance/security packs are NEVER
#     auto-served — they hold internal security details (privilege model, the guest
#     password, abstention contracts) that must not leak into a user's chat context.
# Curated allowlist entries keep priority (discovered are appended after them).
_HOLLOW_MARKERS = ("to expand", "procedures to expand", "procedure for testing",
                   "practical playbook 1")
# Substrings in a pack id that mark it as a guard/policy/governance contract.
_DISCOVERY_SKIP_SUBSTR = ("guard", "policy", "_contract", "abstention", "protocol",
                          "k2t_", "k2r_", "rubric",
                          # internal system/ops pack families (see skip-ids below)
                          "system_architecture", "runbook")
# Packs never auto-served: system self-awareness + security/auth internals + meta.
_DISCOVERY_SKIP_IDS = {
    "skills_and_tools", "projectforge_sme", "my_ai_system_core",
    "auth_and_guest_access_model", "tool_and_agent_safety",
    "myai_system_architecture_runtime_brief", "testing_regression",
    "product_experience_and_ui_standards",
    # Internal system/ops packs: host paths, model roster, auth/session file
    # locations, LAN URLs, admin runbooks. Must not reach a user's chat context.
    "odysseus_system_architecture", "ops_runbook_and_incident_response",
}
_DISC_CACHE: dict = {"sig": None, "entries": None}


def _is_hollow(text: str) -> bool:
    low = text.lower()
    return len(text.strip()) < 600 or any(m in low for m in _HOLLOW_MARKERS)


def _discovered_entries() -> list[dict]:
    """Allowlist-shaped entries for substantive, non-guard, non-curated packs,
    discovered from the pack dirs + their manifests. Cached by a signature over
    each pack's manifest/knowledge/reference mtimes. Fail-safe: [] on any problem."""
    try:
        curated = {e["id"] for e in _CODING_KNOWLEDGE}
        dirs = sorted(p for p in _PACKS.iterdir() if p.is_dir())

        def _mt(f: Path) -> float:
            try:
                return f.stat().st_mtime
            except OSError:
                return 0.0

        # Signature covers the routed FILES (manifest triggers, served content),
        # not just the dir mtime — on POSIX editing a file does not touch the
        # parent dir's mtime, so a dir-only signature went stale on content edits.
        sig = tuple(
            (p.name,) + tuple(_mt(p / n) for n in ("manifest.json", "knowledge.md", "reference.md"))
            for p in dirs
        )
        if _DISC_CACHE.get("sig") == sig and _DISC_CACHE.get("entries") is not None:
            return _DISC_CACHE["entries"]
        out: list[dict] = []
        for d in dirs:
            pid = d.name
            if pid in curated or pid in _DISCOVERY_SKIP_IDS:
                continue
            if any(s in pid for s in _DISCOVERY_SKIP_SUBSTR):
                continue
            served, text = None, ""
            for name in ("knowledge.md", "reference.md"):
                f = d / name
                try:
                    if f.exists():
                        t = f.read_text(encoding="utf-8", errors="replace").strip()
                        if t and not _is_hollow(t):
                            served, text = name, t
                            break
                except Exception:
                    continue
            if not served:
                continue
            man = {}
            try:
                mf = d / "manifest.json"
                if mf.exists():
                    man = json.loads(mf.read_text(encoding="utf-8", errors="replace"))
            except Exception:
                man = {}
            triggers = [str(t).lower() for t in (man.get("triggers") or []) if str(t).strip()]
            title = man.get("title") or man.get("name") or pid.replace("_", " ").title()
            out.append({
                "id": pid, "title": str(title),
                "files": [served],
                "max_chars": min(len(text), _DEFAULT_PACK_CHARS + 800),
                "triggers": triggers, "_discovered": True,
            })
        _DISC_CACHE.update(sig=sig, entries=out)
        return out
    except Exception:
        return []


def _all_entries() -> list[dict]:
    """Curated allowlist first (keeps priority), then discovered registry packs."""
    return _CODING_KNOWLEDGE + _discovered_entries()


def _trigger_hit(trigger: str, q: str) -> bool:
    """Word-boundary-aware substring match. A trigger that starts/ends with an
    alphanumeric must sit on a word boundary there, so "obby" no longer fires on
    "lobby"/"hobby" while ".py", "kill -9", and phrases still match naturally."""
    t = trigger.strip()
    if not t:
        return False
    n = len(t)
    i = q.find(t)
    while i >= 0:
        before = q[i - 1] if i > 0 else " "
        after = q[i + n] if i + n < len(q) else " "
        left_ok = (not t[0].isalnum()) or (not before.isalnum())
        right_ok = (not t[-1].isalnum()) or (not after.isalnum())
        if left_ok and right_ok:
            return True
        i = q.find(t, i + 1)
    return False


# Semantic recall lane (additive to the substring triggers). Triggers are precise
# but miss paraphrases ("make my code less repetitive" never hits the creative pack);
# a high-threshold cosine surfaces those without hurting trigger precision.
_PACK_VEC_CACHE: dict = {"key": None, "matrix": None, "ids": None}
_SEM_PACK_THRESHOLD = 0.40  # FastEmbed cosines run low; tuned so clear paraphrases
                            # (~0.42+) surface while generic coding queries (~0.24) stay clean


def _pack_semantic_sims(query: str, entries: list[dict]) -> dict:
    """{pack_id: cosine} for the query, or {} if embeddings unavailable. Packs are
    embedded by title+triggers (cached); the query per call. Reuses the skills
    module's cached embedding client so there's a single client process-wide."""
    try:
        from services.memory.skills import _get_embed_client
        client = _get_embed_client()
        if client is None or not (query or "").strip():
            return {}
        texts = [
            f"{e['title']} {' '.join(e['triggers'])} "
            f"{_read_pack(e['id'], e.get('files') or ['knowledge.md', 'reference.md'])[:400]}"
            for e in entries
        ]
        key = hash(tuple(texts))
        if _PACK_VEC_CACHE.get("key") != key:
            _PACK_VEC_CACHE.update(key=key, matrix=client.encode(texts),
                                   ids=[e["id"] for e in entries])
        mat = _PACK_VEC_CACHE.get("matrix")
        if mat is None or getattr(mat, "size", 0) == 0:
            return {}
        qv = client.encode([query])
        if getattr(qv, "size", 0) == 0:
            return {}
        sims = mat @ qv[0]
        return {i: float(v) for i, v in zip(_PACK_VEC_CACHE["ids"], sims)}
    except Exception:
        return {}


def _read_pack(pack_id: str, files: list[str]) -> str:
    base = _PACKS / pack_id
    for name in files:
        p = base / name
        try:
            if p.exists():
                text = p.read_text(encoding="utf-8", errors="replace").strip()
                if text:
                    return text
        except Exception:
            continue
    return ""


def coding_knowledge_block(query: str, *, max_total_chars: int = _MAX_TOTAL_CHARS) -> str:
    """Bounded REFERENCE block for a coding query, or '' when nothing relevant matches."""
    try:
        q = " ".join(str(query or "").lower().split())
        if not q:
            return ""
        parts: list[str] = []
        total = 0
        _entries = _all_entries()  # curated allowlist + revived registry-discovery lane
        _sems = _pack_semantic_sims(q, _entries)  # {} when embeddings unavailable
        # Score every candidate by RELEVANCE, then fill the budget most-relevant
        # first — so a specific pack (e.g. fastapi_django on a FastAPI query) is
        # never crowded out by a generic one that happens to sit earlier in the
        # list. Each trigger hit outweighs the max semantic cosine (1.0); list
        # index is a stable tiebreaker that preserves curated order within ties.
        _scored = []
        for _idx, entry in enumerate(_entries):
            _hits = sum(1 for t in entry["triggers"] if _trigger_hit(t, q))
            _sem = _sems.get(entry["id"], 0.0)
            if _hits == 0 and _sem < _SEM_PACK_THRESHOLD:
                continue
            _scored.append((_hits * 2.0 + _sem, _idx, entry))
        _scored.sort(key=lambda x: (-x[0], x[1]))
        for _score, _idx, entry in _scored:
            text = _read_pack(entry["id"], entry.get("files") or ["knowledge.md", "reference.md", "overview.md"])
            if not text:
                continue
            cap = int(entry.get("max_chars") or _DEFAULT_PACK_CHARS)
            chunk = f"### {entry['title']}\n{text[:cap].rstrip()}"
            if parts and total + len(chunk) > max_total_chars:
                continue  # this pack won't fit, but a smaller later one still might
            parts.append(chunk)
            total += len(chunk)
            if total >= max_total_chars:
                break
        if not parts:
            return ""
        return (
            "REFERENCE KNOWLEDGE — local playbooks/examples for THIS environment. Consult "
            "them for technique, patterns, and pitfalls; do not quote verbatim, and the "
            "operator's request still governs.\n\n" + "\n\n".join(parts)
        )
    except Exception:
        return ""


def coding_knowledge_message(query: str, max_total_chars: int | None = None) -> dict | None:
    """A system message carrying the reference block, or None if nothing matched.

    ``max_total_chars`` overrides the default pack budget — the caller scales it
    down for small-context models so scaffold doesn't crowd out the request."""
    block = coding_knowledge_block(
        query, max_total_chars=int(max_total_chars or _MAX_TOTAL_CHARS))
    return {"role": "system", "content": block} if block else None
