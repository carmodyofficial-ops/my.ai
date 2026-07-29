"""GET /api/workspace/files — the @-mention file picker's backend.

Confined to a folder that passes vet_workspace (the same gate that decides what
may be bound for the agent's file tools) and admin-only, matching /browse.
"""
from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException

import routes.workspace_routes as wr


def _endpoint():
    router = wr.setup_workspace_routes()
    return next(r.endpoint for r in router.routes
                if getattr(r, "path", "") == "/api/workspace/files")


@pytest.fixture
def project(tmp_path):
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "widget.py").write_text("x = 1\n")
    (tmp_path / "src" / "widget_helper.py").write_text("y = 2\n")
    (tmp_path / "notes.md").write_text("hi\n")
    # Noise that must never be offered.
    (tmp_path / "src" / "widget.pyc").write_bytes(b"\x00\x01")
    (tmp_path / "node_modules").mkdir()
    (tmp_path / "node_modules" / "widget.js").write_text("nope\n")
    return tmp_path


def _call(project, **kw):
    kw.setdefault("workspace", str(project))
    with patch.object(wr, "effective_user", lambda r: "admin"), \
         patch.object(wr, "owner_is_admin_or_single_user", lambda o: True):
        return _endpoint()(request=MagicMock(), **kw)


def test_finds_files_by_substring(project):
    out = _call(project, q="widget")
    assert "src/widget.py" in out["files"]


def test_basename_matches_rank_above_path_matches(project):
    """Typing a filename should offer that file first, not a deeper path."""
    out = _call(project, q="widget")
    assert out["files"][0] == "src/widget.py"


def test_paths_are_relative_to_the_workspace(project):
    out = _call(project, q="notes")
    assert out["files"] == ["notes.md"]
    assert not any(f.startswith("/") for f in out["files"])


def test_compiled_and_vendored_files_are_not_offered(project):
    out = _call(project, q="widget", limit=50)
    assert not any(f.endswith(".pyc") for f in out["files"])
    assert not any("node_modules" in f for f in out["files"])


def test_empty_query_lists_files(project):
    out = _call(project, q="")
    assert out["files"]
    assert out["workspace"] == str(project)


def test_limit_is_honoured_and_capped(project):
    out = _call(project, q="", limit=1)
    assert len(out["files"]) == 1
    out = _call(project, q="", limit=9999)      # clamped, must not explode
    assert len(out["files"]) <= 100


def test_requires_a_valid_workspace(project):
    with pytest.raises(HTTPException) as exc:
        _call(project, workspace="", q="widget")
    assert exc.value.status_code == 400
    with pytest.raises(HTTPException) as exc:
        _call(project, workspace="/nonexistent-dir-xyz", q="widget")
    assert exc.value.status_code == 400


def test_non_admin_is_refused(project):
    """Same gate as /browse: enumerating a project is an admin capability."""
    with patch.object(wr, "effective_user", lambda r: "bob"), \
         patch.object(wr, "owner_is_admin_or_single_user", lambda o: False):
        with pytest.raises(HTTPException) as exc:
            _endpoint()(request=MagicMock(), workspace=str(project), q="widget")
    assert exc.value.status_code == 403


def test_sensitive_folder_cannot_be_searched(project):
    """vet_workspace rejects it, so the endpoint must too."""
    with pytest.raises(HTTPException) as exc:
        _call(project, workspace="/", q="x")
    assert exc.value.status_code == 400
