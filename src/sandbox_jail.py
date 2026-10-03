"""Kernel-enforced workspace jail for agent subprocesses (Linux Landlock).

The bash/python/run_tests/git/code_sandbox/background-job tools used to run as
plain children of the app: same filesystem view (the whole home directory is
bind-mounted read-write at /host), same data dir (auth.json, app.db, TLS keys),
same network. The regex guard in subprocess_tools is a heuristic, "not a
sandbox". This module is the sandbox.

Each agent subprocess is restricted, by the kernel, before it execs:

  * write: the bound workspace, a private scratch HOME, /tmp, and explicitly
    granted files (a background job's own log/exit files). Nothing else.
  * read:  system directories (/usr, /etc, /proc, ...), plus the above, plus any
    `sandbox_read_roots`. The rest of /host, the app's data dir and source tree
    are invisible (EACCES).
  * secrets inside a workspace (.env, .ssh, auth.json, *.pem, ...) are carved
    out: a workspace that contains one is granted entry-by-entry around it.
  * network: TCP connect only to web ports by default (`sandbox_network`), so
    jailed code can't reach chromadb/searxng/ollama/the app's own API.
  * scope: no signals to, and no abstract-socket connections into, processes
    outside the jail (the app itself); ptrace/procfs access to them is denied.

Landlock is unprivileged and stackable, needs no extra container capabilities,
and only ever removes access. The ruleset is built in the parent (all the path
opening and syscalls), so the post-fork preexec hook does just two syscalls.

Settings (data/settings.json):
  agent_sandbox            "jail" (default) | "off"
  sandbox_network          "web" (default: TCP 80/443/53 + sandbox_net_ports)
                           | "none" | "any"
  sandbox_net_ports        extra TCP ports for "web" (list of int)
  sandbox_read_roots       extra read-only directories (list of str)
  sandbox_protected_roots  directories that may never be bound as a workspace
                           (e.g. a live-trading repo); see is_protected_path.

When the jail is on but the kernel can't enforce it, spawning fails closed.
"""
from __future__ import annotations

import contextlib
import ctypes
import os
import struct
import sys
import threading
import time
from typing import Callable, Iterable, Iterator, List, Optional, Tuple

# ── Landlock ABI ────────────────────────────────────────────────────────────
# Syscall numbers are from the generic table: identical on x86_64 and aarch64.
_SYS_CREATE_RULESET = 444
_SYS_ADD_RULE = 445
_SYS_RESTRICT_SELF = 446
_CREATE_RULESET_VERSION = 1 << 0
_RULE_PATH_BENEATH = 1
_RULE_NET_PORT = 2
_PR_SET_NO_NEW_PRIVS = 38

FS_EXECUTE = 1 << 0
FS_WRITE_FILE = 1 << 1
FS_READ_FILE = 1 << 2
FS_READ_DIR = 1 << 3
FS_REMOVE_DIR = 1 << 4
FS_REMOVE_FILE = 1 << 5
FS_MAKE_CHAR = 1 << 6
FS_MAKE_DIR = 1 << 7
FS_MAKE_REG = 1 << 8
FS_MAKE_SOCK = 1 << 9
FS_MAKE_FIFO = 1 << 10
FS_MAKE_BLOCK = 1 << 11
FS_MAKE_SYM = 1 << 12
FS_REFER = 1 << 13        # ABI 2
FS_TRUNCATE = 1 << 14     # ABI 3
FS_IOCTL_DEV = 1 << 15    # ABI 5
NET_CONNECT_TCP = 1 << 1  # ABI 4
SCOPE_ABSTRACT_UNIX = 1 << 0  # ABI 6
SCOPE_SIGNAL = 1 << 1         # ABI 6

# Rights that are valid on a non-directory rule.
_FILE_ONLY = FS_EXECUTE | FS_WRITE_FILE | FS_READ_FILE | FS_TRUNCATE | FS_IOCTL_DEV


class _RulesetAttr(ctypes.Structure):
    _fields_ = [("handled_access_fs", ctypes.c_uint64),
                ("handled_access_net", ctypes.c_uint64),
                ("scoped", ctypes.c_uint64)]


