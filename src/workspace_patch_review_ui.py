from __future__ import annotations

import html
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from src.workspace_patch_review_api import (
    list_workspace_requests_api,
    review_patch_api,
)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _safety() -> dict[str, bool]:
    return {
        "patch_applied": False,
        "commit_performed": False,
        "push_performed": False,
        "service_restart_performed": False,
        "server_started": False,
        "lan_exposure_allowed": False,
        "model_endpoint_exposure_allowed": False,
        "remote_command_execution_allowed": False,
        "whatsapp_outbound_allowed": False,
    }


def _esc(value: Any) -> str:
    return html.escape("" if value is None else str(value), quote=True)


def _badge(status: str | None) -> str:
    value = status or "UNKNOWN"
    if value.startswith("PASS_"):
        tone = "pass"
    elif value.startswith("BLOCKED_"):
        tone = "blocked"
    elif value.startswith("REVIEW_"):
        tone = "review"
    else:
        tone = "neutral"
    return f"<span class=\"badge {tone}\">{_esc(value)}</span>"


def build_patch_review_ui_model(
    *,
    patch_file: str | Path,
    token: str | None,
    expected_token: str | None,
    root: str | Path = ".",
    allowed_prefixes: list[str] | None = None,
    requests_dir: str | Path | None = None,
) -> dict[str, Any]:
    review_result = review_patch_api(
        patch_file,
        token=token,
        expected_token=expected_token,
        root=root,
        allowed_prefixes=allowed_prefixes,
        include_preview=True,
    )

    if requests_dir is not None:
        requests_result = list_workspace_requests_api(
            requests_dir,
            token=token,
            expected_token=expected_token,
            include_payload=False,
            limit=50,
        )
    else:
        requests_result = {
            "status": "PASS_WORKSPACE_REQUESTS_NOT_REQUESTED",
            "authenticated": review_result.get("authenticated", False),
            "requests": [],
            "request_count": 0,
            "safety": _safety(),
            "updated_at": _now(),
        }

    return {
        "status": "PASS_PATCH_REVIEW_UI_MODEL_BUILT",
        "patch_file": str(patch_file),
        "root": str(root),
        "allowed_prefixes": allowed_prefixes or [],
        "review": review_result,
        "requests": requests_result,
        "safety": _safety(),
        "updated_at": _now(),
    }


