"""Auto-delegate the chat model from the prompt — precise + conversation-aware.

Picks the per-turn LOCAL model by categorizing the message:
  coding   -> coding model  (the most capable coder that loads on the host)
  complex  -> big model     (the 120B gpt-oss)   [also: any agent-mode turn]
  simple   -> small model   (gpt-oss:20b)
Defaults live in src/settings.py (auto_model_coding / _complex / _simple).

Coding covers not just "write me code" but command-line / ops requests — "give
me a command to mount this drive", "how do I install X" — so terminal answers
come from the strongest coder and inherit the copy-paste command formatting.

Precision comes from three layers, fast-path first — clear prompts are instant and
only genuinely ambiguous ones pay for more:
  1. Confidence-scored heuristic with WORD-BOUNDARY matching (so "api" never matches
     "capital"). Clear cases decided immediately.
  2. Conversation STICKINESS. A coding thread stays on the coding model for short
     follow-ups ("now add error handling", "make it faster"), so it never flip-flops.
  3. LLM tie-breaker. Only for prompts the heuristic is unsure about: a one-word
     classification from the small model. Gated + bounded; falls back to the heuristic.

The 'agent vs chat' MODE is unchanged. Fail-safe: returns the current model on doubt.
"""
from __future__ import annotations

import re

_LOCAL_HINTS = ("localhost", "127.0.0.1", "host.docker.internal", "0.0.0.0", ":11434")

# --- signal vocabularies -----------------------------------------------------
# Word-based keywords are matched on WORD BOUNDARIES (prevents "api" in "capital",
# "go" in "good", "let" in "wallet", etc.). Symbol/phrase signs use substring.
_FENCE = re.compile(r"```|~~~")
_FILE_EXT = re.compile(r"\.(py|js|ts|tsx|jsx|go|rs|java|kt|c|cc|cpp|h|hpp|cs|rb|php|sql|sh|bash|"
                       r"html|css|scss|vue|svelte|json|ya?ml|toml|tf|lua|dockerfile)\b")
# Symbolic / unambiguously-code substrings (no bare English words here).
_SIGNS = ("=>", "();", "()", "{}", "[]", "==", "!=", "->", "::", "&&", "||", "</", "/>",
          "console.log", "print(", "@app.", "self.", "<div", "def ", "fn main",
          "traceback", "stacktrace", "pip install", "npm install", "git commit", "create table")
_SPECIAL_LANGS = ("c++", "c#", ".net", "node.js", "next.js")  # special chars -> substring

_CODE_ACTIONS = ("write", "create", "build", "make", "implement", "fix", "debug", "refactor",
                 "generate", "optimize", "convert", "parse", "configure", "rewrite", "deploy")
_CODE_NOUNS = ("function", "class", "method", "script", "code", "api", "endpoint", "component",
               "module", "regex", "algorithm", "snippet", "query", "loop", "array", "variable",
               "struct", "interface", "compiler", "dockerfile", "bug", "exception", "schema",
               "migration", "syntax", "parser", "decorator", "stack trace", "unit test")
_TOOLS = ("git", "docker", "kubectl", "kubernetes", "npm", "pip", "sql", "bash", "terraform",
          "apt", "apt-get", "brew", "yum", "dnf", "pacman", "systemctl", "systemd", "ssh", "scp",
          "curl", "wget", "crontab", "cron", "ollama", "conda", "cargo", "rsync", "vllm",
          "fstab", "blkid", "lsblk", "nvidia-smi")
# Bare language names only — common-English words (go/node/react/express) are
# excluded; they're caught via file extensions, special langs, or the LLM tie-breaker.
_LANGS = ("python", "javascript", "typescript", "golang", "rust", "java", "kotlin",
          "fastapi", "django", "svelte", "tailwind", "postgres", "numpy", "pytorch")
_COMPLEX = ("explain", "analyze", "compare", "design", "architect", "reason", "prove",
            "derive", "step by step", "in detail", "trade-off", "tradeoff", "pros and cons",
            "strategy", "evaluate", "essay", "research", "philosophy", "implication",
            "framework", "comprehensive", "critique", "walk me through", "deep dive",
            "elaborate", "theory", "ethics", "why does", "how does", "how do")
_FOLLOWUP = re.compile(
    r"^\s*(now|also|then|next|and\b|but\b|ok\b|okay\b|make it|add\b|fix\b|change|update|"
    r"remove|instead|continue|keep going|shorter|longer|simplify|the (error|bug|issue|test)|"
    r"can you (also|now)|do that|try (that|again))", re.I)

