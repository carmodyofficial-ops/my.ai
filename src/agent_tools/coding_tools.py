"""Dedicated coding tools — run_tests / git / lint_format.

Thin, structured wrappers over the SAME confined-subprocess machinery the bash
and python tools use (workspace cwd via agent_cwd(), per-turn sandbox RLIMITs +
timeout via _sandbox_subproc_kwargs, secret-scrubbed env, streamed output). The
value over freehand bash is (a) parsed pass/fail for run_tests, (b) an allowlist
that keeps git to safe, local, non-destructive subcommands, and (c) auto-detected
linters/formatters. All three are admin-gated (they execute) like bash/python.

Structured args arrive as a JSON string in `content` (the default mapping in
function_call_to_tool_block).
"""
from __future__ import annotations

import asyncio
import json
import os
import re
import shlex
import shutil
import tempfile
import urllib.parse

from .subprocess_tools import (
    _run_subprocess_streaming,
    _sandbox_subproc_kwargs,
    scan_for_sensitive_access,
    scrub_secret_env,
    MAX_OUTPUT_CHARS,
)

DEFAULT_TEST_TIMEOUT = 300
DEFAULT_GIT_TIMEOUT = 60
DEFAULT_LINT_TIMEOUT = 120


def _parse_args(content) -> dict:
    if isinstance(content, dict):
        return content
    if not content or not str(content).strip():
        return {}
    try:
        v = json.loads(content)
        return v if isinstance(v, dict) else {}
    except Exception:
        return {}


async def _run(cmd: list[str], cwd: str, ctx: dict, default_timeout: int) -> tuple[str, str, int | None, bool, int]:
    _timeout, _preexec = _sandbox_subproc_kwargs(default_timeout)
    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        env=scrub_secret_env(ctx.get("subproc_env")),
        cwd=cwd,
        preexec_fn=_preexec,
    )
    stdout, stderr, rc, timed_out = await _run_subprocess_streaming(
        proc, timeout=_timeout, progress_cb=ctx.get("progress_cb")
    )
    return stdout, stderr, rc, timed_out, _timeout


# ---------------------------------------------------------------------------
# run_tests
# ---------------------------------------------------------------------------

def _detect_test_framework(cwd: str) -> str:
    has = lambda *names: any(os.path.exists(os.path.join(cwd, n)) for n in names)
    if has("Cargo.toml"):
        return "cargo"
    if has("go.mod"):
        return "go"
    if has("package.json"):
        try:
            with open(os.path.join(cwd, "package.json"), encoding="utf-8") as f:
                if '"test"' in f.read():
                    return "npm"
        except Exception:
            pass
    # default to pytest for python repos (conftest/pytest.ini/pyproject/tests/)
    return "pytest"


def _build_test_cmd(framework: str, path: str) -> list[str] | None:
    p = [path] if path else []
    if framework == "pytest":
        return ["python3", "-m", "pytest", "-q", "--no-header", *p]
    if framework == "npm":
        return ["npm", "test", "--silent"]
    if framework == "go":
        return ["go", "test", *(p or ["./..."])]
    if framework == "cargo":
        return ["cargo", "test", "-q"]
    return None


def _parse_test_summary(output: str, rc: int | None) -> dict:
    out = {"passed": None, "failed": None, "errors": None, "ok": (rc == 0)}
    m = re.search(r"(\d+) passed", output)
    if m:
        out["passed"] = int(m.group(1))
    m = re.search(r"(\d+) failed", output)
    if m:
        out["failed"] = int(m.group(1))
    m = re.search(r"(\d+) error", output)
    if m:
        out["errors"] = int(m.group(1))
    # Build a one-line summary.
    bits = []
    for k in ("passed", "failed", "errors"):
        if out[k] is not None:
            bits.append(f"{out[k]} {k}")
    out["summary"] = (", ".join(bits) if bits else ("PASS" if rc == 0 else f"exit {rc}"))
    return out


