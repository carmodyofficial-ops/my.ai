"""Symbol-level code navigation — find where a name is DEFINED or USED.

Without this the agent has to guess a regex ("def foo", "foo =", "class foo")
and then eat the false positives, or grep a bare name and wade through every
mention. Both cost rounds, and on a 20-round budget that is real.

Two resolution strategies, best-effort in order:
  * Python files are parsed with `ast`, so a definition is an actual
    FunctionDef/ClassDef/Assign node — exact, not a pattern guess. A syntax
    error in one file degrades to the regex path for that file only.
  * Everything else uses per-language definition patterns (JS/TS, Go, Rust,
    Kotlin/Java, shell). These are heuristics and are reported as such.

Read-only by construction: it opens files and never writes. Bounded by the same
skip-dirs / max-hits limits as grep so a common name cannot flood the context.
"""
from __future__ import annotations

import ast
import json
import os
import re
from typing import Any, Dict, List, Tuple

from src.constants import MAX_OUTPUT_CHARS

_SKIP_DIRS = frozenset({
    ".git", ".hg", ".svn", "node_modules", "venv", ".venv", "__pycache__",
    ".mypy_cache", ".pytest_cache", ".ruff_cache", "dist", "build",
    ".next", ".cache", "site-packages", ".idea", ".tox",
    # Directories that typically hold COPIES of the source. Without these a
    # symbol search returns the same definition several times from stale
    # snapshots, and the model may cite a path nobody actually edits. The
    # git-tracked path below is the better filter when .git is available; these
    # names are the fallback for when it is not.
    "mirrors", "backups", ".backups", "vendor", "third_party", "coverage",
    "htmlcov", "target", "bower_components", "Pods", ".terraform",
})
_MAX_FILES = 4000
_MAX_HITS = 100
_MAX_LINE = 400

_CODE_EXTS = (
    ".py", ".js", ".mjs", ".cjs", ".jsx", ".ts", ".tsx", ".go", ".rs",
    ".kt", ".java", ".rb", ".php", ".c", ".cc", ".cpp", ".h", ".hpp",
    ".cs", ".sh", ".bash", ".lua",
)


def _def_patterns(sym: str) -> List[Tuple[str, "re.Pattern"]]:
    """(kind, regex) pairs matching a DEFINITION of *sym* in non-Python code."""
    s = re.escape(sym)
    return [
        ("function", re.compile(rf"\bfunction\s+{s}\b")),
        ("function", re.compile(rf"\b(?:func|fn|def|sub)\s+{s}\b")),          # go/rust/ruby/perl
        ("method",   re.compile(rf"\bfun\s+{s}\b")),                           # kotlin
        ("class",    re.compile(rf"\b(?:class|interface|struct|enum|trait|type)\s+{s}\b")),
        ("const",    re.compile(rf"\b(?:const|let|var|val)\s+{s}\s*[=:]")),
        ("assign",   re.compile(rf"^\s*{s}\s*[:=][^=]")),                      # top-level binding
        ("export",   re.compile(rf"\bexport\s+(?:default\s+)?(?:async\s+)?(?:function|class|const|let|var)\s+{s}\b")),
        ("shell_fn", re.compile(rf"^\s*(?:function\s+)?{s}\s*\(\)\s*\{{")),
    ]


def _python_defs(path: str, sym: str) -> List[Dict[str, Any]]:
    """Exact definitions of *sym* in a Python file via AST. [] if unparseable."""
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            src = f.read()
        tree = ast.parse(src)
    except (OSError, SyntaxError, ValueError):
        return []
    lines = src.splitlines()
    out: List[Dict[str, Any]] = []

    def add(node, kind):
        ln = getattr(node, "lineno", 0)
        out.append({
            "file": path, "line": ln, "kind": kind,
            "text": (lines[ln - 1].strip()[:_MAX_LINE] if 0 < ln <= len(lines) else ""),
        })

    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == sym:
            add(node, "async def" if isinstance(node, ast.AsyncFunctionDef) else "def")
        elif isinstance(node, ast.ClassDef) and node.name == sym:
            add(node, "class")
        elif isinstance(node, ast.Assign):
            for t in node.targets:
                if isinstance(t, ast.Name) and t.id == sym:
                    add(node, "assign")
        elif isinstance(node, ast.AnnAssign):
            if isinstance(node.target, ast.Name) and node.target.id == sym:
                add(node, "assign")
    return out


def _git_files(root: str) -> List[str]:
    """Tracked + untracked-but-not-ignored files, when root is a git repo.

    Without this, a search under a project that keeps generated copies in an
    ignored directory (build output, dev-mirrors, vendored deps) returns mostly
    STALE DUPLICATES of the real source — the model then cites a path that isn't
    the file anyone edits. `--exclude-standard` applies .gitignore, so a file the
    project deliberately ignores is deliberately not searched, while a brand-new
    untracked source file is still found.
    """
    try:
        import subprocess
        p = subprocess.run(
            ["git", "-C", root, "ls-files", "--cached", "--others", "--exclude-standard"],
            capture_output=True, text=True, timeout=15,
        )
        if p.returncode != 0:
            return []
        out = []
        for rel in (p.stdout or "").splitlines():
            rel = rel.strip()
            if not rel or not rel.endswith(_CODE_EXTS):
                continue
            out.append(os.path.join(root, rel))
            if len(out) >= _MAX_FILES:
                break
        return out
    except Exception:
        return []


