"""Workspace API - browse server directories to pick a tool workspace folder."""
import os
from fastapi import APIRouter, Request, HTTPException, Query

from src.auth_helpers import get_current_user, effective_user
from src.tool_security import owner_is_admin_or_single_user

# Cap entries returned per directory (mirrors filesystem_tools._CODENAV_MAX_HITS).
# A huge directory shouldn't dump thousands of rows into the picker; the user can
# type/paste a path to jump straight in instead.
_MAX_BROWSE_DIRS = 500


# Extensions the @-mention picker never offers: compiled artefacts, archives
# and media. read_file cannot render them, so they are noise in a file picker.
_UNMENTIONABLE_EXTS = (
    ".pyc", ".pyo", ".pyd", ".so", ".o", ".a", ".class", ".jar", ".war",
    ".zip", ".tar", ".gz", ".bz2", ".xz", ".7z", ".rar", ".whl", ".egg",
    ".png", ".jpg", ".jpeg", ".gif", ".bmp", ".ico", ".webp", ".svgz",
    ".mp4", ".webm", ".mov", ".mp3", ".wav", ".ogg", ".pdf",
    ".db", ".sqlite", ".sqlite3", ".bin", ".dat", ".lock", ".woff", ".woff2",
)


def setup_workspace_routes():
    router = APIRouter(prefix="/api/workspace", tags=["workspace"])

    def _require_workspace_admin(request: Request):
        """Gate every ProjectForge workspace endpoint behind admin/single-user.

        These routes read and write host files under the workspace data root and
        can prepare run envelopes, so they carry the same authorization as
        /browse and /vet. Login alone is not sufficient: a non-admin (including
        a self-registered LAN account) must not reach workspace state.
        """
        owner = effective_user(request)
        if not owner_is_admin_or_single_user(owner):
            raise HTTPException(status_code=403, detail="ProjectForge workspace is admin-only")
        return owner

    def _require_valid_request_id(request_id: str):
        """Reject path-control characters in a request_id used to build a file path.

        Mirrors the run_id guard. The route's path converter already blocks '/',
        but this rejects '..', backslashes, and any out-of-charset input as
        defense-in-depth before the id is interpolated into a filename.
        """
        import re as _re
        if (not request_id or ".." in request_id or "/" in request_id
                or "\\" in request_id or not _re.match(r"^[A-Za-z0-9_.:-]+$", str(request_id))):
            raise HTTPException(status_code=400, detail="invalid request_id")
        return request_id

    @router.get("/browse")
    def browse(request: Request, path: str = Query(default="")):
        """List subdirectories of `path` (default: home) so the UI can navigate
        the server filesystem and pick a workspace folder. Directories only.

        ADMIN-ONLY: this enumerates the server filesystem, so it is gated the
        same way the file/shell tools are (read_file/write_file/bash are in
        NON_ADMIN_BLOCKED_TOOLS). A non-admin who can't use those tools must not
        be able to map the host's directory tree either.
        """
        owner = effective_user(request)
        if not owner_is_admin_or_single_user(owner):
            raise HTTPException(status_code=403, detail="Workspace browsing is admin-only")

        # Resolve symlinks so the reported path is canonical and the UI navigates
        # real directories (defends against symlink games in displayed paths).
        target = os.path.realpath(os.path.expanduser(path.strip() or "~"))
        if not os.path.isdir(target):
            target = os.path.realpath(os.path.expanduser("~"))

        dirs = []
        try:
            with os.scandir(target) as it:
                for entry in it:
                    try:
                        # Don't follow symlinks when classifying - a symlinked
                        # dir is skipped rather than letting the browser wander
                        # off via a link. Hidden entries are omitted.
                        if entry.is_dir(follow_symlinks=False) and not entry.name.startswith("."):
                            # Build the child path server-side with os.path.join
                            # so it's correct on Windows (backslashes) and Linux.
                            dirs.append({"name": entry.name, "path": os.path.join(target, entry.name)})
                    except OSError:
                        continue
        except (PermissionError, OSError):
            dirs = []

        dirs_sorted = sorted(dirs, key=lambda d: d["name"].lower())
        truncated = len(dirs_sorted) > _MAX_BROWSE_DIRS
        parent = os.path.dirname(target)
        from src.tool_execution import vet_workspace
        return {
            "path": target,
            "parent": parent if parent and parent != target else None,
            "dirs": dirs_sorted[:_MAX_BROWSE_DIRS],
            "truncated": truncated,
            # Whether this directory may be bound as a workspace (filesystem
            # roots and sensitive dirs may be browsed through but not chosen).
            "selectable": vet_workspace(target) is not None,
        }

    @router.get("/files")
    def list_files(request: Request,
                   workspace: str = Query(default=""),
                   q: str = Query(default=""),
                   limit: int = Query(default=30)):
        """Search FILES inside a bound workspace, for the composer's @-mention.

        Distinct from /browse, which lists directories anywhere on the host so a
        workspace can be picked. Results here never leave the given folder: it is
        re-vetted on arrival (it comes from the client) and paths come back
        RELATIVE to it.

        Scope, stated honestly: the gate is admin + vet_workspace, i.e. exactly
        the set of folders that may be BOUND as a workspace for the agent's file
        tools. Listing files in such a folder is no more than the agent's own
        ls/glob would return once bound, and /browse already lets an admin walk
        the host's directory tree. This adds no reach beyond existing policy.

        Prefers `git ls-files` so the project's own .gitignore decides what is
        searchable — otherwise a repo with a large build directory or vendored
        dependencies drowns the real source. Falls back to a bounded walk.

        ADMIN-ONLY, matching /browse: a caller who cannot use read_file must not
        be able to enumerate the project either.
        """
        owner = effective_user(request)
        if not owner_is_admin_or_single_user(owner):
            raise HTTPException(status_code=403, detail="Workspace file search is admin-only")

        from src.tool_execution import vet_workspace
        root = vet_workspace(os.path.expanduser((workspace or "").strip())) if workspace else None
        if not root:
            raise HTTPException(status_code=400, detail="a valid workspace is required")

        needle = (q or "").strip().lower()
        try:
            limit = max(1, min(int(limit), 100))
        except (TypeError, ValueError):
            limit = 30

        rels: list[str] = []
        try:
            import subprocess as _sp
            p = _sp.run(["git", "-C", root, "ls-files", "--cached", "--others",
                         "--exclude-standard"],
                        capture_output=True, text=True, timeout=10)
            if p.returncode == 0:
                rels = [ln.strip() for ln in (p.stdout or "").splitlines() if ln.strip()]
        except Exception:
            rels = []
        if not rels:
            # Same skip set as symbol search (src/agent_tools/symbol_tools.py):
            # build output AND directories that typically hold COPIES of the
            # source, so a project keeping dev-mirrors or backups doesn't offer
            # the same file several times from stale snapshots.
            from src.agent_tools.symbol_tools import _SKIP_DIRS as skip
            for dp, dns, fns in os.walk(root):
                dns[:] = [d for d in dns if d not in skip and not d.startswith(".")]
                for fn in fns:
                    if fn.startswith("."):
                        continue
                    rels.append(os.path.relpath(os.path.join(dp, fn), root))
                    if len(rels) >= 20000:      # bounded: never walk forever
                        break
                if len(rels) >= 20000:
                    break

        # Drop compiled/binary/media files: read_file cannot usefully show them,
        # so offering them in an @-mention picker is pure noise (and a stray
        # .pyc can outrank the source file it was built from).
        rels = [r for r in rels if not r.lower().endswith(_UNMENTIONABLE_EXTS)]

        if needle:
            # Rank basename matches above path matches — typing "chat" should
            # offer chat.py before deep/nested/other/chatty_helper.py.
            exact, partial = [], []
            for r in rels:
                base = os.path.basename(r).lower()
                if needle in base:
                    exact.append(r)
                elif needle in r.lower():
                    partial.append(r)
            matches = sorted(exact, key=len) + sorted(partial, key=len)
        else:
            matches = sorted(rels, key=len)

        return {"workspace": root, "files": matches[:limit],
                "truncated": len(matches) > limit}

    @router.get("/vet")
    def vet(request: Request, path: str = Query(default="")):
        """Validate a workspace path without binding it.

        The UI calls this before persisting a manually typed path (/workspace
        set) so a typo, file path, deleted folder, sensitive dir, or filesystem
        root is rejected up front with the canonical path returned on success,
        instead of being stored client-side and silently dropped at chat time.
        Admin-gated like /browse: it confirms path existence on the host.
        """
        owner = effective_user(request)
        if not owner_is_admin_or_single_user(owner):
            raise HTTPException(status_code=403, detail="Workspace selection is admin-only")
        from src.tool_execution import vet_workspace
        resolved = vet_workspace(path)
        return {"ok": resolved is not None, "path": resolved}

    # ProjectForge Workspace Planner MVP
    def _pf_workspace_data_root():
        from pathlib import Path
        import os
        # In container this is /app/data; on host fallback stays local.
        return Path(os.environ.get("DATA_DIR", "/app/data"))

    def _pf_workspace_now():
        from datetime import datetime, timezone
        return datetime.now(timezone.utc).isoformat(timespec="seconds")

    def _pf_workspace_slug(value: str) -> str:
        import re
        value = (value or "").strip().lower()
        value = re.sub(r"[^a-z0-9]+", "_", value).strip("_")
        return value[:80] or "request"

    def _pf_workspace_classify(prompt: str) -> dict:
        p = (prompt or "").lower()
        if any(x in p for x in ["canvas", "game", "enemy", "projectile", "wave", "hud"]):
            kind = "web_game"
            complexity = "moderate"
            risk = "medium"
        elif any(x in p for x in ["debug", "broken", "refactor", "traceback", "error", "failing", "repair"]):
            kind = "debug_repair"
            complexity = "moderate"
            risk = "high"
        elif any(x in p for x in ["architecture", "system", "backend", "api", "memory", "registry", "orchestration"]):
            kind = "complex_architecture"
            complexity = "complex"
            risk = "medium"
        elif any(x in p for x in ["self", "improve", "dedupe", "knowledge", "skill", "maintenance"]):
            kind = "self_maintenance"
            complexity = "moderate"
            risk = "medium"
        elif any(x in p for x in ["review", "diff", "pull request", "code review", "security"]):
            kind = "code_review"
            complexity = "moderate"
            risk = "medium"
        elif any(x in p for x in ["web app", "app", "frontend", "form", "dashboard", "tracker"]):
            kind = "greenfield_web_app"
            complexity = "simple"
            risk = "medium"
        else:
            kind = "general_local_coding"
            complexity = "unknown"
            risk = "medium"
        return {
            "request_type": kind,
            "complexity": complexity,
            "risk_level": risk,
            "local_only": True,
            "git_sync_allowed": False
        }

    def _pf_workspace_team(kind: str) -> list[str]:
        teams = {
            "greenfield_web_app": [
                "projectforge-sme-human-prompt-clarifier",
                "projectforge-sme-product-requirements-planner",
                "projectforge-sme-simple-solution-architect",
                "projectforge-sme-greenfield-software-builder",
                "projectforge-sme-web-app-engineer",
                "projectforge-sme-test-and-quality-engineer",
                "projectforge-sme-run-guard-plan"
            ],
            "web_game": [
                "projectforge-sme-web-game-engineer",
                "projectforge-sme-build-plan-architect",
                "projectforge-sme-test-and-quality-engineer",
                "projectforge-sme-run-guard-plan"
            ],
            "debug_repair": [
                "projectforge-sme-debugging-repair-engineer",
                "projectforge-sme-code-reviewer",
                "projectforge-sme-test-and-quality-engineer",
                "projectforge-sme-source-of-truth-arbiter"
            ],
            "complex_architecture": [
                "projectforge-sme-complex-solution-architect",
                "projectforge-sme-backend-api-engineer",
                "projectforge-sme-state-and-data-engineer",
                "projectforge-sme-local-runtime-devops",
                "projectforge-sme-self-system-maintainer"
            ],
            "self_maintenance": [
                "projectforge-sme-self-system-maintainer",
                "projectforge-sme-knowledge-card-builder",
                "projectforge-sme-documentation-turnover-engineer",
                "projectforge-sme-source-of-truth-arbiter",
                "projectforge-sme-local-runtime-devops"
            ],
            "code_review": [
                "projectforge-sme-code-reviewer",
                "projectforge-sme-simple-solution-architect",
                "projectforge-sme-test-and-quality-engineer",
                "projectforge-sme-source-of-truth-arbiter"
            ],
            "general_local_coding": [
                "projectforge-sme-all-source-router",
                "projectforge-sme-human-prompt-clarifier",
                "projectforge-sme-build-plan-architect",
                "projectforge-sme-test-and-quality-engineer"
            ]
        }
        return teams.get(kind, teams["general_local_coding"])

    def _pf_workspace_evidence(kind: str) -> list[str]:
        base = [
            "target path or intended local workspace",
            "expected behavior",
            "acceptance criteria",
            "rollback preference"
        ]
        if kind == "debug_repair":
            return [
                "failing command",
                "full error output",
                "changed files or diff",
                "expected behavior",
                "actual behavior",
                "last known-good state"
            ]
        if kind == "code_review":
            return [
                "actual diff or changed files",
                "test output",
                "risk areas to prioritize",
                "expected acceptance criteria"
            ]
        return base

    def _pf_workspace_guard_plan(kind: str) -> dict:
        return {
            "mode": "planner_first",
            "automatic_execution": False,
            "checks": [
                "local_only=true",
                "git_sync_allowed=false",
                "forbidden tokens absent: v15, game_v15",
                "owner metadata present",
                "source metadata present",
                "evidence requirements reviewed",
                "rollback path defined",
                "verification commands defined"
            ],
            "verification_commands": [
                "git status --short --ignored data workspace static/brain/projectforge_sme docker-compose.override.yml | head -120",
                "curl -fsS http://127.0.0.1:7000/api/workspace/health",
                "curl -fsS http://127.0.0.1:7000/static/brain/projectforge_sme/projectforge_sme_knowledge.json | head -20"
            ]
        }

    def _pf_workspace_task_packet(request_id: str, prompt: str, classification: dict, team: list[str]) -> dict:
        kind = classification.get("request_type", "general_local_coding")
        return {
            "id": request_id,
            "type": "projectforge_workspace_task_packet",
            "prompt": prompt,
            "classification": classification,
            "selected_skills": team,
            "evidence_requirements": _pf_workspace_evidence(kind),
            "execution_policy": {
                "automatic_execution": False,
                "requires_operator_approval": True,
                "local_only": True,
                "git_sync_allowed": False,
                "feature_ladder_closed_at": "v13_verified",
                "final_boundary": "v14",
                "forbidden": ["v15", "game_v15"]
            },
            "recommended_next_step": "Review the packet and evidence requirements before creating any run envelope or executing agents."
        }

    def _pf_workspace_write_json(path, payload):
        import json
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")

    @router.get("/health")
    async def projectforge_workspace_health(request: Request):
        _require_workspace_admin(request)
        root = _pf_workspace_data_root()
        workspace_root = root / "workspace"
        return {
            "ok": True,
            "service": "projectforge_workspace_planner",
            "mode": "planner_first",
            "automatic_execution": False,
            "owner_default": "admin",
            "data_root": str(root),
            "workspace_root": str(workspace_root),
            "policy": {
                "local_only": True,
                "git_sync_allowed": False,
                "feature_ladder_closed_at": "v13_verified",
                "final_boundary": "v14",
                "forbidden": ["v15", "game_v15"]
            }
        }

    @router.post("/plan")
    async def projectforge_workspace_plan(request: Request):
        _require_workspace_admin(request)
        import hashlib
        try:
            body = await request.json()
        except Exception:
            body = {}
        prompt = str(body.get("prompt") or "").strip()
        if not prompt:
            raise HTTPException(status_code=400, detail="prompt is required")

        now = _pf_workspace_now()
        digest = hashlib.sha256(prompt.encode("utf-8")).hexdigest()[:10]
        request_id = f"ws_{now.replace(':','').replace('-','').replace('+','z')}_{digest}"
        classification = _pf_workspace_classify(prompt)
        kind = classification["request_type"]
        team = _pf_workspace_team(kind)
        task_packet = _pf_workspace_task_packet(request_id, prompt, classification, team)
        guard_plan = _pf_workspace_guard_plan(kind)

        record = {
            "id": request_id,
            "owner": "admin",
            "source": "workspace",
            "category": "projectforge_workspace_request",
            "prompt": prompt,
            "classification": classification,
            "selected_skills": team,
            "evidence_requirements": _pf_workspace_evidence(kind),
            "task_packet": task_packet,
            "guard_plan": guard_plan,
            "created_at": now,
            "updated_at": now,
            "local_only": True,
            "git_sync_allowed": False,
            "policy": {
                "feature_ladder_closed_at": "v13_verified",
                "final_boundary": "v14",
                "forbidden": ["v15", "game_v15"]
            }
        }

        root = _pf_workspace_data_root() / "workspace"
        _pf_workspace_write_json(root / "requests" / f"{request_id}.json", record)
        _pf_workspace_write_json(root / "task_packets" / f"{request_id}.json", task_packet)
        _pf_workspace_write_json(root / "guard_plans" / f"{request_id}.json", guard_plan)
        return record

    @router.get("/requests")
    async def projectforge_workspace_requests(request: Request):
        _require_workspace_admin(request)
        import json
        root = _pf_workspace_data_root() / "workspace" / "requests"
        items = []
        if root.exists():
            for p in sorted(root.glob("*.json"), reverse=True)[:100]:
                try:
                    obj = json.loads(p.read_text())
                    items.append({
                        "id": obj.get("id"),
                        "created_at": obj.get("created_at"),
                        "classification": obj.get("classification", {}),
                        "prompt_preview": str(obj.get("prompt", ""))[:160]
                    })
                except Exception:
                    continue
        return {"ok": True, "count": len(items), "items": items}

    @router.get("/requests/{request_id}")
    async def projectforge_workspace_request_detail(request_id: str, request: Request):
        _require_workspace_admin(request)
        _require_valid_request_id(request_id)
        import json
        root = _pf_workspace_data_root() / "workspace" / "requests"
        path = root / f"{request_id}.json"
        if not path.exists():
            raise HTTPException(status_code=404, detail="workspace request not found")
        return json.loads(path.read_text())

    # ProjectForge Workspace V2 approval/edit endpoints
    @router.put("/requests/{request_id}/task_packet")
    async def projectforge_workspace_update_task_packet(request_id: str, request: Request):
        _require_workspace_admin(request)
        _require_valid_request_id(request_id)
        import json
        from datetime import datetime, timezone
        root = _pf_workspace_data_root() / "workspace"
        request_path = root / "requests" / f"{request_id}.json"
        packet_path = root / "task_packets" / f"{request_id}.json"
        if not request_path.exists():
            raise HTTPException(status_code=404, detail="workspace request not found")
        try:
            body = await request.json()
        except Exception:
            body = {}
        task_packet = body.get("task_packet")
        if task_packet is None:
            raise HTTPException(status_code=400, detail="task_packet is required")

        now = datetime.now(timezone.utc).isoformat(timespec="seconds")
        record = json.loads(request_path.read_text())
        record["task_packet"] = task_packet
        record["updated_at"] = now
        record["local_only"] = True
        record["git_sync_allowed"] = False
        packet_path.write_text(json.dumps(task_packet, indent=2, sort_keys=True) + "\n")
        request_path.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n")
        return {"ok": True, "id": request_id, "updated_at": now, "task_packet": task_packet}

    @router.put("/requests/{request_id}/guard_plan")
    async def projectforge_workspace_update_guard_plan(request_id: str, request: Request):
        _require_workspace_admin(request)
        _require_valid_request_id(request_id)
        import json
        from datetime import datetime, timezone
        root = _pf_workspace_data_root() / "workspace"
        request_path = root / "requests" / f"{request_id}.json"
        guard_path = root / "guard_plans" / f"{request_id}.json"
        if not request_path.exists():
            raise HTTPException(status_code=404, detail="workspace request not found")
        try:
            body = await request.json()
        except Exception:
            body = {}
        guard_plan = body.get("guard_plan")
        if guard_plan is None:
            raise HTTPException(status_code=400, detail="guard_plan is required")

        now = datetime.now(timezone.utc).isoformat(timespec="seconds")
        record = json.loads(request_path.read_text())
        record["guard_plan"] = guard_plan
        record["updated_at"] = now
        record["local_only"] = True
        record["git_sync_allowed"] = False
        guard_path.write_text(json.dumps(guard_plan, indent=2, sort_keys=True) + "\n")
        request_path.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n")
        return {"ok": True, "id": request_id, "updated_at": now, "guard_plan": guard_plan}

    @router.post("/requests/{request_id}/approve")
    async def projectforge_workspace_approve_guarded_run(request_id: str, request: Request):
        _require_workspace_admin(request)
        _require_valid_request_id(request_id)
        import json
        from datetime import datetime, timezone
        root = _pf_workspace_data_root() / "workspace"
        request_path = root / "requests" / f"{request_id}.json"
        if not request_path.exists():
            raise HTTPException(status_code=404, detail="workspace request not found")

        try:
            body = await request.json()
        except Exception:
            body = {}

        now = datetime.now(timezone.utc).isoformat(timespec="seconds")
        record = json.loads(request_path.read_text())
        approval = {
            "id": request_id,
            "approved_at": now,
            "approved_by": "admin",
            "status": "approved_for_guarded_run_preparation",
            "automatic_execution": False,
            "operator_note": body.get("operator_note", ""),
            "policy": {
                "local_only": True,
                "git_sync_allowed": False,
                "automatic_execution": False,
                "feature_ladder_closed_at": "v13_verified",
                "final_boundary": "v14",
                "forbidden": ["v15", "game_v15"]
            },
            "message": "Approval marker created. This does not execute agents."
        }

        approvals = root / "approvals"
        approvals.mkdir(parents=True, exist_ok=True)
        (approvals / f"{request_id}.json").write_text(json.dumps(approval, indent=2, sort_keys=True) + "\n")

        record["approval"] = approval
        record["approval_status"] = approval["status"]
        record["updated_at"] = now
        record["local_only"] = True
        record["git_sync_allowed"] = False
        request_path.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n")
        return {"ok": True, "id": request_id, "approval": approval}

    # ProjectForge Workspace V3 Phase B backend endpoint


    def _pf_workspace_operator_visible_path(value):
        text = str(value or "")
        if text == "/app/data":
            return "/home/youruser/odysseus/data"
        if text.startswith("/app/data/"):
            return "/home/youruser/odysseus/data/" + text[len("/app/data/"):]
        return text

    def _pf_workspace_find_run_dir(run_id: str):
        if not run_id or "/" in run_id or "\\" in run_id or ".." in run_id:
            raise HTTPException(status_code=400, detail="invalid run id")
        run_dir = _pf_workspace_data_root() / "workspace" / "run_envelopes" / run_id
        if not run_dir.exists():
            raise HTTPException(status_code=404, detail="run envelope not found")
        return run_dir

    def _pf_workspace_manual_status_path(run_dir):
        return run_dir / "manual_execution_status.json"

    def _pf_workspace_read_manual_status(run_dir):
        json_mod = __import__("json")
        path = _pf_workspace_manual_status_path(run_dir)
        if not path.exists():
            return {
                "manual_status": "manual_run_not_started",
                "browser_executes_commands": False,
                "updated_at": None,
                "note": "",
            }
        try:
            data = json_mod.loads(path.read_text(encoding="utf-8"))
        except Exception:
            data = {}
        return {
            "manual_status": data.get("manual_status") or "manual_run_not_started",
            "browser_executes_commands": False,
            "updated_at": data.get("updated_at"),
            "note": data.get("note") or "",
        }

    def _pf_workspace_manual_execution_checklist(run_dir, run_id: str):
        visible = _pf_workspace_operator_visible_path(str(run_dir))
        return [
            "Review request_snapshot.json",
            "Review task_packet.json",
            "Review guard_plan.json",
            "Review operator_instructions.md",
            f"Run manually only if desired: cd {visible} && bash preflight.sh",
            "Manually decide whether any implementation work is appropriate",
            f"After any manual work, run manually: cd {visible} && bash post_run_guard.sh",
            "Confirm no forbidden v15/game_v15 work was introduced",
            "Confirm local-only Git state remains expected",
        ]

    def _pf_workspace_manual_command_block(run_dir):
        visible = _pf_workspace_operator_visible_path(str(run_dir))
        return "\n".join([
            f"cd {visible}",
            "",
            "echo '=== review request snapshot ==='",
            "jq . request_snapshot.json",
            "",
            "echo '=== review task packet ==='",
            "jq . task_packet.json",
            "",
            "echo '=== review guard plan ==='",
            "jq . guard_plan.json",
            "",
            "echo '=== review operator instructions ==='",
            "sed -n '1,240p' operator_instructions.md",
            "",
            "echo '=== manual preflight ==='",
            "bash preflight.sh",
            "",
            "echo '=== manual implementation decision point ==='",
            "echo 'No implementation command is generated by the browser.'",
            "echo 'Operator must decide and type any implementation commands manually.'",
            "",
            "echo '=== post-run guard after any manual work ==='",
            "bash post_run_guard.sh",
        ])

    @router.get("/run_envelopes")
    async def projectforge_workspace_run_envelopes(request: Request):
        """Read-only Workspace run-envelope history.

        This endpoint exposes prepared run-envelope metadata and copyable manual
        commands only. It does not execute preflight, agents, shell commands, or
        Git operations.
        """
        _require_workspace_admin(request)
        workspace_root = _pf_workspace_data_root() / "workspace"
        run_root = workspace_root / "run_envelopes"

        def operator_visible_path(value):
            text = str(value or "")
            if text == "/app/data":
                return "/home/youruser/odysseus/data"
            if text.startswith("/app/data/"):
                return "/home/youruser/odysseus/data/" + text[len("/app/data/"):]
            return text

        def path_mtime(path):
            try:
                return path.stat().st_mtime
            except OSError:
                return 0

        items = []
        if run_root.exists():
            run_paths = sorted(
                run_root.glob("*/run_envelope.json"),
                key=path_mtime,
                reverse=True,
            )

            for path in run_paths[:25]:
                try:
                    payload = __import__("json").loads(path.read_text(encoding="utf-8"))
                except Exception:
                    continue

                run_dir = operator_visible_path(payload.get("run_dir") or str(path.parent))
                item = {
                    "id": payload.get("id") or path.parent.name,
                    "request_id": payload.get("request_id"),
                    "status": payload.get("status") or "unknown",
                    "run_dir": run_dir,
                    "run_envelope_path": operator_visible_path(str(path)),
                    "created_at": payload.get("created_at") or path.parent.name.rsplit("_", 1)[-1],
                    "automatic_execution": bool(payload.get("automatic_execution", False)),
                    "local_only": bool(payload.get("local_only", False)),
                    "git_sync_allowed": bool(payload.get("git_sync_allowed", False)),
                    "preflight_command": f"cd {run_dir} && bash preflight.sh" if run_dir else "",
                    "post_run_guard_command": f"cd {run_dir} && bash post_run_guard.sh" if run_dir else "",
                    "manual_execution_checklist": _pf_workspace_manual_execution_checklist(path.parent, payload.get("id") or path.parent.name),
                    "manual_command_block": _pf_workspace_manual_command_block(path.parent),
                    "manual_status": _pf_workspace_read_manual_status(path.parent).get("manual_status"),
                    "browser_executes_commands": False,
                }
                items.append(item)

        return {
            "items": items,
            "policy": {
                "automatic_execution": False,
                "local_only": True,
                "git_sync_allowed": False,
                "browser_executes_commands": False,
            },
        }


    # ProjectForge Workspace V3 Phase F Part 4 artifact/result inventory
    _PFWS_ARTIFACT_TEXT_EXTS = {
        ".json", ".jsonl", ".txt", ".md", ".log", ".diff", ".patch", ".sh", ".yaml", ".yml", ".html"
    }
    _PFWS_ARTIFACT_MAX_ITEMS = 250
    _PFWS_ARTIFACT_MAX_PREVIEW_BYTES = 256 * 1024
    _PFWS_ARTIFACT_MAX_SCAN_BYTES = 8 * 1024 * 1024


    def _pfws_phase_f4_http_error(status_code, detail):
        from fastapi import HTTPException
        return HTTPException(status_code=status_code, detail=detail)


    def _pfws_phase_f4_path_cls():
        from pathlib import Path
        return Path


    def _pfws_phase_f4_runs_root():
        Path = _pfws_phase_f4_path_cls()

        candidates = []

        for name in ("RUNS", "RUN_ENVELOPES", "RUN_ENVELOPES_DIR"):
            try:
                value = globals().get(name)
                if value:
                    candidates.append(Path(value))
            except Exception:
                pass

        candidates.extend([
            Path("/app/data/workspace/run_envelopes"),
            Path("data/workspace/run_envelopes"),
            Path("/home/youruser/odysseus/data/workspace/run_envelopes"),
        ])

        for candidate in candidates:
            try:
                if candidate.exists() and candidate.is_dir():
                    return candidate.resolve()
            except Exception:
                continue

        return Path("data/workspace/run_envelopes").resolve()


    def _pfws_phase_f4_safe_run_dir(run_id):
        import re as _re

        if not run_id or not _re.match(r"^[A-Za-z0-9_.:-]+$", str(run_id)):
            raise _pfws_phase_f4_http_error(400, "Invalid run_id.")

        root = _pfws_phase_f4_runs_root()

        try:
            run_dir = (root / str(run_id)).resolve()
        except Exception:
            raise _pfws_phase_f4_http_error(400, "Invalid run path.")

        if root != run_dir and root not in run_dir.parents:
            raise _pfws_phase_f4_http_error(400, "Invalid run path.")

        if not run_dir.exists() or not run_dir.is_dir():
            raise _pfws_phase_f4_http_error(404, "Run envelope not found.")

        return root, run_dir


    def _pfws_phase_f4_kind(path):
        name = path.name.lower()
        suffix = path.suffix.lower()

        if name in {"result.json", "summary.json"}:
            return "result"
        if name in {"trajectory.json", "trajectory.jsonl"}:
            return "trajectory"
        if name in {"final.diff", "diff.patch"} or suffix in {".diff", ".patch"}:
            return "diff"
        if name == "run_envelope.json":
            return "run_envelope"
        if name in {"request_snapshot.json", "task_packet.json", "guard_plan.json"}:
            return "planning_metadata"
        if name in {"operator_instructions.md", "readme.md"} or suffix == ".md":
            return "instructions"
        if suffix == ".sh":
            return "manual_script_text"
        if suffix in {".log", ".txt"}:
            return "log"
        if suffix in {".json", ".jsonl"}:
            return "json"
        return "artifact"


    def _pfws_phase_f4_priority(item):
        kind_order = {
            "result": 0,
            "run_envelope": 1,
            "planning_metadata": 2,
            "instructions": 3,
            "trajectory": 4,
            "diff": 5,
            "log": 6,
            "manual_script_text": 7,
            "json": 8,
            "artifact": 9,
        }
        return (kind_order.get(item.get("kind"), 99), item.get("path", ""))


    def _pfws_phase_f4_preview(path, size):
        suffix = path.suffix.lower()
        if suffix not in _PFWS_ARTIFACT_TEXT_EXTS:
            return None

        if size > _PFWS_ARTIFACT_MAX_SCAN_BYTES:
            return None

        try:
            raw = path.read_bytes()[:_PFWS_ARTIFACT_MAX_PREVIEW_BYTES]
        except Exception:
            return None

        if b"\x00" in raw[:4096]:
            return None

        try:
            return raw.decode("utf-8", errors="replace")
        except Exception:
            return None


    @router.get("/run_envelopes/{run_id}/artifacts")
    async def get_run_envelope_artifacts(run_id: str, request: Request):
        _require_workspace_admin(request)
        root, run_dir = _pfws_phase_f4_safe_run_dir(run_id)

        items = []
        scanned = 0
        skipped = 0

        try:
            paths = sorted(run_dir.rglob("*"), key=lambda p: p.as_posix())
        except Exception as exc:
            raise _pfws_phase_f4_http_error(500, f"Artifact scan failed: {exc}")

        for path in paths:
            try:
                if path.is_symlink():
                    skipped += 1
                    continue

                if not path.is_file():
                    continue

                resolved = path.resolve()
                if run_dir != resolved and run_dir not in resolved.parents:
                    skipped += 1
                    continue

                rel = path.relative_to(run_dir).as_posix()
                if any(part.startswith(".") for part in rel.split("/")):
                    skipped += 1
                    continue

                scanned += 1
                if len(items) >= _PFWS_ARTIFACT_MAX_ITEMS:
                    break

                stat = path.stat()
                size = int(stat.st_size)
                kind = _pfws_phase_f4_kind(path)
                preview = _pfws_phase_f4_preview(path, size)

                items.append({
                    "path": rel,
                    "name": path.name,
                    "kind": kind,
                    "size_bytes": size,
                    "mtime": int(stat.st_mtime),
                    "preview": preview,
                    "preview_truncated": bool(preview is not None and size > _PFWS_ARTIFACT_MAX_PREVIEW_BYTES),
                    "copy_only": True,
                })
            except Exception:
                skipped += 1
                continue

        items.sort(key=_pfws_phase_f4_priority)

        return {
            "run_id": run_id,
            "run_dir": str(run_dir),
            "runs_root": str(root),
            "artifact_count": len(items),
            "scanned_file_count": scanned,
            "skipped_file_count": skipped,
            "max_items": _PFWS_ARTIFACT_MAX_ITEMS,
            "read_only": True,
            "browser_executes_commands": False,
            "automatic_execution": False,
            "items": items,
        }

    @router.get("/run_envelopes/{run_id}/manual_status")
    async def projectforge_workspace_get_manual_status(run_id: str, request: Request):
        _require_workspace_admin(request)
        """Read manual execution metadata only. Does not execute commands."""
        run_dir = _pf_workspace_find_run_dir(run_id)
        status = _pf_workspace_read_manual_status(run_dir)
        status["run_id"] = run_id
        status["run_dir"] = _pf_workspace_operator_visible_path(str(run_dir))
        status["manual_execution_checklist"] = _pf_workspace_manual_execution_checklist(run_dir, run_id)
        status["manual_command_block"] = _pf_workspace_manual_command_block(run_dir)
        return status

    @router.put("/run_envelopes/{run_id}/manual_status")
    async def projectforge_workspace_put_manual_status(run_id: str, request: Request):
        _require_workspace_admin(request)
        """Write manual execution metadata only. Does not execute commands."""
        json_mod = __import__("json")
        run_dir = _pf_workspace_find_run_dir(run_id)
        try:
            body = await request.json()
        except Exception:
            body = {}
        if not isinstance(body, dict):
            raise HTTPException(status_code=400, detail="invalid request body")

        allowed = {
            "manual_run_not_started",
            "manual_run_started",
            "manual_run_completed",
        }

        manual_status = body.get("manual_status")
        if manual_status not in allowed:
            raise HTTPException(status_code=400, detail="invalid manual status")

        note = str(body.get("note") or "")[:1000]
        payload = {
            "run_id": run_id,
            "run_dir": _pf_workspace_operator_visible_path(str(run_dir)),
            "manual_status": manual_status,
            "note": note,
            "browser_executes_commands": False,
            "automatic_execution": False,
            "local_only": True,
            "git_sync_allowed": False,
            "updated_at": _pf_workspace_now(),
        }

        path = _pf_workspace_manual_status_path(run_dir)
        path.write_text(json_mod.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        return payload


    @router.post("/requests/{request_id}/prepare_run_envelope")
    async def projectforge_workspace_prepare_run_envelope_from_ui(request_id: str, request: Request):
        _require_workspace_admin(request)
        _require_valid_request_id(request_id)
        import json
        import subprocess
        from pathlib import Path

        root = _pf_workspace_data_root()
        workspace_root = root / "workspace"
        request_path = workspace_root / "requests" / f"{request_id}.json"
        tool_path = root / "projectforge_sme" / "workspace_feature" / "tools" / "prepare_workspace_run_envelope.py"

        if not request_path.exists():
            raise HTTPException(status_code=404, detail="workspace request not found")

        if not tool_path.exists():
            raise HTTPException(status_code=500, detail=f"run envelope tool not found: {tool_path}")

        try:
            request_record = json.loads(request_path.read_text(errors="replace"))
        except Exception as exc:
            raise HTTPException(status_code=500, detail=f"could not read workspace request: {exc}")

        if request_record.get("approval_status") != "approved_for_guarded_run_preparation":
            raise HTTPException(
                status_code=409,
                detail="request must be approved_for_guarded_run_preparation before preparing a run envelope"
            )

        # This invokes the verified local Python envelope generator only.
        # It does not execute agents, does not run preflight, and does not run shell=True.
        proc = subprocess.run(
            ["python3", str(tool_path), "--request-id", request_id],
            cwd=str(root),
            text=True,
            capture_output=True,
            timeout=30,
            check=False,
        )

        if proc.returncode != 0:
            raise HTTPException(
                status_code=500,
                detail={
                    "message": "run envelope preparation failed",
                    "returncode": proc.returncode,
                    "stdout": proc.stdout[-4000:],
                    "stderr": proc.stderr[-4000:],
                },
            )

        try:
            envelope = json.loads(proc.stdout)
        except Exception as exc:
            raise HTTPException(
                status_code=500,
                detail={
                    "message": f"run envelope tool returned non-json output: {exc}",
                    "stdout": proc.stdout[-4000:],
                    "stderr": proc.stderr[-4000:],
                },
            )

        run_dir = envelope.get("run_dir")
        preflight = (envelope.get("files") or {}).get("preflight")

        return {
            "ok": True,
            "id": request_id,
            "run_envelope": envelope,
            "run_dir": run_dir,
            "preflight_command": f"cd {run_dir} && bash preflight.sh" if run_dir else None,
            "automatic_execution": False,
            "message": "Run envelope prepared. No agents, preflight, or shell implementation commands executed."
        }

    # ----- Per-session sandbox coding pipeline (admin-gated) -----
    # POST a coding prompt; the system generates + builds + tests the change in an
    # isolated per-session dev-mirror, then packages a patch for browser review.
    # Nothing touches the live repo until the operator reviews and approves.
    @router.post("/sandbox/build")
    async def sandbox_build(request: Request):
        owner = _require_workspace_admin(request)
        try:
            body = await request.json()
        except Exception:
            body = {}
        if not isinstance(body, dict):
            raise HTTPException(status_code=400, detail="invalid request body")
        prompt = str(body.get("prompt") or "").strip()
        if not prompt:
            raise HTTPException(status_code=400, detail="prompt is required")
        session_id = body.get("session_id")
        session_id = str(session_id) if session_id is not None else None
        try:
            max_rounds = int(body.get("max_rounds") or 40)
        except Exception:
            max_rounds = 40
        max_rounds = max(1, min(max_rounds, 100))
        # candidates>1 runs the design panel (best-of-N): N distinct candidate
        # solutions, tested, judge picks the best. temperature steers diversity.
        try:
            candidates = int(body.get("candidates") or 1)
        except Exception:
            candidates = 1
        candidates = max(1, min(candidates, 4))
        try:
            temperature = float(body.get("temperature"))
        except Exception:
            temperature = 0.6
        temperature = max(0.0, min(temperature, 1.2))

        # Resolve + enqueue via the shared launcher (one source of truth, also
        # used by the in-chat request_sandbox_build tool). It prefers the
        # originating session's endpoint/model, else the configured default, and
        # honors an admin-pinned model. Returns {"ok": False, ...} on failure.
        from src.workspace_request_executor import launch_sandbox_build
        result = await launch_sandbox_build(
            prompt, owner=owner, session_id=session_id, candidates=candidates,
            max_rounds=max_rounds, temperature=temperature,
            model=str(body.get("model")) if body.get("model") else None,
        )
        if not result.get("ok"):
            raise HTTPException(status_code=503, detail=result.get("error") or "sandbox build failed to start")
        return result

    @router.get("/sandbox/runs")
    async def sandbox_runs(request: Request):
        _require_workspace_admin(request)
        from src.workspace_request_executor import list_sandbox_statuses
        return {"items": list_sandbox_statuses(limit=25)}

    @router.get("/sandbox/health")
    async def sandbox_health_route(request: Request):
        _require_workspace_admin(request)
        from src.workspace_request_executor import sandbox_health
        return sandbox_health()

    @router.get("/sandbox/runs/{tracking_id}")
    async def sandbox_run_detail(tracking_id: str, request: Request):
        _require_workspace_admin(request)
        _require_valid_request_id(tracking_id)
        from src.workspace_request_executor import read_sandbox_status
        status = read_sandbox_status(tracking_id)
        if not status:
            raise HTTPException(status_code=404, detail="sandbox run not found")
        return status

    return router

# BEGIN D53B_R3_FASTAPI_WORKSPACE_PATCH_REVIEW_APP_WIRING
# Local-only authenticated patch review route wiring for FastAPI/APIRouter.
# This block exposes review/status rendering through the existing APIRouter only.
# It does not apply patches, create commits, push, restart services, bind sockets, or expose model endpoints.

# Module-level router for the browser-visible /workspace/patch-review/* routes.
# app.py imports this name and mounts it with prefix="/workspace" (the D55D_R2
# mount block). It is intentionally separate from the /api/workspace router that
# setup_workspace_routes() builds and returns: the patch-review decorators below
# bind to this module-level router so the name exists at import time. Without it,
# `from routes.workspace_routes import router` in app.py raises ImportError and
# the app fails to start.
router = APIRouter(tags=["workspace-patch-review"])

import json as _workspace_patch_review_json
import os as _workspace_patch_review_os
import secrets as _workspace_patch_review_secrets
from dataclasses import replace as _workspace_patch_review_replace
from pathlib import Path as _WorkspacePatchReviewPath

from fastapi import Request as _WorkspacePatchReviewRequest
from fastapi.responses import Response as _WorkspacePatchReviewResponse

# Per-process bridge token. When no external review token is configured, the
# patch-review routes are gated by the FastAPI session/admin check
# (_require_patch_review_admin) and we bridge that already-authenticated admin
# to the integration's bearer-token check with this internal value. It is never
# sent to, nor accepted from, a client: a browser navigation carries a session
# cookie (not a bearer header), so without this bridge every logged-in admin
# would get a 401 BLOCKED_AUTH_TOKEN_NOT_CONFIGURED/MISSING.
_WORKSPACE_PATCH_REVIEW_BRIDGE_TOKEN = _workspace_patch_review_secrets.token_urlsafe(32)

from src.workspace_patch_review_app_integration import (
    WorkspaceAppIntegrationConfig as _WorkspaceAppIntegrationConfig,
    handle_workspace_app_request as _handle_workspace_app_request,
    integration_manifest as _workspace_integration_manifest,
)


def _workspace_patch_review_root() -> _WorkspacePatchReviewPath:
    configured = (
        _workspace_patch_review_os.getenv("MYAI_WORKSPACE_ROOT")
        or _workspace_patch_review_os.getenv("ODYSSEUS_ROOT")
    )
    if configured:
        return _WorkspacePatchReviewPath(configured)

    app_root = _WorkspacePatchReviewPath("/app")
    if app_root.exists():
        return app_root

    return _WorkspacePatchReviewPath("/home/youruser/odysseus")


def _workspace_patch_review_allowed_prefixes() -> tuple[str, ...]:
    raw = _workspace_patch_review_os.getenv(
        "MYAI_WORKSPACE_REVIEW_ALLOWED_PREFIXES",
        "src/,tests/,routes/",
    )
    return tuple(part.strip() for part in raw.split(",") if part.strip())


def _workspace_patch_review_config() -> _WorkspaceAppIntegrationConfig:
    root = _workspace_patch_review_root()
    requests_dir = _workspace_patch_review_os.getenv("MYAI_WORKSPACE_REQUESTS_DIR")
    expected_token = (
        _workspace_patch_review_os.getenv("MYAI_WORKSPACE_REVIEW_API_TOKEN")
        or _workspace_patch_review_os.getenv("MYAI_WORKSPACE_PATCH_REVIEW_TOKEN")
    )

    return _WorkspaceAppIntegrationConfig(
        root=root,
        requests_dir=(
            _WorkspacePatchReviewPath(requests_dir)
            if requests_dir
            else root / "data/workspace/requests"
        ),
        expected_token=expected_token,
        allowed_prefixes=_workspace_patch_review_allowed_prefixes(),
        mount_prefix="/workspace",
    )


def _workspace_patch_review_headers(request: _WorkspacePatchReviewRequest) -> dict[str, str]:
    return {str(k): str(v) for k, v in request.headers.items()}


def _workspace_patch_review_query_string(request: _WorkspacePatchReviewRequest) -> str:
    return request.url.query or ""


def _workspace_patch_review_fastapi_response(result: dict) -> _WorkspacePatchReviewResponse:
    body = str(result.get("body", ""))
    status_code = int(result.get("status_code", 200))
    content_type = str(result.get("content_type", "text/plain; charset=utf-8"))

    headers = {}
    for name, value in dict(result.get("headers", {})).items():
        if str(name).lower() not in {"content-type", "content-length"}:
            headers[str(name)] = str(value)

    return _WorkspacePatchReviewResponse(
        content=body,
        status_code=status_code,
        media_type=content_type,
        headers=headers,
    )


def _require_patch_review_admin(request: _WorkspacePatchReviewRequest):
    """Session/admin gate for the browser-visible patch-review routes.

    These run behind the global AuthMiddleware (authenticated) and are mounted at
    /workspace/patch-review. We additionally require admin/single-user here so they
    carry the same authorization as the /api/workspace planner routes, and so a
    non-admin (including a self-registered LAN account) cannot reach patch review.
    """
    owner = effective_user(request)
    if not owner_is_admin_or_single_user(owner):
        raise HTTPException(status_code=403, detail="ProjectForge patch review is admin-only")
    return owner


def _workspace_patch_review_dispatch(request: _WorkspacePatchReviewRequest, route_path: str):
    """Dispatch to the workspace integration as the authenticated admin.

    If an external review token is configured (MYAI_WORKSPACE_REVIEW_API_TOKEN /
    MYAI_WORKSPACE_PATCH_REVIEW_TOKEN), that bearer-token model is preserved.
    Otherwise the FastAPI session/admin gate above is the boundary, and we inject
    the per-process bridge token so the integration's token check passes for this
    already-authorized request instead of failing closed with a 401.
    """
    config = _workspace_patch_review_config()
    headers = _workspace_patch_review_headers(request)
    if not config.expected_token:
        config = _workspace_patch_review_replace(
            config, expected_token=_WORKSPACE_PATCH_REVIEW_BRIDGE_TOKEN
        )
        headers["Authorization"] = f"Bearer {_WORKSPACE_PATCH_REVIEW_BRIDGE_TOKEN}"
    return _handle_workspace_app_request(
        route_path,
        method=request.method,
        headers=headers,
        query_string=_workspace_patch_review_query_string(request),
        config=config,
    )


@router.get("/patch-review/health")
async def workspace_patch_review_health(request: _WorkspacePatchReviewRequest):
    _require_patch_review_admin(request)
    result = _workspace_patch_review_dispatch(request, "/workspace/health")
    return _workspace_patch_review_fastapi_response(result)


@router.get("/patch-review/manifest")
async def workspace_patch_review_manifest(request: _WorkspacePatchReviewRequest):
    _require_patch_review_admin(request)
    payload = _workspace_integration_manifest(_workspace_patch_review_config())
    return _WorkspacePatchReviewResponse(
        content=_workspace_patch_review_json.dumps(payload, indent=2, sort_keys=True),
        status_code=200,
        media_type="application/json; charset=utf-8",
    )


@router.get("/patch-review")
async def workspace_patch_review_page(request: _WorkspacePatchReviewRequest):
    _require_patch_review_admin(request)
    result = _workspace_patch_review_dispatch(request, "/workspace/patch-review")
    return _workspace_patch_review_fastapi_response(result)


@router.get("/patch-review/requests")
async def workspace_patch_review_requests(request: _WorkspacePatchReviewRequest):
    _require_patch_review_admin(request)
    result = _workspace_patch_review_dispatch(request, "/workspace/requests")
    return _workspace_patch_review_fastapi_response(result)
# END D53B_R3_FASTAPI_WORKSPACE_PATCH_REVIEW_APP_WIRING


@router.post("/patch-review/apply")
async def workspace_patch_review_apply(request: _WorkspacePatchReviewRequest):
    """Approve & apply a reviewed patch from the browser — closes the CLI-only
    dead end. Admin-gated; requires the exact approval phrase in the body (the same
    human gate as the CLI, moved into the UI the pipeline already links to).
    apply_reviewed_patch re-reviews, re-checks scope, backs up, applies, and
    post-apply re-checks (auto-reverting on failure). By default it leaves the
    change UNCOMMITTED (original behavior); pass commit=true (opt-in, on top of
    the approval phrase) to branch + commit it, and push/open_pr to publish."""
    _require_patch_review_admin(request)
    try:
        body = await request.json()
    except Exception:
        body = {}
    if not isinstance(body, dict):
        body = {}
    patch_file = str(body.get("patch_file") or "").strip()
    approval_phrase = str(body.get("approval_phrase") or "")
    if not patch_file:
        raise HTTPException(status_code=400, detail="patch_file is required")
    # Confine to a dev-mirror patch path; no absolute paths or '..' escape.
    if patch_file.startswith("/") or ".." in patch_file or "patches/" not in patch_file:
        raise HTTPException(status_code=400, detail="invalid patch_file")

    # Opt-in git workflow. commit defaults OFF (unchanged behavior). When asked to
    # commit, default to a derived `sandbox/<run-id>` branch so an auto-commit
    # never silently lands on the main branch unless the caller names one.
    import os as _os
    import re as _re
    commit = bool(body.get("commit", False))
    push = bool(body.get("push", False))
    open_pr = bool(body.get("open_pr", False))
    commit_message = (str(body.get("commit_message")).strip() or None) if body.get("commit_message") else None
    pr_base = str(body.get("pr_base") or "dev").strip() or "dev"

    def _safe_branch(name: str) -> str:
        name = _re.sub(r"[^A-Za-z0-9._/-]+", "-", name).strip("-/") or "patch"
        return name[:80]

    branch = None
    if commit:
        raw_branch = str(body.get("branch") or "").strip()
        if raw_branch:
            branch = _safe_branch(raw_branch)
        else:
            stem = _os.path.splitext(_os.path.basename(patch_file))[0]
            branch = _safe_branch(f"sandbox/{stem}")

    from src.workspace_patch_approval import apply_reviewed_patch
    return apply_reviewed_patch(
        patch_file,
        approval_phrase=approval_phrase,
        allowed_prefixes=list(_workspace_patch_review_allowed_prefixes()),
        commit=commit,
        branch=branch,
        commit_message=commit_message,
        push=push,
        open_pr=open_pr,
        pr_base=pr_base,
    )

