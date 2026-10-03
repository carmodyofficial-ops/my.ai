"""code_sandbox — build + test code in an isolated scratch dir, mid-response.

This makes the sandbox a NATIVE part of the normal prompt flow: instead of a
separate /sandbox/build endpoint, the agent can, during any turn, write files and
run/test them in a fresh, resource-limited, secret-scrubbed scratch dir, read the
result, fix, and re-run — then hand back code it has actually executed.

Distinct from the heavy dev-mirror pipeline (which produces a reviewed PATCH to
modify the REAL repo): this is an ephemeral interpreter for producing verified
standalone code. Admin/single-user only (it executes code); reuses the Wave-1
subprocess hardening (env scrub + sensitive-path scan + RLIMITs).
"""

import asyncio
import json
import os
import shutil
import time
from pathlib import Path
from typing import Optional

from src.constants import MAX_OUTPUT_CHARS
from src import sandbox_jail
from .subprocess_tools import scrub_secret_env, scan_for_sensitive_access, _sandbox_preexec

# Per-run resource caps (CPU/mem/file-size/fds/wall-clock) so AI-generated code
# can't exhaust the host. Tighter than a full build since this is a quick verify.
_LIMITS = {"cpu_s": 30, "as_bytes": 2 * 1024 ** 3, "fsize": 64 * 1024 ** 2, "nofile": 256, "timeout": 45}

_PARSE_ERR = ('code_sandbox expects {"files": [{"path": "...", "content": "..."}], '
              '"run": "optional shell command"}')


def _scratch_root() -> Path:
    base = Path(os.environ.get("MYAI_ROOT") or ("/app" if Path("/app").exists() else "/home/youruser/odysseus"))
    return base / "data/sandbox_scratch"


def _safe_rel(path: str) -> Optional[str]:
    """Confine a file path to the scratch dir: relative, no '..' escape."""
    p = (path or "").strip().lstrip("/")
    if not p or ".." in Path(p).parts:
        return None
    return p


def _sweep_old(root: Path, max_age_s: int = 3600) -> None:
    try:
        now = time.time()
        for d in root.iterdir():
            if d.is_dir() and (now - d.stat().st_mtime) > max_age_s:
                shutil.rmtree(d, ignore_errors=True)
    except Exception:
        pass


class CodeSandboxTool:
    async def execute(self, content, ctx: dict) -> dict:
        try:
            args = json.loads(content) if isinstance(content, str) else (content or {})
        except Exception:
            return {"error": _PARSE_ERR, "exit_code": 2}
        if not isinstance(args, dict):
            return {"error": _PARSE_ERR, "exit_code": 2}
        files = args.get("files") or []
        run = (args.get("run") or "").strip()
        if not isinstance(files, list) or not files:
            return {"error": "code_sandbox: provide at least one file in `files`.", "exit_code": 2}

        root = _scratch_root()
        root.mkdir(parents=True, exist_ok=True)
        _sweep_old(root)
        # Per-session scratch dir so repeated calls within a turn accumulate.
        sid = "".join(c for c in str(ctx.get("session_id") or "default") if c.isalnum() or c in "-_")[:40] or "default"
        sbx = root / f"sbx_{sid}"
        sbx.mkdir(parents=True, exist_ok=True)

        written = []
        for f in files:
            if not isinstance(f, dict):
                continue
            rel = _safe_rel(f.get("path", ""))
            if rel is None:
                return {"error": f"code_sandbox: rejected unsafe path {f.get('path')!r} (must be relative, no '..').",
                        "exit_code": 2}
            dest = sbx / rel
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_text(str(f.get("content", "")), encoding="utf-8")
            written.append(rel)

        # Decide what to run: explicit `run`, else auto (pytest if a test file is
        # present, else the single .py file, else just keep the written files).
        if run:
            if scan_for_sensitive_access(run):
                return {"error": "code_sandbox: run command references a protected credential path.", "exit_code": 126}
            cmds = [run]
        else:
            py = [w for w in written if w.endswith(".py")]
            tests = [w for w in py if "test" in Path(w).name]
            if tests:
                cmds = ["python3 -m pytest -q"]
            elif len(py) == 1:
                cmds = [f"python3 {py[0]}"]
            else:
                cmds = []

        env = scrub_secret_env(None)
        preexec = _sandbox_preexec(_LIMITS) if os.name == "posix" else None
        results = []
        for cmd in cmds:
            try:
                # The scratch dir is the only writable place; the bound
                # workspace is not exposed to throwaway snippets.
                with sandbox_jail.guard(preexec, use_active_workspace=False,
                                        extra_rw=[str(sbx)]) as jailed_preexec:
                    proc = await asyncio.create_subprocess_shell(
                        cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
                        cwd=str(sbx), env=sandbox_jail.jail_env(env), preexec_fn=jailed_preexec)
                try:
                    out, err = await asyncio.wait_for(proc.communicate(), timeout=_LIMITS["timeout"])
                    results.append({"cmd": cmd, "exit_code": proc.returncode,
                                    "stdout": out.decode("utf-8", "replace")[-MAX_OUTPUT_CHARS:],
                                    "stderr": err.decode("utf-8", "replace")[-MAX_OUTPUT_CHARS:]})
                except asyncio.TimeoutError:
                    try:
                        proc.kill()
                    except Exception:
                        pass
                    results.append({"cmd": cmd, "exit_code": 124, "stdout": "",
                                    "stderr": f"timed out after {_LIMITS['timeout']}s"})
            except Exception as e:
                results.append({"cmd": cmd, "exit_code": 1, "stdout": "", "stderr": f"{type(e).__name__}: {e}"})

        ok = all(r["exit_code"] == 0 for r in results) if results else True
        lines = [f"sandbox: {sbx.name}   files: {', '.join(written) or '(none)'}"]
        for r in results:
            tag = "OK" if r["exit_code"] == 0 else f"FAIL (exit {r['exit_code']})"
            lines.append(f"$ {r['cmd']}  ->  {tag}")
            body = (r["stdout"] + (("\n" + r["stderr"]) if r["stderr"] else "")).strip()
            if body:
                lines.append(body)
        if not cmds:
            lines.append("(files written; nothing auto-run — pass `run` to execute)")
        return {"output": "\n".join(lines)[:MAX_OUTPUT_CHARS], "exit_code": 0 if ok else 1,
                "ok": ok, "files": written, "results": results}