# Command-line / ops intent. A request for something to paste into a terminal is
# a coding request: it routes to the coding model so shell/ops answers come from
# the strongest coder AND inherit the copy-paste command formatting. Sysadmin
# verbs kept tight (common English like "run"/"start" excluded → they'd over-fire;
# they fall through to the low-confidence tie-breaker instead).
_OPS_ACTIONS = ("install", "uninstall", "reinstall", "mount", "unmount", "setup",
                "enable", "disable", "restart", "reboot", "compile", "chmod", "chown",
                "symlink", "provision", "partition", "quantize")
_CMD_NOUNS = ("command", "commands", "terminal", "shell", "cli", "one-liner", "oneliner",
              "code block", "codeblock")
# Explicit "give me a command to X" / "in my terminal" / "cli" — strong coding.
_CMD_REQUEST = re.compile(
    r"\b(command|one[-\s]?liner|code\s?block|script|snippet)\b[^.?!]{0,40}\b(to|for|that|which|i can)\b"
    r"|\b(give|write|show|need|want|get)\b[^.?!]{0,30}\b(command|one[-\s]?liner|code\s?block|script|snippet)\b"
    r"|\b(in|into|from|to|on)\s+(the\s+|my\s+|your\s+)?terminal\b"
    r"|\b(cli|command[-\s]?line)\b")
# "how do I <thing>" is a TASK; "how does X work" (complex) is handled elsewhere.
_HOWTO = re.compile(r"\bhow\s+(do|can|would|could|should)\s+i\b|\bhow\s+to\b")


def _wb(words):
    return re.compile(r"\b(" + "|".join(re.escape(w) for w in words) + r")\b")


_RE_ACTIONS = _wb(_CODE_ACTIONS)
_RE_NOUNS = _wb(_CODE_NOUNS)
_RE_TOOLS = _wb(_TOOLS)
_RE_LANGS = _wb(_LANGS)
_RE_OPS = _wb(_OPS_ACTIONS)
_RE_CMD_NOUNS = _wb(_CMD_NOUNS)
_RE_COMPLEX = re.compile("|".join(re.escape(c) for c in _COMPLEX))  # phrases ok as substr


def _code_score(text: str) -> int:
    if _FENCE.search(text):
        return 5
    if _FILE_EXT.search(text):
        return 4
    signs = min(3, sum(1 for s in _SIGNS if s in text))
    tool = bool(_RE_TOOLS.search(text))
    lang = bool(_RE_LANGS.search(text)) or any(s in text for s in _SPECIAL_LANGS) or tool
    noun = bool(_RE_NOUNS.search(text))
    act = bool(_RE_ACTIONS.search(text))
    ops = bool(_RE_OPS.search(text))
    cmd_noun = bool(_RE_CMD_NOUNS.search(text))
    cmd_req = bool(_CMD_REQUEST.search(text))
    howto = bool(_HOWTO.search(text))
    score = signs
    if noun:
        score += 1
    if act and noun:
        score += 1          # "write a function", "fix the bug"
    if lang:
        score += 1          # a bare language alone is weak (-> low conf / tie-breaker)
        if noun or act or signs:
            score += 1       # language IN a coding context = strong
    # Command-line / ops intent -> the user wants runnable terminal output.
    if cmd_req:
        score += 4          # explicit: "give me a command to ...", "in my terminal", "cli"
    else:
        if cmd_noun:
            score += 1
        if ops:
            score += 1
        if cmd_noun and (ops or tool or act):
            score += 2       # "command to install X", "terminal ... systemctl"
    # "how do I <tech>" is a task (coding); "how does X work" stays complex, so
    # only boost when a concrete tech signal is also present.
    if howto and (ops or cmd_noun or lang):
        score += 2
    return score


def _complex_score(text: str, words: int) -> int:
    score = 0
    if words >= 60:
        score += 2
    elif words >= 28:
        score += 1
    score += min(3, len(_RE_COMPLEX.findall(text)))
    if text.count("?") >= 2:
        score += 1
    return score


def classify_heuristic(message: str, *, chat_mode: str = "chat") -> tuple[str, str]:
    """Return (category, confidence): coding|complex|simple x high|med|low."""
    text = (message or "").lower()
    words = len((message or "").split())
    if not text.strip():
        return ("complex", "high")
    cs = _code_score(text)
    xs = _complex_score(text, words)
    if cs >= 4:
        return ("coding", "high")
    if chat_mode == "agent":
        return ("complex", "high")
    if xs >= 3:
        return ("complex", "high")
    if cs >= 2 and cs >= xs:
        return ("coding", "med")
    if xs >= 2:
        return ("complex", "med")
    if cs == 0 and xs == 0 and words <= 8:
        return ("simple", "high")
    if cs >= 1:
        return ("coding", "low")
    if xs >= 1:
        return ("complex", "low")
    return ("simple", "low")