class RunTestsTool:
    async def execute(self, content, ctx: dict) -> dict:
        from src.tool_execution import agent_cwd, _truncate
        args = _parse_args(content)
        path = str(args.get("path") or "").strip()
        framework = str(args.get("framework") or "auto").strip().lower()
        if scan_for_sensitive_access(path):
            return {"error": "blocked: path references a protected credential location."}
        cwd = agent_cwd()
        if framework in ("", "auto"):
            framework = _detect_test_framework(cwd)
        cmd = _build_test_cmd(framework, path)
        if cmd is None:
            return {"error": f"unknown test framework '{framework}' (use auto|pytest|npm|go|cargo)."}
        if shutil.which(cmd[0]) is None:
            return {"error": f"'{cmd[0]}' not found — cannot run {framework} tests here."}
        stdout, stderr, rc, timed_out, t = await _run(cmd, cwd, ctx, DEFAULT_TEST_TIMEOUT)
        combined = (stdout + ("\n" + stderr if stderr else "")).strip()
        if timed_out:
            return {"framework": framework, "ok": False, "timed_out": True,
                    "error": f"tests timed out after {t}s — process killed",
                    "output": _truncate(combined, MAX_OUTPUT_CHARS)}
        low = combined.lower()
        # A missing test runner is an environment problem, not a failing test
        # run — say so explicitly instead of a bare "exit 1".
        if "no module named pytest" in low:
            return {"framework": framework, "ok": False, "no_tests": True,
                    "error": "pytest is not installed in this environment — "
                             "cannot run Python tests. Verify another way "
                             "(e.g. run the code directly).",
                    "output": _truncate(combined, MAX_OUTPUT_CHARS)}
        # "No tests exist here" is a NEUTRAL result, not a failure. Without this,
        # pytest's exit 5 (nothing collected) reads as a failing test run and
        # sends the model into pointless re-verify loops on test-less workspaces.
        if (framework == "pytest" and rc == 5) or "no tests ran" in low or "no test files" in low:
            return {"framework": framework, "exit_code": 0, "ok": True, "no_tests": True,
                    "passed": 0, "failed": 0, "errors": 0,
                    "summary": "no tests found in this workspace — nothing to run "
                               "(verify another way, e.g. run the code directly)",
                    "output": _truncate(combined, MAX_OUTPUT_CHARS) or "(no output)"}
        summary = _parse_test_summary(combined, rc)
        return {"framework": framework, "exit_code": rc or 0, **summary,
                "output": _truncate(combined, MAX_OUTPUT_CHARS) or "(no output)"}


# ---------------------------------------------------------------------------
# git (allowlisted, local, non-destructive)
# ---------------------------------------------------------------------------

# Safe, local, mostly-read subcommands. Local writes (add/commit/stash/restore)
# are allowed because the human still reviews/approves before anything ships.
_GIT_ALLOWED = {
    "status", "diff", "log", "show", "branch", "add", "commit", "stash",
    "restore", "rev-parse", "blame", "ls-files", "tag", "describe",
    "shortlog", "remote", "fetch", "switch",
}
# Never, even if someone tries to smuggle them in as the subcommand.
_GIT_FORBIDDEN_TOKENS = {
    "push", "reset", "rebase", "clean", "merge", "cherry-pick", "checkout",
    "filter-branch", "gc", "prune", "reflog", "--force", "-f",
    "--force-with-lease", "--hard",
}


class GitTool:
    async def execute(self, content, ctx: dict) -> dict:
        from src.tool_execution import agent_cwd, _truncate
        args = _parse_args(content)
        sub = str(args.get("subcommand") or "").strip()
        rest = args.get("args") or []
        if isinstance(rest, str):
            try:
                rest = shlex.split(rest)
            except Exception:
                rest = rest.split()
        rest = [str(x) for x in rest]
        if sub not in _GIT_ALLOWED:
            return {"error": f"git '{sub}' is not allowed. Allowed (local/non-destructive): "
                             f"{', '.join(sorted(_GIT_ALLOWED))}. For anything else, ask the operator."}
        toks = [sub, *rest]
        bad = next((t for t in toks if t in _GIT_FORBIDDEN_TOKENS), None)
        if bad:
            return {"error": f"git: token '{bad}' is blocked (destructive / history-rewriting / remote-push). "
                             "This tool stays local and non-destructive."}
        joined = " ".join(toks)
        if scan_for_sensitive_access(joined):
            return {"error": "blocked: command references a protected credential location."}
        cmd = ["git", sub, *rest]
        if shutil.which("git") is None:
            return {"error": "git not found."}
        cwd = agent_cwd()
        stdout, stderr, rc, timed_out, t = await _run(cmd, cwd, ctx, DEFAULT_GIT_TIMEOUT)
        if timed_out:
            return {"error": f"git timed out after {t}s", "exit_code": 124}
        out = stdout.rstrip()
        err = stderr.rstrip()
        if err:
            out = (out + "\nSTDERR: " + err).strip() if out else "STDERR: " + err
        return {"output": _truncate(out, MAX_OUTPUT_CHARS) or "(no output)", "exit_code": rc or 0}


