"""Symbol navigation (src/agent_tools/symbol_tools.py).

The agent previously had no way to ask "where is X defined?" — it had to guess a
regex ("def foo", "foo =", "class foo") and sift the false positives. Python is
resolved with a real AST so definitions are exact; other languages use patterns
and are flagged as such.
"""
import json

import pytest

from src.agent_tools.symbol_tools import FindSymbolTool
from src.tool_execution import _active_workspace


@pytest.fixture
def project(tmp_path):
    (tmp_path / "pkg").mkdir()
    (tmp_path / "pkg" / "core.py").write_text(
        "CONST = 1\n\n\n"
        "class Widget:\n"
        "    def render(self):\n"
        "        return CONST\n\n\n"
        "def build_widget():\n"
        "    return Widget()\n"
    )
    (tmp_path / "pkg" / "use.py").write_text(
        "from .core import build_widget\n\n"
        "def main():\n"
        "    return build_widget()\n"
    )
    (tmp_path / "app.js").write_text(
        "export function buildWidget() { return 1; }\n"
        "const other = buildWidget();\n"
    )
    # A stale copy that must NOT pollute results.
    mirror = tmp_path / "mirrors" / "old"
    mirror.mkdir(parents=True)
    (mirror / "core.py").write_text("def build_widget():\n    return None\n")

    tok = _active_workspace.set(str(tmp_path))
    yield tmp_path
    _active_workspace.reset(tok)


async def _find(**kw):
    return await FindSymbolTool().execute(json.dumps(kw), {})


async def _find_in(project, **kw):
    """Search the fixture project by EXPLICIT path.

    The fixture also binds the workspace contextvar, but a contextvar set in a
    sync fixture is not reliably visible inside the async test body, so relying
    on it made these tests pass alone and fail in a full-suite run (the search
    root fell back to the data dir). Passing `path` removes the ambiguity.
    """
    kw.setdefault("path", str(project))
    return await FindSymbolTool().execute(json.dumps(kw), {})


@pytest.mark.asyncio
async def test_finds_function_definition_via_ast(project):
    r = await _find_in(project, symbol="build_widget")
    assert r["exit_code"] == 0
    assert "core.py:9" in r["output"]      # def build_widget() is on line 9
    assert "[def]" in r["output"]


@pytest.mark.asyncio
async def test_finds_class_definition(project):
    r = await _find_in(project, symbol="Widget")
    assert "[class]" in r["output"]
    assert "core.py:4" in r["output"]


@pytest.mark.asyncio
async def test_finds_module_level_assignment(project):
    r = await _find_in(project, symbol="CONST")
    assert "[assign]" in r["output"]


@pytest.mark.asyncio
async def test_references_mode_excludes_the_definition_line(project):
    r = await _find_in(project, symbol="build_widget", mode="references")
    out = r["output"]
    assert "REFERENCES" in out
    assert "use.py" in out          # the import and the call site
    # The AST definition line itself is not repeated as a reference.
    assert "core.py:9" not in out.split("REFERENCES")[-1]


@pytest.mark.asyncio
async def test_non_python_definitions_are_flagged_as_heuristic(project):
    r = await _find_in(project, symbol="buildWidget", glob="*.js")
    assert "buildWidget" in r["output"]
    # '?' marks a pattern match rather than a parsed one.
    assert "?" in r["output"]


@pytest.mark.asyncio
async def test_copy_directories_do_not_pollute_results(project):
    """A stale copy under mirrors/ must not be reported as a definition.

    Otherwise the model cites a path nobody edits — the failure this guards was
    real: searching this repo returned dev-mirror snapshots ahead of the source.
    """
    r = await _find_in(project, symbol="build_widget")
    assert "mirrors" not in r["output"]
    assert r["output"].count("[def]") == 1


@pytest.mark.asyncio
async def test_rejects_non_identifier_input(project):
    r = await _find_in(project, symbol="foo.*bar")
    assert "bare identifier" in r.get("error", "")


@pytest.mark.asyncio
async def test_missing_symbol_says_so_rather_than_failing(project):
    r = await _find_in(project, symbol="no_such_symbol_here")
    assert r["exit_code"] == 0
    assert "No definition" in r["output"]