def _is_followup(text: str, words: int) -> bool:
    return words <= 14 and bool(_FOLLOWUP.search(text))


def _msg_text(m) -> str:
    if isinstance(m, dict):
        return str(m.get("content") or "")
    return str(getattr(m, "content", "") or "")


def _recent_is_coding(history, lookback: int = 4) -> bool:
    if not history:
        return False
    seen = 0
    for m in reversed(list(history)):
        c = _msg_text(m)
        if not c:
            continue
        low = c.lower()
        if _FENCE.search(low) or _code_score(low) >= 4:
            return True
        seen += 1
        if seen >= lookback:
            break
    return False


async def _llm_classify(message: str, *, endpoint_url: str, headers, model: str,
                        timeout: int = 8) -> str | None:
    sys = ("Classify the user's message for model routing. Reply with EXACTLY one word: "
           "coding, complex, or simple.\n"
           "coding = writing/reading/debugging/explaining code, software, configs, SQL, "
           "devops, regex, shell.\n"
           "complex = deep reasoning, analysis, multi-step explanation, math, philosophy, "
           "research, design, long-form writing.\n"
           "simple = short factual lookups, greetings, quick casual chat, translations.")
    try:
        from src.llm_core import llm_call_async
        out = await llm_call_async(
            endpoint_url, model,
            [{"role": "system", "content": sys},
             {"role": "user", "content": (message or "")[:1200]}],
            temperature=0.0, max_tokens=4, headers=headers or {}, timeout=timeout,
        )
        w = (out or "").strip().lower()
        for cat in ("coding", "complex", "simple"):
            if cat in w:
                return cat
    except Exception:
        pass
    return None


def _is_local(endpoint_url: str) -> bool:
    u = (endpoint_url or "").lower()
    return (not u) or any(h in u for h in _LOCAL_HINTS)


async def select_model_for_turn(message, *, chat_mode: str, current_model: str,
                                endpoint_url: str, headers=None, history=None) -> str:
    """Pick the per-turn model. Returns current_model unchanged when routing is off,
    the endpoint is external, or anything is uncertain (never raises)."""
    try:
        from src import settings
        if not settings.get_setting("auto_model_routing", True):
            return current_model
        if not _is_local(endpoint_url):
            return current_model
        # Coalesce null/blank → default: a persisted settings.json may carry these
        # keys as null (the Settings save path materializes known keys), which
        # would otherwise pass None through and fall back to current_model — i.e.
        # coding turns would silently stay on the chat/complex model.
        def _routed_model(key: str, dflt: str) -> str:
            v = settings.get_setting(key, dflt)
            v = str(v).strip() if v is not None else ""
            return v or dflt
        # Defaults mirror src/settings.py. Coding points at the strongest model
        # that loads on a single GB-10 (the 120B), NOT a small coder — see the
        # settings.py note on the Qwen3.5-397B / dual-GB-10 upgrade path.
        models = {
            "coding": _routed_model("auto_model_coding", "seamon67/GPT-OSS-Heretic:v2-120b"),
            "complex": _routed_model("auto_model_complex", "seamon67/GPT-OSS-Heretic:v2-120b"),
            "simple": _routed_model("auto_model_simple", "gpt-oss:20b"),
        }
        msg = message if isinstance(message, str) else ""
        words = len(msg.split())
        cat, conf = classify_heuristic(msg, chat_mode=chat_mode)
        # Stickiness: a short follow-up (or any non-confident, non-coding turn) inside a
        # coding thread stays on the coding model — no mid-conversation flip.
        if cat != "coding" and _recent_is_coding(history) and (conf != "high" or _is_followup(msg.lower(), words)):
            cat, conf = "coding", "high"
        # LLM tie-breaker only for genuinely ambiguous prompts.
        if conf == "low" and settings.get_setting("auto_model_routing_llm", True):
            llm_cat = await _llm_classify(msg, endpoint_url=endpoint_url, headers=headers,
                                          model=models["simple"])
            if llm_cat:
                cat = llm_cat
        return (models.get(cat) or current_model).strip() or current_model
    except Exception:
        return current_model