# ---------------------------------------------------------------------------
# lint_format
# ---------------------------------------------------------------------------

def _detect_linter(path: str) -> str | None:
    ext = os.path.splitext(path)[1].lower()
    if ext in (".py", ""):
        if shutil.which("ruff"):
            return "ruff"
        if shutil.which("black"):
            return "black"
    if ext in (".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs"):
        if shutil.which("npx") or shutil.which("eslint"):
            return "eslint"
        if shutil.which("prettier"):
            return "prettier"
    if ext == ".go" and shutil.which("gofmt"):
        return "gofmt"
    return None


def _build_lint_cmd(tool: str, path: str, fix: bool) -> list[str] | None:
    if tool == "ruff":
        return ["ruff", "check", *(["--fix"] if fix else []), path]
    if tool == "black":
        return ["black", *([] if fix else ["--check", "--diff"]), path]
    if tool == "eslint":
        base = ["npx", "eslint"] if shutil.which("npx") else ["eslint"]
        return [*base, *(["--fix"] if fix else []), path]
    if tool == "prettier":
        base = ["npx", "prettier"] if shutil.which("npx") else ["prettier"]
        return [*base, *(["--write"] if fix else ["--check"]), path]
    if tool == "gofmt":
        return ["gofmt", *(["-w"] if fix else ["-l", "-d"]), path]
    return None


class LintFormatTool:
    async def execute(self, content, ctx: dict) -> dict:
        from src.tool_execution import agent_cwd, _truncate
        args = _parse_args(content)
        path = str(args.get("path") or ".").strip()
        fix = bool(args.get("fix"))
        tool = str(args.get("tool") or "auto").strip().lower()
        if scan_for_sensitive_access(path):
            return {"error": "blocked: path references a protected credential location."}
        if tool in ("", "auto"):
            tool = _detect_linter(path)
        if not tool:
            return {"error": f"no linter/formatter available for '{path}'. Install ruff/black (py), "
                             "eslint/prettier (js/ts), or gofmt (go)."}
        cmd = _build_lint_cmd(tool, path, fix)
        if cmd is None:
            return {"error": f"unknown linter '{tool}'."}
        if shutil.which(cmd[0]) is None:
            return {"error": f"'{cmd[0]}' not found."}
        cwd = agent_cwd()
        stdout, stderr, rc, timed_out, t = await _run(cmd, cwd, ctx, DEFAULT_LINT_TIMEOUT)
        if timed_out:
            return {"error": f"{tool} timed out after {t}s", "exit_code": 124}
        combined = (stdout + ("\n" + stderr if stderr else "")).strip()
        return {"tool": tool, "fixed": fix, "exit_code": rc or 0,
                "clean": (rc == 0),
                "output": _truncate(combined, MAX_OUTPUT_CHARS) or "(no issues)"}


# ---------------------------------------------------------------------------
# apply_patch — apply a unified diff to the workspace via `git apply`
# ---------------------------------------------------------------------------

