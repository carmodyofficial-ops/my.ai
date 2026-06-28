from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from http import HTTPStatus
from pathlib import Path
from typing import Any, Callable
from urllib.parse import urlencode

from src.workspace_patch_review_route import (
    WorkspaceRouteConfig,
    route_summary,
    route_workspace_request,
)


@dataclass(frozen=True)
class WorkspaceAppIntegrationConfig:
    root: str | Path = "."
    requests_dir: str | Path | None = None
    expected_token: str | None = None
    allowed_prefixes: tuple[str, ...] = ()
    mount_prefix: str = "/workspace"


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


def _route_config(config: WorkspaceAppIntegrationConfig | None) -> WorkspaceRouteConfig:
    cfg = config or WorkspaceAppIntegrationConfig()
    return WorkspaceRouteConfig(
        root=cfg.root,
        requests_dir=cfg.requests_dir,
        expected_token=cfg.expected_token,
        allowed_prefixes=cfg.allowed_prefixes,
    )


def _query_string(
    *,
    query: dict[str, Any] | str | None = None,
    query_string: str | None = None,
) -> str:
    if query_string:
        return query_string.lstrip("?")
    if isinstance(query, str):
        return query.lstrip("?")
    if isinstance(query, dict):
        return urlencode(query, doseq=True)
    return ""


def _status_line(status_code: int) -> str:
    try:
        phrase = HTTPStatus(status_code).phrase
    except Exception:
        phrase = "OK"
    return f"{status_code} {phrase}"


def _headers_from_wsgi_environ(environ: dict[str, Any]) -> dict[str, str]:
    headers: dict[str, str] = {}
    for key, value in environ.items():
        if value is None:
            continue
        if key.startswith("HTTP_"):
            header = key[5:].replace("_", "-").title()
            headers[header] = str(value)
        elif key == "CONTENT_TYPE":
            headers["Content-Type"] = str(value)
        elif key == "CONTENT_LENGTH":
            headers["Content-Length"] = str(value)
    return headers


def integration_manifest(
    config: WorkspaceAppIntegrationConfig | None = None,
) -> dict[str, Any]:
    cfg = config or WorkspaceAppIntegrationConfig()
    prefix = cfg.mount_prefix.rstrip("/") or "/workspace"

    return {
        "status": "PASS_WORKSPACE_APP_INTEGRATION_MANIFEST",
        "mount_prefix": prefix,
        "routes": [
            {"method": "GET", "path": f"{prefix}/health", "auth_required": False},
            {"method": "GET", "path": f"{prefix}/patch-review?patch=<path>", "auth_required": True},
            {"method": "GET", "path": f"{prefix}/requests", "auth_required": True},
        ],
        "source_route_summary": route_summary(),
        "server_started": False,
        "socket_bound": False,
        "safety": _safety(),
        "updated_at": _now(),
    }


def handle_workspace_app_request(
    path: str,
    *,
    method: str = "GET",
    headers: dict[str, str] | None = None,
    query: dict[str, Any] | str | None = None,
    query_string: str | None = None,
    config: WorkspaceAppIntegrationConfig | None = None,
) -> dict[str, Any]:
    cfg = config or WorkspaceAppIntegrationConfig()
    prefix = cfg.mount_prefix.rstrip("/") or "/workspace"

    normalized_path = path or "/"
    if normalized_path == f"{prefix}/health":
        route_path = "/workspace/health"
    elif normalized_path == f"{prefix}/patch-review":
        route_path = "/workspace/patch-review"
    elif normalized_path == f"{prefix}/requests":
        route_path = "/workspace/requests"
    elif normalized_path in {"/health", "/workspace/health", "/workspace/patch-review", "/workspace/requests"}:
        route_path = normalized_path
    else:
        route_path = normalized_path

    qs = _query_string(query=query, query_string=query_string)
    url = route_path if not qs else f"{route_path}?{qs}"

    response = route_workspace_request(
        url,
        method=method,
        headers=headers,
        config=_route_config(cfg),
    )

    response = dict(response)
    response.setdefault("safety", _safety())
    response["integration"] = {
        "status": "PASS_WORKSPACE_APP_REQUEST_DISPATCHED",
        "mount_prefix": prefix,
        "server_started": False,
        "socket_bound": False,
        "updated_at": _now(),
    }
    return response


def build_workspace_wsgi_app(
    config: WorkspaceAppIntegrationConfig | None = None,
) -> Callable[[dict[str, Any], Callable[[str, list[tuple[str, str]]], None]], list[bytes]]:
    cfg = config or WorkspaceAppIntegrationConfig()

    def app(environ: dict[str, Any], start_response: Callable[[str, list[tuple[str, str]]], None]) -> list[bytes]:
        method = str(environ.get("REQUEST_METHOD", "GET"))
        path = str(environ.get("PATH_INFO", "/"))
        query_string = str(environ.get("QUERY_STRING", ""))
        headers = _headers_from_wsgi_environ(environ)

        response = handle_workspace_app_request(
            path,
            method=method,
            headers=headers,
            query_string=query_string,
            config=cfg,
        )

        body_text = str(response.get("body", ""))
        body = body_text.encode("utf-8")
        status_code = int(response.get("status_code", 200))
        content_type = str(response.get("content_type", "text/plain; charset=utf-8"))

        out_headers = [
            ("Content-Type", content_type),
            ("Content-Length", str(len(body))),
        ]

        for name, value in dict(response.get("headers", {})).items():
            if name.lower() not in {"content-type", "content-length"}:
                out_headers.append((str(name), str(value)))

        start_response(_status_line(status_code), out_headers)
        return [body]

    setattr(app, "workspace_integration_manifest", integration_manifest(cfg))
    setattr(app, "workspace_integration_safety", _safety())
    return app