def _path_beneath_attr(allowed_access: int, parent_fd: int):
    """struct landlock_path_beneath_attr is __packed__ (u64 + s32 = 12 bytes)."""
    return ctypes.create_string_buffer(struct.pack("=Qi", allowed_access, parent_fd), 12)


class _NetPortAttr(ctypes.Structure):
    _fields_ = [("allowed_access", ctypes.c_uint64), ("port", ctypes.c_uint64)]


try:
    _libc = ctypes.CDLL(None, use_errno=True)
    _syscall = _libc.syscall
    _syscall.restype = ctypes.c_long
    _prctl = _libc.prctl
    _prctl.restype = ctypes.c_int
except (OSError, AttributeError):  # non-Linux / no libc
    _libc = _syscall = _prctl = None


class JailUnavailable(RuntimeError):
    """The jail is enabled but this kernel/runtime can't enforce it."""


_abi_cache: Optional[int] = None


def landlock_abi() -> int:
    """Landlock ABI version supported by the running kernel, 0 if none."""
    global _abi_cache
    if _abi_cache is None:
        v = -1
        if sys.platform.startswith("linux") and _syscall is not None:
            v = _syscall(_SYS_CREATE_RULESET, None, ctypes.c_size_t(0),
                         ctypes.c_uint32(_CREATE_RULESET_VERSION))
        _abi_cache = int(v) if v and v > 0 else 0
    return _abi_cache


def _fs_rights(abi: int) -> int:
    rights = (FS_EXECUTE | FS_WRITE_FILE | FS_READ_FILE | FS_READ_DIR | FS_REMOVE_DIR
              | FS_REMOVE_FILE | FS_MAKE_CHAR | FS_MAKE_DIR | FS_MAKE_REG | FS_MAKE_SOCK
              | FS_MAKE_FIFO | FS_MAKE_BLOCK | FS_MAKE_SYM)
    if abi >= 2:
        rights |= FS_REFER
    if abi >= 3:
        rights |= FS_TRUNCATE
    if abi >= 5:
        rights |= FS_IOCTL_DEV
    return rights


# ── Policy ──────────────────────────────────────────────────────────────────
_SYSTEM_RO = ("/usr", "/bin", "/sbin", "/lib", "/lib32", "/lib64", "/libx32",
              "/opt", "/proc", "/sys")
# /etc is granted entry by entry minus these: the app's own config mount
# (/etc/myai holds the WhatsApp provider env file), password hashes, and TLS
# private keys. /run (docker secrets) is deliberately not granted at all.
_ETC_HIDDEN = {"myai", "shadow", "shadow-", "gshadow", "gshadow-", "sudoers", "sudoers.d",
               "ssl/private", "security/opasswd"}
_SYSTEM_RW = ("/tmp", "/var/tmp", "/dev/shm", "/dev/pts")
_DEV_RW_FILES = ("/dev/null", "/dev/zero", "/dev/full", "/dev/random",
                 "/dev/urandom", "/dev/tty", "/dev/ptmx")
_WEB_PORTS = (80, 443, 53)

# Names that mark a secret inside a workspace, on top of tool_execution's
# sensitive-path list (.ssh, .gnupg, .env, shell rc files, key files).
_EXTRA_SECRET_NAMES = {"auth.json", "app.db", "credentials.json", ".git-credentials",
                       ".npmrc", ".pypirc", ".netrc", ".pgpass", ".aws", ".kube",
                       ".docker", "secrets", ".secrets"}
_SECRET_SUFFIXES = (".pem", ".key", ".p12", ".pfx", ".kdbx", ".env")
# Don't descend into these when scanning a workspace for secrets (huge, and
# never where a project's own secrets live).
_SCAN_SKIP = {"node_modules", ".git", ".venv", "venv", "__pycache__", "site-packages",
              "dist", "build", ".cache", ".tox", ".mypy_cache", ".pytest_cache", "target"}
_SCAN_DEPTH = 3


def _setting(key: str, default):
    try:
        from src.settings import get_setting
        v = get_setting(key, default)
        return default if v is None else v
    except Exception:
        return default