class ApplyPatchTool:
    async def execute(self, content, ctx: dict) -> dict:
        from src.tool_execution import agent_cwd, _truncate
        args = _parse_args(content)
        patch = args.get("patch") or args.get("diff") or ""
        if not str(patch).strip():
            return {"error": "apply_patch: 'patch' (a unified diff) is required."}
        if shutil.which("git") is None:
            return {"error": "apply_patch: git not found."}
        # Path safety: reject any target that's absolute, escapes the tree, or is a
        # secret path. git diffs prefix targets with a/ and b/ (or /dev/null for new).
        targets = re.findall(r'^[+-]{3} [ab]/(.+)$', patch, re.M)
        for t in {x.strip() for x in targets}:
            if t.startswith("/") or ".." in t.split("/") or scan_for_sensitive_access(t):
                return {"error": f"apply_patch: refusing a patch that touches '{t}' "
                                 "(absolute / parent-escaping / credential path)."}
        cwd = agent_cwd()
        if not patch.endswith("\n"):
            patch += "\n"
        tmp = None
        try:
            fd, tmp = tempfile.mkstemp(suffix=".patch")
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                f.write(patch)
            so, se, rc, to, t = await _run(["git", "apply", "--check", tmp], cwd, ctx, DEFAULT_GIT_TIMEOUT)
            if rc != 0:
                return {"error": "apply_patch: patch does not apply cleanly (checked, nothing changed).",
                        "output": _truncate((so + se).strip(), MAX_OUTPUT_CHARS)}
            files = sorted({x.strip() for x in targets if x.strip() != "dev/null"})
            abs_files = [os.path.join(cwd, f) for f in files]
            # Snapshot every target AFTER --check passes and BEFORE the real
            # apply, so a multi-file patch is undoable like any other edit. A
            # file the patch creates snapshots as "did not exist", so undoing it
            # removes the file rather than leaving an empty one.
            checkpoint_ids = []
            try:
                from src.file_checkpoints import snapshot
                for _p in abs_files:
                    _cid = snapshot(_p, tool="apply_patch")
                    if _cid:
                        checkpoint_ids.append(_cid)
            except Exception:
                pass
            so, se, rc, to, t = await _run(["git", "apply", tmp], cwd, ctx, DEFAULT_GIT_TIMEOUT)
            if rc != 0:
                return {"error": "apply_patch: git apply failed.",
                        "output": _truncate((so + se).strip(), MAX_OUTPUT_CHARS)}
            # Report the changed paths so the post-edit syntax check covers them
            # (previously apply_patch returned no path at all and was skipped).
            try:
                from src.file_ledger import record_read
                for _p in abs_files:
                    record_read(_p)
            except Exception:
                pass
            return {"output": f"Applied patch to {len(files)} file(s): {', '.join(files) or '(unknown)'}",
                    "exit_code": 0,
                    "paths": abs_files,
                    "checkpoint_ids": checkpoint_ids}
        except OSError as e:
            return {"error": f"apply_patch: {e}", "exit_code": 1}
        finally:
            if tmp:
                try:
                    os.remove(tmp)
                except OSError:
                    pass


# ---------------------------------------------------------------------------
# http_request — make an external HTTP request (admin-gated; SSRF-guarded)
# ---------------------------------------------------------------------------

# Cloud metadata endpoints are pure attack surface — block them outright. Private/
# localhost is allowed (legit for testing local services in interactive work).
_HTTP_BLOCKED_HOSTS = {
    "169.254.169.254", "metadata.google.internal", "metadata.goog", "metadata",
    "100.100.100.200",  # Alibaba metadata
}
_HTTP_METHODS = {"GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"}


class HttpRequestTool:
    async def execute(self, content, ctx: dict) -> dict:
        from src.tool_execution import _truncate
        args = _parse_args(content)
        url = str(args.get("url") or "").strip()
        method = str(args.get("method") or "GET").strip().upper()
        headers = args.get("headers") or {}
        body = args.get("body")
        try:
            timeout = float(args.get("timeout") or 30)
        except (TypeError, ValueError):
            timeout = 30.0
        if not url:
            return {"error": "http_request: 'url' is required."}
        if not url.lower().startswith(("http://", "https://")):
            return {"error": "http_request: url must start with http:// or https://"}
        if method not in _HTTP_METHODS:
            return {"error": f"http_request: method '{method}' not allowed ({', '.join(sorted(_HTTP_METHODS))})."}
        host = (urllib.parse.urlparse(url).hostname or "").lower()
        if host in _HTTP_BLOCKED_HOSTS:
            return {"error": "http_request: blocked host (cloud metadata endpoint)."}
        if not isinstance(headers, dict):
            headers = {}
        try:
            import httpx
            kw = {"headers": {str(k): str(v) for k, v in headers.items()}}
            if body is not None and method not in ("GET", "HEAD"):
                if isinstance(body, (dict, list)):
                    kw["json"] = body
                else:
                    kw["content"] = str(body)
            async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
                r = await client.request(method, url, **kw)
            return {
                "status": r.status_code,
                "headers": dict(list(r.headers.items())[:20]),
                "body": _truncate(r.text, MAX_OUTPUT_CHARS),
                "exit_code": 0 if r.status_code < 400 else 1,
            }
        except Exception as e:  # network/timeout/parse — surface, don't crash the turn
            return {"error": f"http_request: {str(e)[:200]}", "exit_code": 1}


