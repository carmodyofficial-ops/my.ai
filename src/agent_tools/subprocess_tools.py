import asyncio
import os
import re
import sys
import time
import collections
from typing import Optional, Callable, Awaitable, Tuple, Dict
from src.constants import MAX_OUTPUT_CHARS

DEFAULT_BASH_TIMEOUT = 60 * 60     # 1 hour
DEFAULT_PYTHON_TIMEOUT = 60 * 60

# Keys whose VALUES are credentials — never hand them to an agent subprocess
# (a lured agent's `printenv` would otherwise exfiltrate every token/password).
_SECRET_ENV_RE = re.compile(
    r"(TOKEN|SECRET|PASSWORD|PASSWD|API[_-]?KEY|_KEY$|^KEY_|CREDENTIAL|PRIVATE_KEY|_SID|OAUTH|AUTH_)",
    re.I,
)
# Credential files/paths an agent must never touch via the shell. The file tools
# already block these; bash/python bypassed that confinement until now.
_SENSITIVE_CMD_RE = re.compile(
    r"(\.ssh\b|\bid_rsa\b|\bid_ed25519\b|\bid_ecdsa\b|\.gnupg\b|\bsecring\b|"
    r"\.netrc\b|\.pgpass\b|\.aws/|\.kube/|\.docker/config|\.npmrc\b|"
    r"\.env\b|known_hosts|\.pem\b|\.p12\b|credentials\.json)",
    re.I,
)


def scrub_secret_env(env: Optional[dict]) -> dict:
    """Subprocess env with credential-bearing keys removed. Never returns None
    (which would make the child inherit the parent's full, secret-laden environ).
    Keeps PATH/HOME/locale/venv/build vars so builds still work."""
    base = dict(env) if env else dict(os.environ)
    return {k: v for k, v in base.items() if not _SECRET_ENV_RE.search(k)}


def scan_for_sensitive_access(text: str) -> Optional[str]:
    """If a shell command / python source references a credential file, return the
    offending fragment; else None. A heuristic guard (not a sandbox) that closes
    the obvious `cat ~/.ssh/id_rsa` / `cat .env` exfiltration via the shell."""
    if not text:
        return None
    m = _SENSITIVE_CMD_RE.search(text)
    return m.group(0) if m else None

PROGRESS_INTERVAL_S = 2.0
PROGRESS_TAIL_LINES = 12


def _sandbox_preexec(limits: dict):
    """Return a POSIX preexec_fn that applies per-process RLIMITs in the child.

    Only used when the sandbox coder has bound resource limits for this turn, so
    AI-generated build/test code can't exhaust CPU/memory/disk. RLIMIT_NPROC is
    intentionally omitted: it is per-UID (the container runs as root, same UID as
    the app) so it would either be bypassed or throttle the app itself. CPU/AS/
    FSIZE/NOFILE are per-process and safe. Runs after fork, before exec.
    """
    def _apply() -> None:
        try:
            import resource
            cpu = int(limits.get("cpu_s", 240))
            resource.setrlimit(resource.RLIMIT_CPU, (cpu, cpu + 5))
            as_bytes = int(limits.get("as_bytes", 4 * 1024 ** 3))
            resource.setrlimit(resource.RLIMIT_AS, (as_bytes, as_bytes))
            fsize = int(limits.get("fsize", 512 * 1024 ** 2))
            resource.setrlimit(resource.RLIMIT_FSIZE, (fsize, fsize))
            nofile = int(limits.get("nofile", 1024))
            resource.setrlimit(resource.RLIMIT_NOFILE, (nofile, nofile))
        except Exception:
            # Never let limit-setting failure abort the child; degrade to unbounded.
            pass
    return _apply


def _sandbox_subproc_kwargs(default_timeout: int):
    """Resolve (timeout, preexec_fn) from the per-turn sandbox limits, if any.

    Returns the unmodified default timeout and preexec_fn=None for ordinary chat
    (limits unset), so non-sandbox behavior is byte-identical.
    """
    try:
        from src.tool_execution import get_sandbox_limits
        limits = get_sandbox_limits()
    except Exception:
        limits = None
    if not limits:
        return default_timeout, None
    timeout = int(limits.get("timeout", default_timeout))
    preexec = _sandbox_preexec(limits) if sys.platform != "win32" else None
    return timeout, preexec