def enabled() -> bool:
    return str(_setting("agent_sandbox", "jail")).strip().lower() != "off"


def scratch_home() -> str:
    from src.constants import DATA_DIR
    path = os.path.join(DATA_DIR, "sandbox_home")
    os.makedirs(path, exist_ok=True)
    return path


def is_protected_path(path: str) -> bool:
    """True when *path* is (inside) a `sandbox_protected_roots` entry, or
    contains one — binding a parent would expose the protected tree too."""
    roots = _setting("sandbox_protected_roots", [])
    if not isinstance(roots, list) or not path:
        return False
    real = os.path.realpath(path)
    for r in roots:
        try:
            pr = os.path.realpath(os.path.expanduser(str(r)))
        except Exception:
            continue
        if not pr or pr == "/":
            continue
        if real == pr or real.startswith(pr + os.sep) or pr.startswith(real.rstrip(os.sep) + os.sep):
            return True
    return False


def _is_secret_name(name: str) -> bool:
    from src.tool_execution import _SENSITIVE_BASENAMES, _SENSITIVE_FILE_PATTERNS
    low = name.lower()
    return (name in _SENSITIVE_BASENAMES or name in _SENSITIVE_FILE_PATTERNS
            or low in _EXTRA_SECRET_NAMES or low.endswith(_SECRET_SUFFIXES)
            or (low.startswith(".env.") and low != ".env.example"))


def _has_secret(path: str, depth: int) -> bool:
    try:
        with os.scandir(path) as it:
            entries = list(it)
    except OSError:
        return False
    for e in entries:
        if _is_secret_name(e.name):
            return True
    if depth <= 1:
        return False
    for e in entries:
        if e.name in _SCAN_SKIP:
            continue
        try:
            if e.is_dir(follow_symlinks=False) and _has_secret(e.path, depth - 1):
                return True
        except OSError:
            continue
    return False


# (workspace, root mtime) -> (expires_at, grants)
_plan_cache: dict = {}
_plan_lock = threading.Lock()


def _workspace_grants(root: str, depth: int = _SCAN_DEPTH) -> List[Tuple[str, bool]]:
    """[(path, recursive_rw)] covering *root* minus secret entries.

    A clean tree is one recursive grant. A tree holding a secret is granted
    entry by entry around it; its own directory gets listing only (False), so
    new top-level files there must be made with the file tools, not the shell.
    """
    if depth <= 0 or not _has_secret(root, depth):
        return [(root, True)]
    out: List[Tuple[str, bool]] = [(root, False)]
    try:
        with os.scandir(root) as it:
            entries = list(it)
    except OSError:
        return out
    for e in entries:
        if _is_secret_name(e.name):
            continue
        try:
            if e.is_dir(follow_symlinks=False):
                out.extend(_workspace_grants(e.path, depth - 1))
            elif e.is_file(follow_symlinks=False):
                out.append((e.path, True))
        except OSError:
            continue
    return out


def _cached_workspace_grants(root: str) -> List[Tuple[str, bool]]:
    try:
        key = (root, os.stat(root).st_mtime_ns)
    except OSError:
        return []
    now = time.monotonic()
    with _plan_lock:
        hit = _plan_cache.get(key)
        if hit and hit[0] > now:
            return hit[1]
    grants = _workspace_grants(root)
    with _plan_lock:
        if len(_plan_cache) > 64:
            _plan_cache.clear()
        _plan_cache[key] = (now + 30.0, grants)
    return grants


def _grant_except(rs: "_Ruleset", root: str, hidden: set, rights: int, prefix: str = "") -> None:
    """Grant *rights* on every entry of *root* except the relative paths in
    *hidden* (descending only as far as needed to carve them out)."""
    try:
        with os.scandir(root) as it:
            entries = list(it)
    except OSError:
        return
    rs.allow(root, FS_READ_DIR)
    for e in entries:
        rel = prefix + e.name
        if rel in hidden:
            continue
        if any(h.startswith(rel + "/") for h in hidden) and e.is_dir(follow_symlinks=False):
            _grant_except(rs, e.path, hidden, rights, rel + "/")
        else:
            rs.allow(e.path, rights)