# ---------------------------------------------------------------------------
# manage_corpus — ingest/search/stats the licensed external-knowledge corpus
# ---------------------------------------------------------------------------

def _html_to_text(html: str) -> str:
    """Light HTML -> text: drop script/style, strip tags, unescape entities. Good
    enough for ingesting doc pages without a heavy parser."""
    import html as _html
    s = re.sub(r"(?is)<(script|style|nav|footer|header)[^>]*>.*?</\1>", " ", html)
    s = re.sub(r"(?is)<br\s*/?>", "\n", s)
    s = re.sub(r"(?is)</(p|div|li|h[1-6]|tr|section|article)>", "\n", s)
    s = re.sub(r"(?s)<[^>]+>", " ", s)
    s = _html.unescape(s)
    s = re.sub(r"[ \t]+", " ", s)
    s = re.sub(r"\n[ \t]+", "\n", s)
    return s.strip()


class ManageCorpusTool:
    async def execute(self, content, ctx: dict) -> dict:
        from src.knowledge_corpus import (ingest_text, search_corpus, corpus_stats,
                                           reset_corpus, ingest_hf_dataset)
        from src.tool_execution import _truncate
        args = _parse_args(content)
        action = str(args.get("action") or "stats").strip().lower()

        if action == "stats":
            return corpus_stats()

        if action == "reset":
            return reset_corpus()

        if action == "search":
            q = str(args.get("query") or "").strip()
            if not q:
                return {"error": "manage_corpus search: 'query' required"}
            hits = await asyncio.to_thread(search_corpus, q, int(args.get("k") or 5))
            return {"count": len(hits), "results": hits}

        if action == "ingest_text":
            # Heavy (embed+upsert) — off the event loop.
            return await asyncio.to_thread(
                ingest_text, str(args.get("text") or ""),
                source=str(args.get("source") or ""), url=str(args.get("url") or ""),
                license=str(args.get("license") or ""), title=str(args.get("title") or ""),
                max_chunks=args.get("max_chunks"))

        if action == "ingest_hf":
            ds = str(args.get("dataset") or "").strip()
            if not ds:
                return {"error": "manage_corpus ingest_hf: 'dataset' required (e.g. 'databricks/databricks-dolly-15k')"}
            tc = args.get("text_columns")
            if isinstance(tc, str):
                tc = [tc]
            # Streams + embeds many rows — run off the event loop.
            return await asyncio.to_thread(
                ingest_hf_dataset, ds, config=args.get("config"), split=args.get("split"),
                text_columns=tc, max_rows=int(args.get("max_rows") or 300),
                start_offset=int(args.get("start_offset") or 0),
                license_override=(str(args.get("license")).strip() or None) if args.get("license") else None)

        if action == "ingest_url":
            url = str(args.get("url") or "").strip()
            license = str(args.get("license") or "").strip()
            if not url.lower().startswith(("http://", "https://")):
                return {"error": "manage_corpus ingest_url: 'url' must be http(s)"}
            if not license:
                return {"error": "manage_corpus ingest_url: 'license' is required (no unlicensed ingestion)"}
            host = (urllib.parse.urlparse(url).hostname or "").lower()
            if host in _HTTP_BLOCKED_HOSTS:
                return {"error": "manage_corpus: blocked host (cloud metadata endpoint)."}
            try:
                import httpx
                async with httpx.AsyncClient(timeout=45, follow_redirects=True) as c:
                    r = await c.get(url)
                body = r.text
            except Exception as e:
                return {"error": f"manage_corpus fetch failed: {str(e)[:160]}"}
            ctype = r.headers.get("content-type", "")
            text = _html_to_text(body) if ("html" in ctype or url.rstrip("/").endswith((".html", ".htm"))) else body
            return await asyncio.to_thread(
                ingest_text, text, source=str(args.get("source") or url),
                url=url, license=license, title=str(args.get("title") or ""),
                max_chunks=args.get("max_chunks"))

        return {"error": f"manage_corpus: unknown action '{action}' (stats|search|ingest_text|ingest_url|ingest_hf|reset)"}