async def _run_subprocess_streaming(
    proc: asyncio.subprocess.Process,
    *,
    timeout: float,
    progress_cb: Optional[Callable[[Dict], Awaitable[None]]] = None,
) -> Tuple[str, str, Optional[int], bool]:
    started = time.time()
    stdout_full: list[str] = []
    stderr_full: list[str] = []
    tail = collections.deque(maxlen=PROGRESS_TAIL_LINES)

    async def _reader(stream, full_buf, label: str):
        if stream is None:
            return
        while True:
            line = await stream.readline()
            if not line:
                break
            decoded = line.decode("utf-8", errors="replace").rstrip("\n")
            full_buf.append(decoded)
            if label == "err":
                tail.append(f"! {decoded}")
            else:
                tail.append(decoded)

    async def _progress_emitter():
        await asyncio.sleep(PROGRESS_INTERVAL_S)
        while True:
            if progress_cb:
                try:
                    await progress_cb({
                        "elapsed_s": round(time.time() - started, 1),
                        "tail": "\n".join(list(tail)),
                    })
                except Exception:
                    pass
            await asyncio.sleep(PROGRESS_INTERVAL_S)

    rd_out = asyncio.create_task(_reader(proc.stdout, stdout_full, "out"))
    rd_err = asyncio.create_task(_reader(proc.stderr, stderr_full, "err"))
    prog_task = asyncio.create_task(_progress_emitter()) if progress_cb else None

    timed_out = False
    try:
        await asyncio.wait_for(proc.wait(), timeout=timeout)
    except asyncio.TimeoutError:
        timed_out = True
        try:
            proc.kill()
        except Exception:
            pass
        try:
            await asyncio.wait_for(proc.wait(), timeout=2)
        except Exception:
            pass
    except asyncio.CancelledError:
        try:
            proc.kill()
        except Exception:
            pass
        try:
            await asyncio.wait_for(proc.wait(), timeout=2)
        except Exception:
            pass
        for t in (rd_out, rd_err):
            t.cancel()
        if prog_task is not None:
            prog_task.cancel()
        raise
    finally:
        if prog_task is not None and not prog_task.done():
            prog_task.cancel()
            try:
                await prog_task
            except (asyncio.CancelledError, Exception):
                pass
        for t in (rd_out, rd_err):
            try:
                await asyncio.wait_for(t, timeout=1)
            except Exception:
                pass

    return (
        "\n".join(stdout_full),
        "\n".join(stderr_full),
        proc.returncode,
        timed_out,
    )

class BashTool:
    async def execute(self, content: str, ctx: dict) -> dict:
        from src.tool_execution import agent_cwd, _truncate
        hit = scan_for_sensitive_access(content)
        if hit:
            return {"error": f"blocked: command references a protected credential path ('{hit}'). "
                             "Reading secrets / .env / .ssh / credential files is not permitted.",
                    "exit_code": 126}
        progress_cb = ctx.get("progress_cb")
        _subproc_env = scrub_secret_env(ctx.get("subproc_env"))
        _timeout, _preexec = _sandbox_subproc_kwargs(DEFAULT_BASH_TIMEOUT)
        proc = await asyncio.create_subprocess_shell(
            content,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=_subproc_env,
            cwd=agent_cwd(),
            preexec_fn=_preexec,
        )
        stdout, stderr, rc, timed_out = await _run_subprocess_streaming(
            proc,
            timeout=_timeout,
            progress_cb=progress_cb,
        )
        if timed_out:
            return {"error": f"bash: timed out after {_timeout}s — process killed", "exit_code": 124, "stdout": _truncate(stdout, MAX_OUTPUT_CHARS), "stderr": _truncate(stderr, MAX_OUTPUT_CHARS)}
        output = stdout.rstrip()
        err = stderr.rstrip()
        if err:
            output = (output + "\nSTDERR: " + err).strip() if output else "STDERR: " + err
        output = _truncate(output, MAX_OUTPUT_CHARS)
        return {"output": output or "(no output)", "exit_code": rc or 0}

class PythonTool:
    async def execute(self, content: str, ctx: dict) -> dict:
        from src.tool_execution import agent_cwd, _truncate
        hit = scan_for_sensitive_access(content)
        if hit:
            return {"error": f"blocked: code references a protected credential path ('{hit}'). "
                             "Reading secrets / .env / .ssh / credential files is not permitted.",
                    "exit_code": 126}
        progress_cb = ctx.get("progress_cb")
        _subproc_env = scrub_secret_env(ctx.get("subproc_env"))
        _timeout, _preexec = _sandbox_subproc_kwargs(DEFAULT_PYTHON_TIMEOUT)
        proc = await asyncio.create_subprocess_exec(
            (sys.executable or "python"), "-I", "-c", content,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=_subproc_env,
            cwd=agent_cwd(),
            preexec_fn=_preexec,
        )
        stdout, stderr, rc, timed_out = await _run_subprocess_streaming(
            proc,
            timeout=_timeout,
            progress_cb=progress_cb,
        )
        if timed_out:
            return {"error": f"python: timed out after {_timeout}s — process killed", "exit_code": 124, "stdout": _truncate(stdout, MAX_OUTPUT_CHARS), "stderr": _truncate(stderr, MAX_OUTPUT_CHARS)}
        output = stdout.rstrip()
        err = stderr.rstrip()
        if err:
            output = (output + "\nSTDERR: " + err).strip() if output else "STDERR: " + err
        output = _truncate(output, MAX_OUTPUT_CHARS)
        return {"output": output or "(no output)", "exit_code": rc or 0}