def _python_ro_roots() -> List[str]:
    out = []
    for p in {sys.prefix, sys.base_prefix, os.path.dirname(os.path.realpath(sys.executable or ""))}:
        if p and p != "/":
            out.append(p)
    return out


# ── Ruleset construction ────────────────────────────────────────────────────
class _Ruleset:
    def __init__(self, abi: int, network: str, ports: Iterable[int]):
        self.abi = abi
        self.fs = _fs_rights(abi)
        attr = _RulesetAttr(handled_access_fs=self.fs, handled_access_net=0, scoped=0)
        size = 8
        if abi >= 4 and network != "any":
            attr.handled_access_net = NET_CONNECT_TCP
            size = 16
        if abi >= 6:
            attr.scoped = SCOPE_ABSTRACT_UNIX | SCOPE_SIGNAL
            size = 24
        fd = _syscall(_SYS_CREATE_RULESET, ctypes.byref(attr), ctypes.c_size_t(size), ctypes.c_uint32(0))
        if fd < 0:
            raise JailUnavailable(f"landlock_create_ruleset failed: {os.strerror(ctypes.get_errno())}")
        self.fd = int(fd)
        if attr.handled_access_net and network == "web":
            for port in sorted(set(int(p) for p in ports if 0 < int(p) < 65536)):
                na = _NetPortAttr(allowed_access=NET_CONNECT_TCP, port=port)
                if _syscall(_SYS_ADD_RULE, self.fd, _RULE_NET_PORT, ctypes.byref(na), ctypes.c_uint32(0)) < 0:
                    self.close()
                    raise JailUnavailable(f"landlock net rule failed: {os.strerror(ctypes.get_errno())}")

    def allow(self, path: str, rights: int) -> None:
        try:
            pfd = os.open(path, os.O_PATH | os.O_CLOEXEC)
        except OSError:
            return  # absent paths simply aren't granted
        try:
            if not os.path.isdir(path):
                rights &= _FILE_ONLY
            rights &= self.fs
            if not rights:
                return
            pa = _path_beneath_attr(rights, pfd)
            if _syscall(_SYS_ADD_RULE, self.fd, _RULE_PATH_BENEATH, pa, ctypes.c_uint32(0)) < 0:
                raise JailUnavailable(f"landlock rule for {path} failed: {os.strerror(ctypes.get_errno())}")
        finally:
            os.close(pfd)

    def close(self) -> None:
        if self.fd >= 0:
            try:
                os.close(self.fd)
            except OSError:
                pass
            self.fd = -1


def build_ruleset(workspace: Optional[str] = None,
                  extra_rw: Iterable[str] = (),
                  extra_rw_files: Iterable[str] = (),
                  extra_ro_files: Iterable[str] = ()) -> _Ruleset:
    """Build (but don't apply) the jail ruleset. Caller must .close() it."""
    abi = landlock_abi()
    if abi <= 0:
        raise JailUnavailable("this kernel does not support Landlock; set agent_sandbox to "
                              "\"off\" to run agent commands unjailed")
    if workspace and is_protected_path(workspace):
        raise JailUnavailable(f"workspace {workspace} is a protected path (sandbox_protected_roots)")
    network = str(_setting("sandbox_network", "web")).strip().lower()
    if network not in ("web", "none", "any"):
        network = "web"
    extra_ports = _setting("sandbox_net_ports", [])
    ports = list(_WEB_PORTS) + [p for p in (extra_ports if isinstance(extra_ports, list) else [])
                                if isinstance(p, int)]
    rs = _Ruleset(abi, network, ports)
    try:
        ro = FS_EXECUTE | FS_READ_FILE | FS_READ_DIR
        rw = rs.fs
        for p in _SYSTEM_RO:
            rs.allow(p, ro)
        _grant_except(rs, "/etc", _ETC_HIDDEN, ro)
        for p in _python_ro_roots():
            rs.allow(p, ro)
        rs.allow("/dev", FS_READ_DIR)
        for p in _DEV_RW_FILES:
            rs.allow(p, FS_READ_FILE | FS_WRITE_FILE | FS_IOCTL_DEV)
        for p in _SYSTEM_RW:
            rs.allow(p, rw)
        rs.allow(scratch_home(), rw)
        extra_ro = _setting("sandbox_read_roots", [])
        for p in (extra_ro if isinstance(extra_ro, list) else []):
            rp = os.path.realpath(os.path.expanduser(str(p)))
            if not is_protected_path(rp):
                rs.allow(rp, ro)
        if workspace:
            for path, recursive in _cached_workspace_grants(os.path.realpath(workspace)):
                rs.allow(path, rw if recursive else (FS_READ_DIR | FS_EXECUTE))
        for p in extra_rw:
            rs.allow(os.path.realpath(p), rw)
        for p in extra_rw_files:
            rs.allow(os.path.realpath(p), FS_READ_FILE | FS_WRITE_FILE | FS_TRUNCATE)
        for p in extra_ro_files:
            rs.allow(os.path.realpath(p), FS_READ_FILE)
    except Exception:
        rs.close()
        raise
    return rs


