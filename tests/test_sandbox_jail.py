"""Landlock workspace jail for agent subprocesses (src/sandbox_jail.py).

These spawn real jailed processes, so they only run where the kernel supports
Landlock. /tmp is removed from the jail's writable set for the test so pytest's
tmp_path (under /tmp) is genuinely outside the jail unless granted.
"""
import asyncio
import os
import socket
import subprocess
import sys

import pytest

from src import sandbox_jail as J

pytestmark = pytest.mark.skipif(J.landlock_abi() <= 0, reason="kernel lacks Landlock")


@pytest.fixture
def jail(tmp_path, monkeypatch):
    settings = {"agent_sandbox": "jail", "sandbox_network": "web",
                "sandbox_protected_roots": [], "sandbox_read_roots": []}
    monkeypatch.setattr(J, "_setting", lambda k, d: settings.get(k, d))
    monkeypatch.setattr(J, "_SYSTEM_RW", ("/dev/shm", "/dev/pts"))
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setattr(J, "scratch_home", lambda: str(home))
    J._plan_cache.clear()
    ws = tmp_path / "ws"
    (ws / "src").mkdir(parents=True)
    (ws / "src" / "main.py").write_text("print('hi')\n")
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "secret.txt").write_text("TOP-SECRET")
    return settings, ws, outside, home


def run(cmd, **guard_kw):
    with J.guard(**guard_kw) as pre:
        return subprocess.run(["/bin/sh", "-c", cmd], capture_output=True, text=True,
                              env=J.jail_env({"PATH": os.environ.get("PATH", "/usr/bin:/bin")}),
                              preexec_fn=pre, timeout=30)


def test_workspace_rw_and_outside_invisible(jail):
    _, ws, outside, home = jail
    p = run(f"cat {ws}/src/main.py && echo new > {ws}/src/new.txt && cat {ws}/src/new.txt",
            workspace=str(ws))
    assert p.returncode == 0 and "new" in p.stdout
    p = run(f"cat {outside}/secret.txt", workspace=str(ws))
    assert p.returncode != 0 and "TOP-SECRET" not in p.stdout
    p = run(f"touch {outside}/pwned", workspace=str(ws))
    assert p.returncode != 0 and not (outside / "pwned").exists()
    p = run("echo x > $HOME/f && cat $HOME/f", workspace=str(ws))
    assert p.returncode == 0 and (home / "f").exists()


def test_secrets_inside_workspace_are_carved_out(jail):
    _, ws, _, _ = jail
    (ws / ".env").write_text("API_KEY=abc")
    (ws / "data").mkdir()
    (ws / "data" / "auth.json").write_text('{"pw": "x"}')
    (ws / "certs").mkdir()
    (ws / "certs" / "server.key").write_text("KEY")
    J._plan_cache.clear()
    assert run(f"cat {ws}/.env", workspace=str(ws)).returncode != 0
    assert run(f"cat {ws}/data/auth.json", workspace=str(ws)).returncode != 0
    assert run(f"cat {ws}/certs/server.key", workspace=str(ws)).returncode != 0
    # Clean subtrees stay fully usable.
    p = run(f"cat {ws}/src/main.py && touch {ws}/src/ok", workspace=str(ws))
    assert p.returncode == 0 and (ws / "src" / "ok").exists()


def test_protected_root_cannot_be_jailed_or_bound(jail, monkeypatch):
    settings, ws, _, _ = jail
    settings["sandbox_protected_roots"] = [str(ws)]
    with pytest.raises(J.JailUnavailable):
        with J.guard(workspace=str(ws)):
            pass
    # A parent of a protected root is refused too.
    assert J.is_protected_path(str(ws.parent))
    from src.tool_execution import vet_workspace
    assert vet_workspace(str(ws)) is None


def test_off_mode_is_passthrough(jail):
    settings, _, _, _ = jail
    settings["agent_sandbox"] = "off"
    sentinel = lambda: None  # noqa: E731
    with J.guard(sentinel) as pre:
        assert pre is sentinel


def test_local_tcp_and_signals_to_app_blocked(jail):
    _, ws, _, _ = jail
    srv = socket.socket()
    srv.bind(("127.0.0.1", 0))
    srv.listen(1)
    port = srv.getsockname()[1]
    try:
        code = f"import socket; socket.create_connection(('127.0.0.1', {port}), 3)"
        p = run(f"{sys.executable} -c \"{code}\"", workspace=str(ws))
        assert p.returncode != 0
    finally:
        srv.close()
    p = run(f"kill -0 {os.getpid()}", workspace=str(ws))
    assert p.returncode != 0


def test_inner_preexec_still_runs(jail):
    _, ws, _, _ = jail
    import resource

    def inner():
        resource.setrlimit(resource.RLIMIT_NOFILE, (64, 64))
    with J.guard(inner, workspace=str(ws)) as pre:
        p = subprocess.run(["/bin/sh", "-c", "ulimit -n"], capture_output=True, text=True,
                           preexec_fn=pre, timeout=10)
    assert p.stdout.strip() == "64"


def test_bash_tool_runs_jailed(jail):
    _, ws, outside, _ = jail
    from src.agent_tools.subprocess_tools import BashTool
    from src.tool_execution import _active_workspace
    tok = _active_workspace.set(str(ws))
    try:
        ok = asyncio.run(BashTool().execute("cat src/main.py", {}))
        bad = asyncio.run(BashTool().execute(f"cat {outside}/secret.txt", {}))
    finally:
        _active_workspace.reset(tok)
    assert ok["exit_code"] == 0 and "print('hi')" in ok["output"]
    assert bad["exit_code"] != 0 and "TOP-SECRET" not in bad["output"]


def test_background_job_is_jailed(jail, tmp_path, monkeypatch):
    _, ws, outside, _ = jail
    from src import bg_jobs
    jobs = tmp_path / "jobs"
    monkeypatch.setattr(bg_jobs, "_JOBS_DIR", jobs)
    monkeypatch.setattr(bg_jobs, "_save", lambda jobs: None)
    monkeypatch.setattr(bg_jobs, "_load", lambda: {})
    (jobs).mkdir()
    (jobs / "other.log").write_text("OTHER-JOB-OUTPUT")
    rec = bg_jobs.launch(f"cat src/main.py; cat {outside}/secret.txt; cat {jobs}/other.log",
                         session_id="t", cwd=str(ws), jail=True)
    import time
    deadline = time.time() + 20
    while time.time() < deadline and not os.path.getsize(rec["exit_path"]):
        time.sleep(0.1)
    log = open(rec["log_path"]).read()
    assert "print('hi')" in log
    assert "TOP-SECRET" not in log and "OTHER-JOB-OUTPUT" not in log