def render_patch_review_ui(model: dict[str, Any]) -> str:
    review = model.get("review", {})
    requests = model.get("requests", {})
    safety = model.get("safety", {})
    preview = review.get("patch_preview_first_80_lines") or ""
    patch_file_js = json.dumps(str(model.get("patch_file") or ""))
    allowed = model.get("allowed_prefixes") or []
    request_items = requests.get("requests") or []

    allowed_html = "".join(f"<li>{_esc(path)}</li>" for path in allowed)
    if not allowed_html:
        allowed_html = "<li>None configured</li>"

    request_rows = []
    for item in request_items:
        request_rows.append(
            "<tr>"
            f"<td>{_esc(item.get('name'))}</td>"
            f"<td>{_esc(item.get('file'))}</td>"
            "</tr>"
        )
    if not request_rows:
        request_rows.append("<tr><td colspan=\"2\">No workspace requests found.</td></tr>")

    parts = [
        "<!doctype html>",
        "<html lang=\"en\">",
        "<head>",
        "<meta charset=\"utf-8\">",
        "<title>my.ai Workspace Patch Review</title>",
        "<style>",
        "body { font-family: system-ui, -apple-system, BlinkMacSystemFont, \"Segoe UI\", sans-serif; margin: 2rem; color: #222; }",
        "main { max-width: 1080px; margin: 0 auto; }",
        "section { border: 1px solid #ddd; border-radius: 12px; padding: 1rem; margin: 1rem 0; background: #fafafa; }",
        "pre { white-space: pre-wrap; overflow-wrap: anywhere; background: #f3f3f3; padding: 1rem; border-radius: 8px; }",
        "table { width: 100%; border-collapse: collapse; }",
        "td, th { border-bottom: 1px solid #ddd; text-align: left; padding: .5rem; }",
        ".badge { display: inline-block; border-radius: 999px; padding: .2rem .6rem; font-size: .85rem; border: 1px solid #ccc; }",
        ".pass { background: #e9f7ec; }",
        ".blocked { background: #fff1f1; }",
        ".review { background: #fff8e1; }",
        ".neutral { background: #f2f2f2; }",
        ".safety-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: .5rem; }",
        ".muted { color: #666; }",
        "</style>",
        "</head>",
        "<body>",
        "<main>",
        "<h1>my.ai Workspace Patch Review</h1>",
        "<p class=\"muted\">Local authenticated review shell. Applying is the ONLY mutating action and is gated behind the exact approval phrase; it never commits, pushes, restarts services, or exposes endpoints.</p>",
        "<section>",
        "<h2>Review Status</h2>",
        f"<p>UI model: {_badge(model.get('status'))}</p>",
        f"<p>API status: {_badge(review.get('status'))}</p>",
        f"<p>Patch review: {_badge(review.get('review_status'))}</p>",
        f"<p>Authenticated: <strong>{_esc(review.get('authenticated'))}</strong></p>",
        f"<p>Patch file: <code>{_esc(model.get('patch_file'))}</code></p>",
        f"<p>Root: <code>{_esc(model.get('root'))}</code></p>",
        "</section>",
        "<section>",
        "<h2>Allowed Prefixes</h2>",
        f"<ul>{allowed_html}</ul>",
        "</section>",
        "<section>",
        "<h2>Safety</h2>",
        "<div class=\"safety-grid\">",
        f"<div>Patch applied: <strong>{_esc(safety.get('patch_applied'))}</strong></div>",
        f"<div>Commit performed: <strong>{_esc(safety.get('commit_performed'))}</strong></div>",
        f"<div>Push performed: <strong>{_esc(safety.get('push_performed'))}</strong></div>",
        f"<div>Server started: <strong>{_esc(safety.get('server_started'))}</strong></div>",
        f"<div>Service restart: <strong>{_esc(safety.get('service_restart_performed'))}</strong></div>",
        f"<div>LAN exposure: <strong>{_esc(safety.get('lan_exposure_allowed'))}</strong></div>",
        "</div>",
        "</section>",
        "<section>",
        "<h2>Patch Preview</h2>",
        f"<pre>{_esc(preview)}</pre>",
        "</section>",
        "<section>",
        "<h2>Approve &amp; Apply</h2>",
        "<p class=\"muted\">Re-reviews, scope-checks, backs up, applies, and post-apply re-checks the live tree (auto-reverting on failure). Never commits or pushes. Type the exact phrase to confirm.</p>",
        "<p>Phrase: <code>APPROVE_APPLY_REVIEWED_PATCH</code></p>",
        "<input id=\"applyPhrase\" type=\"text\" autocomplete=\"off\" placeholder=\"type the approval phrase\" style=\"width:360px;padding:.4rem;\">",
        "<button id=\"applyBtn\" type=\"button\" onclick=\"applyPatch()\" style=\"padding:.4rem .9rem;margin-left:.5rem;\">Approve &amp; Apply</button>",
        "<pre id=\"applyResult\" class=\"muted\">(not applied)</pre>",
        "</section>",
        "<script>",
        f"const PATCH_FILE = {patch_file_js};",
        "async function applyPatch(){",
        "  const b=document.getElementById('applyBtn'), o=document.getElementById('applyResult');",
        "  const p=document.getElementById('applyPhrase').value;",
        "  b.disabled=true; o.textContent='applying…';",
        "  try{",
        "    const r=await fetch('/workspace/patch-review/apply',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({patch_file:PATCH_FILE,approval_phrase:p})});",
        "    const j=await r.json(); o.textContent=JSON.stringify(j,null,2);",
        "  }catch(e){ o.textContent='error: '+e; } finally{ b.disabled=false; }",
        "}",
        "</script>",
        "<section>",
        "<h2>Workspace Requests</h2>",
        f"<p>Request API status: {_badge(requests.get('status'))}</p>",
        "<table>",
        "<thead><tr><th>Name</th><th>File</th></tr></thead>",
        f"<tbody>{''.join(request_rows)}</tbody>",
        "</table>",
        "</section>",
        "<section>",
        "<h2>Updated</h2>",
        f"<p>{_esc(model.get('updated_at'))}</p>",
        "</section>",
        "</main>",
        "</body>",
        "</html>",
    ]
    return "\n".join(parts)


def render_patch_review_page(
    *,
    patch_file: str | Path,
    token: str | None,
    expected_token: str | None,
    root: str | Path = ".",
    allowed_prefixes: list[str] | None = None,
    requests_dir: str | Path | None = None,
) -> dict[str, Any]:
    model = build_patch_review_ui_model(
        patch_file=patch_file,
        token=token,
        expected_token=expected_token,
        root=root,
        allowed_prefixes=allowed_prefixes,
        requests_dir=requests_dir,
    )
    html_text = render_patch_review_ui(model)
    return {
        "status": "PASS_PATCH_REVIEW_UI_RENDERED",
        "model": model,
        "html": html_text,
        "safety": _safety(),
        "updated_at": _now(),
    }
