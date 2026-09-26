"""generate_video tool: native schema wiring, bg-job launch, and result lifting."""
import json

import pytest

import src.agent_tools  # noqa: F401  (import first: agent_tools <-> tool_schemas cycle)
from src import tool_execution
from src.tool_schemas import FUNCTION_TOOL_SCHEMAS, function_call_to_tool_block


def _schema_names():
    return {s["function"]["name"] for s in FUNCTION_TOOL_SCHEMAS}


def test_media_tools_have_native_schemas():
    # Without a schema, native-tool models (Qwen via Ollama) never see the tool.
    assert {"generate_image", "generate_video"} <= _schema_names()


def test_generate_image_native_call_uses_line_format():
    block = function_call_to_tool_block("generate_image", json.dumps({"prompt": "a fox\nin snow", "size": "1024x1024"}))
    assert block.tool_type == "generate_image"
    lines = block.content.split("\n")
    assert lines[0] == "a fox in snow"
    assert lines[2] == "1024x1024"
    assert tool_execution._parse_generate_image(block.content) == {"prompt": "a fox in snow", "size": "1024x1024"}


def test_generate_video_native_call_passes_json():
    block = function_call_to_tool_block("generate_video", json.dumps({"prompt": "waves", "quality": "high"}))
    assert block.tool_type == "generate_video"
    assert json.loads(block.content) == {"prompt": "waves", "quality": "high"}


@pytest.fixture
def settings(monkeypatch):
    values = {"video_gen_enabled": True, "video_server_url": "http://vs:8102", "video_quality": "fast"}
    monkeypatch.setattr("src.settings.get_setting", lambda k, d=None: values.get(k, d))
    return values


@pytest.fixture
def launched(monkeypatch, tmp_path):
    calls = []
    monkeypatch.setattr("src.constants.BG_JOBS_DIR", str(tmp_path))

    def fake_launch(command, session_id, cwd=None, max_runtime_s=0, extra=None):
        calls.append({"command": command, "session_id": session_id, "max_runtime_s": max_runtime_s})
        return {"id": "job123"}

    monkeypatch.setattr("src.bg_jobs.launch", fake_launch)
    return calls


def test_disabled_setting_blocks_launch(settings, launched):
    settings["video_gen_enabled"] = False
    r = tool_execution._launch_generate_video('{"prompt": "x"}', session_id="s1", owner="u")
    assert r["exit_code"] == 1 and "disabled" in r["error"]
    assert launched == []


def test_launch_writes_spec_and_starts_bg_job(settings, launched, tmp_path):
    r = tool_execution._launch_generate_video(
        json.dumps({"prompt": "a dog on a beach", "quality": "bogus", "aspect": "portrait", "seconds": 99}),
        session_id="s1", owner="u")
    assert r["exit_code"] == 0 and r["bg_job_id"] == "job123"
    assert launched[0]["session_id"] == "s1"
    assert "video_client.py" in launched[0]["command"]
    spec = json.loads(next(tmp_path.glob("video-*.json")).read_text())
    # Invalid values fall back to safe defaults; length is clamped to 5 s.
    assert spec["quality"] == "fast" and spec["aspect"] == "portrait" and spec["seconds"] == 5.0
    assert spec["server_url"] == "http://vs:8102" and spec["owner"] == "u"


def test_plain_text_content_is_the_prompt(settings, launched, tmp_path):
    r = tool_execution._launch_generate_video("a red car at sunset", session_id="s1", owner=None)
    assert r["exit_code"] == 0
    assert json.loads(next(tmp_path.glob("video-*.json")).read_text())["prompt"] == "a red car at sunset"


@pytest.mark.parametrize("url", ["https://evil.example/x.png", "/api/generated-image/../../etc/passwd",
                                 "/api/generated-image/abc12345.mp4"])
def test_image_url_must_be_a_generated_image(settings, launched, url):
    r = tool_execution._launch_generate_video(json.dumps({"prompt": "p", "image_url": url}), session_id="s1", owner="u")
    assert r["exit_code"] == 1
    assert launched == []


def test_requires_session(settings, launched):
    r = tool_execution._launch_generate_video('{"prompt": "x"}', session_id=None, owner="u")
    assert r["exit_code"] == 1 and launched == []