def _make_preexec(fd: int, inner: Optional[Callable[[], None]]) -> Callable[[], None]:
    syscall, prctl = _syscall, _prctl  # bind now: nothing to import post-fork

    def _apply() -> None:
        if inner is not None:
            inner()
        if prctl(_PR_SET_NO_NEW_PRIVS, 1, 0, 0, 0) != 0:
            raise OSError(ctypes.get_errno(), "prctl(NO_NEW_PRIVS) failed")
        if syscall(_SYS_RESTRICT_SELF, fd, ctypes.c_uint32(0)) != 0:
            raise OSError(ctypes.get_errno(), "landlock_restrict_self failed")
    return _apply


@contextlib.contextmanager
def guard(inner_preexec: Optional[Callable[[], None]] = None, *,
          workspace: Optional[str] = None,
          use_active_workspace: bool = True,
          extra_rw: Iterable[str] = (),
          extra_rw_files: Iterable[str] = (),
          extra_ro_files: Iterable[str] = ()) -> Iterator[Optional[Callable[[], None]]]:
    """Yield the preexec_fn for one agent subprocess spawn.

    Spawn inside the `with` block: the ruleset fd is closed on exit. When the
    jail is off this yields *inner_preexec* unchanged. Raises JailUnavailable
    when the jail is on but can't be enforced (fail closed).
    """
    if not enabled():
        yield inner_preexec
        return
    if workspace is None and use_active_workspace:
        from src.tool_execution import get_active_workspace
        workspace = get_active_workspace()
    rs = build_ruleset(workspace, extra_rw, extra_rw_files, extra_ro_files)
    try:
        yield _make_preexec(rs.fd, inner_preexec)
    finally:
        rs.close()


def jail_env(env: dict) -> dict:
    """Point HOME (and caches that follow it) at the jail's scratch home, so
    tools don't fail trying to write the app's real home."""
    if not enabled():
        return env
    out = dict(env)
    home = scratch_home()
    out["HOME"] = home
    out.setdefault("XDG_CACHE_HOME", os.path.join(home, ".cache"))
    local_bin = os.path.join(home, ".local", "bin")  # where `pip install --user` lands
    out["PATH"] = local_bin + os.pathsep + out.get("PATH", os.defpath)
    out["MYAI_SANDBOX"] = "landlock"
    return out


def default_cwd() -> str:
    """cwd for a jailed command with no workspace bound (the data dir, the old
    default, is deliberately unreadable inside the jail)."""
    return scratch_home()


def describe() -> str:
    """One-line human description, for the agent's system prompt / diagnostics."""
    if not enabled():
        return "Agent commands run UNJAILED (agent_sandbox=off)."
    net = str(_setting("sandbox_network", "web")).strip().lower()
    net_txt = {"none": "no outbound TCP", "any": "unrestricted network"}.get(
        net, "outbound TCP to web ports (80/443/53) only")
    return ("Shell/python/test commands run in a Landlock jail: they can write only the "
            "bound workspace, $HOME (a scratch dir) and /tmp; the rest of the host, the "
            f"app's data and secrets are not visible; {net_txt}.")
