from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

from src.workspace_patch_review_api import (
    authenticate_request,
    list_workspace_requests_api,
)
from src.workspace_patch_review_ui import render_patch_review_page


@dataclass(frozen=True)
class WorkspaceRouteConfig:
    root: str | Path = "."
    requests_dir: str | Path | None = None
    expected_token: str | None = None
    allowed_prefixes: tuple[str, ...] = ()


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _safety() -> dict[str, bool]:
    return {
        "patch_applied": False,
        "commit_performed": False,
        "push_performed": False,
        "service_restart_performed": False,
        "server_started": False,
        "socket_bound": False,
        "lan_exposure_allowed": False,
        "model_endpoint_exposure_allowed": False,
        "remote_command_execution_allowed": False,
        "whatsapp_outbound_allowed": False,
    }


def _json_response(
    payload: dict[str, Any],
    *,
    status_code: int = 200,
) -> dict[str, Any]:
    payload = dict(payload)
    payload.setdefault("safety", _safety())
    payload.setdefault("updated_at", _now())
    return {
        "status_code": status_code,
        "content_type": "application/json; charset=utf-8",
        "body": json.dumps(payload, indent=2, sort_keys=True),
        "headers": {
            "Cache-Control": "no-store",
            "X-Content-Type-Options": "nosniff",
        },
        "safety": _safety(),
    }


def _html_response(
    html: str,
    *,
    status_code: int = 200,
) -> dict[str, Any]:
    return {
        "status_code": status_code,
        "content_type": "text/html; charset=utf-8",
        "body": html,
        "headers": {
            "Cache-Control": "no-store",
            "X-Content-Type-Options": "nosniff",
            "Content-Security-Policy": "default-src 'self'; style-src 'unsafe-inline'; script-src 'none'; object-src 'none'",
        },
        "safety": _safety(),
    }


def _extract_token(headers: dict[str, str] | None) -> str | None:
    headers = headers or {}
    lowered = {str(k).lower(): str(v) for k, v in headers.items()}

    auth = lowered.get("authorization")
    if auth and auth.lower().startswith("bearer "):
        return auth.split(" ", 1)[1].strip()

    return lowered.get("x-myai-token")


def _first(query: dict[str, list[str]], name: str) -> str | None:
    values = query.get(name) or []
    return values[0] if values else None


def route_workspace_request(
    url: str,
    *,
    method: str = "GET",
    headers: dict[str, str] | None = None,
    config: WorkspaceRouteConfig | None = None,
) -> dict[str, Any]:
    cfg = config or WorkspaceRouteConfig()
    parsed = urlparse(url)
    path = parsed.path.rstrip("/") or "/"
    query = parse_qs(parsed.query)
    token = _extract_token(headers)

    if method.upper() != "GET":
        return _json_response(
            {
                "status": "BLOCKED_METHOD_NOT_ALLOWED",
                "method": method,
                "allowed_methods": ["GET"],
            },
            status_code=405,
        )

    if path in {"/health", "/workspace/health"}:
        return _json_response(
            {
                "status": "PASS_WORKSPACE_ROUTE_HEALTH",
                "server_started": False,
                "socket_bound": False,
            },
            status_code=200,
        )

    auth = authenticate_request(token, expected_token=cfg.expected_token)
    if not auth.get("authenticated"):
        return _json_response(
            {
                "status": auth.get("status", "BLOCKED_AUTHENTICATION"),
                "authenticated": False,
                "auth": auth,
            },
            status_code=401,
        )

    if path == "/workspace/patch-review":
        patch = _first(query, "patch")
        if not patch:
            return _json_response(
                {
                    "status": "BLOCKED_PATCH_PARAMETER_MISSING",
                    "authenticated": True,
                },
                status_code=400,
            )

        page = render_patch_review_page(
            patch_file=patch,
            token=token,
            expected_token=cfg.expected_token,
            root=cfg.root,
            allowed_prefixes=list(cfg.allowed_prefixes),
            requests_dir=cfg.requests_dir,
        )
        return _html_response(page["html"], status_code=200)

    if path == "/workspace/requests":
        requests = list_workspace_requests_api(
            cfg.requests_dir or Path(cfg.root) / "data/workspace/requests",
            token=token,
            expected_token=cfg.expected_token,
            include_payload=False,
            limit=50,
        )
        return _json_response(requests, status_code=200)

    return _json_response(
        {
            "status": "BLOCKED_ROUTE_NOT_FOUND",
            "path": path,
            "allowed_routes": [
                "/health",
                "/workspace/health",
                "/workspace/patch-review?patch=<path>",
                "/workspace/requests",
            ],
        },
        status_code=404,
    )


def route_summary() -> dict[str, Any]:
    return {
        "status": "PASS_WORKSPACE_ROUTE_SUMMARY",
        "routes": [
            {"method": "GET", "path": "/health", "auth_required": False},
            {"method": "GET", "path": "/workspace/health", "auth_required": False},
            {"method": "GET", "path": "/workspace/patch-review?patch=<path>", "auth_required": True},
            {"method": "GET", "path": "/workspace/requests", "auth_required": True},
        ],
        "server_started": False,
        "socket_bound": False,
        "safety": _safety(),
        "updated_at": _now(),
    }
