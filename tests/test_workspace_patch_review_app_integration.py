from __future__ import annotations

import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from urllib.parse import quote

from src.workspace_patch_review_app_integration import (
    WorkspaceAppIntegrationConfig,
    build_workspace_wsgi_app,
    handle_workspace_app_request,
    integration_manifest,
)


class WorkspacePatchReviewAppIntegrationTests(unittest.TestCase):
    def make_repo(self, target_file="sandbox_file.txt", valid=True):
        tmp = tempfile.TemporaryDirectory()
        repo = Path(tmp.name)
        subprocess.run(["git", "init", "-q"], cwd=repo, check=True)

        (repo / target_file).parent.mkdir(parents=True, exist_ok=True)
        (repo / target_file).write_text("original\n")

        patch = repo / "review.patch"
        if valid:
            patch.write_text(
                f"diff --git a/{target_file} b/{target_file}\n"
                f"--- a/{target_file}\n"
                f"+++ b/{target_file}\n"
                "@@ -1 +1 @@\n"
                "-original\n"
                "+updated\n"
            )
        else:
            patch.write_text("not a valid patch\n")

        return tmp, repo, patch, target_file

    def test_manifest_declares_routes_without_server_start(self):
        manifest = integration_manifest()
        self.assertEqual(manifest["status"], "PASS_WORKSPACE_APP_INTEGRATION_MANIFEST")
        self.assertFalse(manifest["server_started"])
        self.assertFalse(manifest["socket_bound"])
        self.assertFalse(manifest["safety"]["server_started"])
        self.assertIn("/workspace/patch-review?patch=<path>", [r["path"] for r in manifest["routes"]])

    def test_handle_health_request_no_auth_no_socket(self):
        response = handle_workspace_app_request("/workspace/health")
        payload = json.loads(response["body"])

        self.assertEqual(response["status_code"], 200)
        self.assertEqual(payload["status"], "PASS_WORKSPACE_ROUTE_HEALTH")
        self.assertFalse(response["safety"]["server_started"])
        self.assertFalse(response["safety"]["socket_bound"])
        self.assertEqual(response["integration"]["status"], "PASS_WORKSPACE_APP_REQUEST_DISPATCHED")

    def test_handle_patch_review_request_no_apply(self):
        tmp, repo, patch, target = self.make_repo()
        self.addCleanup(tmp.cleanup)

        cfg = WorkspaceAppIntegrationConfig(
            root=repo,
            expected_token="secret",
            allowed_prefixes=(target,),
        )

        response = handle_workspace_app_request(
            "/workspace/patch-review",
            headers={"Authorization": "Bearer secret"},
            query={"patch": str(patch)},
            config=cfg,
        )

        self.assertEqual(response["status_code"], 200)
        self.assertIn("text/html", response["content_type"])
        self.assertIn("PASS_PATCH_REVIEW_API", response["body"])
        self.assertIn("PASS_PATCH_REVIEW", response["body"])
        self.assertFalse(response["safety"]["patch_applied"])
        self.assertFalse(response["safety"]["server_started"])
        self.assertEqual((repo / target).read_text(), "original\n")

    def test_handle_unauthenticated_patch_review_blocks(self):
        tmp, repo, patch, target = self.make_repo()
        self.addCleanup(tmp.cleanup)

        cfg = WorkspaceAppIntegrationConfig(
            root=repo,
            expected_token="secret",
            allowed_prefixes=(target,),
        )

        response = handle_workspace_app_request(
            "/workspace/patch-review",
            headers={"Authorization": "Bearer wrong"},
            query={"patch": str(patch)},
            config=cfg,
        )
        payload = json.loads(response["body"])

        self.assertEqual(response["status_code"], 401)
        self.assertEqual(payload["status"], "BLOCKED_AUTH_TOKEN_MISMATCH")
        self.assertEqual((repo / target).read_text(), "original\n")

    def test_wsgi_app_health_response(self):
        app = build_workspace_wsgi_app()
        captured = {}

        def start_response(status, headers):
            captured["status"] = status
            captured["headers"] = headers

        body = b"".join(app({
            "REQUEST_METHOD": "GET",
            "PATH_INFO": "/workspace/health",
            "QUERY_STRING": "",
        }, start_response)).decode("utf-8")

        payload = json.loads(body)
        self.assertTrue(captured["status"].startswith("200 "))
        self.assertEqual(payload["status"], "PASS_WORKSPACE_ROUTE_HEALTH")
        self.assertFalse(app.workspace_integration_safety["server_started"])
        self.assertFalse(app.workspace_integration_safety["socket_bound"])

    def test_wsgi_app_patch_review_response_no_apply(self):
        tmp, repo, patch, target = self.make_repo()
        self.addCleanup(tmp.cleanup)

        cfg = WorkspaceAppIntegrationConfig(
            root=repo,
            expected_token="secret",
            allowed_prefixes=(target,),
        )
        app = build_workspace_wsgi_app(cfg)
        captured = {}

        def start_response(status, headers):
            captured["status"] = status
            captured["headers"] = headers

        body = b"".join(app({
            "REQUEST_METHOD": "GET",
            "PATH_INFO": "/workspace/patch-review",
            "QUERY_STRING": "patch=" + quote(str(patch), safe=""),
            "HTTP_AUTHORIZATION": "Bearer secret",
        }, start_response)).decode("utf-8")

        self.assertTrue(captured["status"].startswith("200 "))
        self.assertIn("PASS_PATCH_REVIEW_API", body)
        self.assertIn("PASS_PATCH_REVIEW", body)
        self.assertEqual((repo / target).read_text(), "original\n")

    def test_wsgi_app_requests_route_json(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            requests_dir = root / "requests"
            requests_dir.mkdir()
            (requests_dir / "request_a.json").write_text('{"id": "a"}\n')

            cfg = WorkspaceAppIntegrationConfig(
                root=root,
                requests_dir=requests_dir,
                expected_token="secret",
            )
            app = build_workspace_wsgi_app(cfg)
            captured = {}

            def start_response(status, headers):
                captured["status"] = status
                captured["headers"] = headers

            body = b"".join(app({
                "REQUEST_METHOD": "GET",
                "PATH_INFO": "/workspace/requests",
                "QUERY_STRING": "",
                "HTTP_X_MYAI_TOKEN": "secret",
            }, start_response)).decode("utf-8")

        payload = json.loads(body)
        self.assertTrue(captured["status"].startswith("200 "))
        self.assertEqual(payload["status"], "PASS_WORKSPACE_REQUESTS_LISTED")
        self.assertEqual(payload["request_count"], 1)

    def test_wsgi_post_method_blocked(self):
        app = build_workspace_wsgi_app(WorkspaceAppIntegrationConfig(expected_token="secret"))
        captured = {}

        def start_response(status, headers):
            captured["status"] = status
            captured["headers"] = headers

        body = b"".join(app({
            "REQUEST_METHOD": "POST",
            "PATH_INFO": "/workspace/patch-review",
            "QUERY_STRING": "",
            "HTTP_AUTHORIZATION": "Bearer secret",
        }, start_response)).decode("utf-8")

        payload = json.loads(body)
        self.assertTrue(captured["status"].startswith("405 "))
        self.assertEqual(payload["status"], "BLOCKED_METHOD_NOT_ALLOWED")


if __name__ == "__main__":
    unittest.main()