def _iter_files(root: str, glob_pat: str = "") -> List[str]:
    import fnmatch
    if os.path.isfile(root):
        return [root]
    tracked = _git_files(root)
    if tracked:
        if glob_pat:
            tracked = [p for p in tracked if fnmatch.fnmatch(os.path.basename(p), glob_pat)]
        return tracked
    files: List[str] = []
    for dp, dns, fns in os.walk(root):
        dns[:] = [d for d in dns if d not in _SKIP_DIRS]
        for fn in fns:
            if glob_pat and not fnmatch.fnmatch(fn, glob_pat):
                continue
            if not fn.endswith(_CODE_EXTS):
                continue
            files.append(os.path.join(dp, fn))
            if len(files) >= _MAX_FILES:
                return files
    return files


def _scan(root: str, sym: str, mode: str, glob_pat: str) -> Tuple[List[Dict], List[Dict], bool]:
    """Return (definitions, references, truncated)."""
    word = re.compile(rf"\b{re.escape(sym)}\b")
    pats = _def_patterns(sym)
    defs: List[Dict] = []
    refs: List[Dict] = []
    truncated = False

    for path in _iter_files(root, glob_pat):
        is_py = path.endswith(".py")
        py_def_lines = set()
        if is_py:
            for d in _python_defs(path, sym):
                defs.append(d)
                py_def_lines.add(d["line"])
        try:
            with open(path, "r", encoding="utf-8", errors="strict") as f:
                lines = f.readlines()
        except (UnicodeDecodeError, OSError):
            continue
        for i, line in enumerate(lines, 1):
            if not word.search(line):
                continue
            if is_py and i in py_def_lines:
                continue          # already captured exactly by the AST pass
            hit_kind = ""
            if not is_py:
                for kind, rx in pats:
                    if rx.search(line):
                        hit_kind = kind
                        break
            if hit_kind:
                defs.append({"file": path, "line": i, "kind": hit_kind + "?",
                             "text": line.strip()[:_MAX_LINE]})
            elif mode in ("references", "both"):
                refs.append({"file": path, "line": i, "text": line.strip()[:_MAX_LINE]})
        if len(defs) + len(refs) > _MAX_HITS * 4:
            truncated = True
            break
    return defs, refs[:_MAX_HITS], truncated


class FindSymbolTool:
    async def execute(self, content: str, ctx: dict) -> dict:
        import asyncio

        from src.tool_execution import _resolve_search_root, _truncate

        args: Dict[str, Any] = {}
        s = (content or "").strip()
        if s.startswith("{"):
            try:
                args = json.loads(s)
            except json.JSONDecodeError:
                args = {}
        else:
            args = {"symbol": s}
        symbol = str(args.get("symbol", "")).strip()
        if not symbol:
            return {"error": "find_symbol: symbol is required", "exit_code": 1}
        if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", symbol):
            return {"error": "find_symbol: symbol must be a bare identifier "
                             "(no dots, spaces or regex). Use grep for free-text search.",
                    "exit_code": 1}
        mode = str(args.get("mode", "definition")).strip().lower()
        if mode not in ("definition", "references", "both"):
            mode = "definition"
        glob_pat = str(args.get("glob", "") or "").strip()
        try:
            root = _resolve_search_root(str(args.get("path", "")))
        except ValueError as e:
            return {"error": f"find_symbol: {e}", "exit_code": 1}

        defs, refs, truncated = await asyncio.to_thread(_scan, root, symbol, mode, glob_pat)

        parts: List[str] = []
        if mode in ("definition", "both"):
            if defs:
                parts.append(f"DEFINITIONS of {symbol!r} ({len(defs)}):")
                for d in defs[:_MAX_HITS]:
                    parts.append(f"  {d['file']}:{d['line']}: [{d['kind']}] {d['text']}")
            else:
                parts.append(f"No definition of {symbol!r} found under {root}. "
                             "It may be imported from a dependency, built in, or "
                             "defined dynamically — try grep for a wider search.")
        if mode in ("references", "both"):
            parts.append("")
            if refs:
                parts.append(f"REFERENCES ({len(refs)}{'+' if truncated else ''}):")
                for r in refs:
                    parts.append(f"  {r['file']}:{r['line']}: {r['text']}")
            else:
                parts.append(f"No other references to {symbol!r} found.")
        if truncated:
            parts.append(f"\n... [truncated — narrow with `path` or `glob`]")
        # A `?` suffix on a kind means it was matched by a language pattern, not
        # parsed — say so rather than implying the same confidence as the AST path.
        if any(d["kind"].endswith("?") for d in defs):
            parts.append("\n(kinds ending in '?' are pattern matches in non-Python "
                         "files — verify before relying on them)")
        return {"output": _truncate("\n".join(parts), MAX_OUTPUT_CHARS), "exit_code": 0}