def test_bg_monitor_lifts_video_link(monkeypatch):
    from src import bg_monitor
    out = ("Submitted video job abc (fast quality).\n"
           "Generated video for: a dog on a beach\n"
           "Direct link: /api/generated-image/0123456789abcdef.mp4\n"
           "model: wan2.2-ti2v-5b-turbo\nsize: 1280x704, 5.0s at 24 fps\n")
    monkeypatch.setattr(bg_monitor.bg_jobs, "result_text", lambda rec: out)
    ev = bg_monitor._video_event({"id": "j"})
    assert ev["image_url"] == "/api/generated-image/0123456789abcdef.mp4"
    assert ev["image_prompt"] == "a dog on a beach"
    assert ev["image_model"] == "wan2.2-ti2v-5b-turbo"


def test_bg_monitor_ignores_other_jobs(monkeypatch):
    from src import bg_monitor
    monkeypatch.setattr(bg_monitor.bg_jobs, "result_text",
                        lambda rec: "pip install ok\n/api/generated-image/0123456789abcdef.mp4")
    assert bg_monitor._video_event({"id": "j"}) is None


# --- image-model chats: video intent routing -------------------------------

@pytest.mark.parametrize("msg,expected", [
    ("make a video of a dog on a beach", True),
    ("Now turn this into a video", True),
    ("animate it", True),
    ("a short clip of waves crashing", True),
    ("a poster for a retro video game", False),
    ("a cat sitting on a windowsill", False),
])
def test_wants_video(msg, expected):
    from routes.chat_routes import _wants_video
    assert _wants_video(msg) is expected


def test_last_session_image_finds_most_recent_still():
    from types import SimpleNamespace
    from routes.chat_routes import _last_session_image
    ev = lambda url, p: SimpleNamespace(metadata={"tool_events": [{"image_url": url, "image_prompt": p}]})
    sess = SimpleNamespace(history=[
        ev("/api/generated-image/aaaaaaaaaaaa.png", "old"),
        ev("/api/generated-image/bbbbbbbbbbbb.png", "lighthouse"),
        ev("/api/generated-image/cccccccccccccccc.mp4", "a video"),  # videos can't seed I2V
        SimpleNamespace(metadata=None),
    ])
    assert _last_session_image(sess) == ("/api/generated-image/bbbbbbbbbbbb.png", "lighthouse")
    assert _last_session_image(SimpleNamespace(history=[])) == ("", "")


def test_direct_reply_flag_reaches_job_record(settings, monkeypatch, tmp_path):
    captured = {}
    monkeypatch.setattr("src.constants.BG_JOBS_DIR", str(tmp_path))
    def fake_launch(command, session_id, cwd=None, max_runtime_s=0, extra=None):
        captured["extra"] = extra
        return {"id": "j1"}
    monkeypatch.setattr("src.bg_jobs.launch", fake_launch)
    tool_execution._launch_generate_video('{"prompt": "x"}', session_id="s1", owner="u", direct_reply=True)
    assert captured["extra"] == {"direct_reply": True}


def test_direct_reply_followup_posts_video_without_agent(monkeypatch):
    import asyncio
    from types import SimpleNamespace
    from src import bg_monitor
    out = ("Generated video for: waves\nDirect link: /api/generated-image/0123456789abcdef.mp4\n"
           "model: wan2.2-ti2v-5b-turbo\nsize: 1280x704, 5.0s at 24 fps\n")
    monkeypatch.setattr(bg_monitor.bg_jobs, "result_text", lambda rec: out)
    posted = []
    sm = SimpleNamespace(get_session=lambda sid: SimpleNamespace(id=sid, model="sdxl-lightning-8step"),
                         add_message=lambda sid, m: posted.append(m), save_sessions=lambda: None)
    monkeypatch.setattr("src.ai_interaction.get_session_manager", lambda: sm)

    async def no_agent(*a, **k):
        raise AssertionError("an image-model chat must not re-invoke the agent")
    monkeypatch.setattr(bg_monitor, "_drain_agent", no_agent)
    assert asyncio.run(bg_monitor._run_followup({"id": "j", "session_id": "s", "direct_reply": True})) is True
    assert posted[0].content == "Your video is ready."
    assert posted[0].metadata["tool_events"][0]["image_url"] == "/api/generated-image/0123456789abcdef.mp4"
