from __future__ import annotations

import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from urllib.parse import quote

from src.workspace_patch_review_route import (
    WorkspaceRouteConfig,
    route_summary,
    route_workspace_request,
)


class WorkspacePatchReviewRouteTests(unittest.TestCase):
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

    def auth_headers(self):
        return {"Authorization": "Bearer secret"}

    def test_route_summary_declares_no_server_start(self):
        summary = route_summary()
        self.assertEqual(summary["status"], "PASS_WORKSPACE_ROUTE_SUMMARY")
        self.assertFalse(summary["server_started"])
        self.assertFalse(summary["socket_bound"])
        self.assertFalse(summary["safety"]["server_started"])

    def test_health_route_does_not_require_auth(self):
        response = route_workspace_request("/health")
        payload = json.loads(response["body"])

        self.assertEqual(response["status_code"], 200)
        self.assertEqual(payload["status"], "PASS_WORKSPACE_ROUTE_HEALTH")
        self.assertFalse(payload["server_started"])
        self.assertFalse(response["safety"]["socket_bound"])

    def test_method_not_allowed_blocks_mutation(self):
        response = route_workspace_request("/workspace/patch-review", method="POST")
        payload = json.loads(response["body"])

        self.assertEqual(response["status_code"], 405)
        self.assertEqual(payload["status"], "BLOCKED_METHOD_NOT_ALLOWED")
        self.assertFalse(response["safety"]["patch_applied"])
        self.assertFalse(response["safety"]["commit_performed"])

    def test_unauthenticated_route_blocks_before_review(self):
        tmp, repo, patch, target = self.make_repo()
        self.addCleanup(tmp.cleanup)

        cfg = WorkspaceRouteConfig(
            root=repo,
            expected_token="secret",
            allowed_prefixes=(target,),
        )

        response = route_workspace_request(
            f"/workspace/patch-review?patch={quote(str(patch))}",
            headers={"Authorization": "Bearer wrong"},
            config=cfg,
        )
        payload = json.loads(response["body"])

        self.assertEqual(response["status_code"], 401)
        self.assertEqual(payload["status"], "BLOCKED_AUTH_TOKEN_MISMATCH")
        self.assertEqual((repo / target).read_text(), "original\n")

    def test_patch_parameter_required(self):
        tmp, repo, _, target = self.make_repo()
        self.addCleanup(tmp.cleanup)

        cfg = WorkspaceRouteConfig(
            root=repo,
            expected_token="secret",
            allowed_prefixes=(target,),
        )

        response = route_workspace_request(
            "/workspace/patch-review",
            headers=self.auth_headers(),
            config=cfg,
        )
        payload = json.loads(response["body"])

        self.assertEqual(response["status_code"], 400)
        self.assertEqual(payload["status"], "BLOCKED_PATCH_PARAMETER_MISSING")

    def test_authenticated_patch_review_route_renders_html_no_apply(self):
        tmp, repo, patch, target = self.make_repo()
        self.addCleanup(tmp.cleanup)

        cfg = WorkspaceRouteConfig(
            root=repo,
            expected_token="secret",
            allowed_prefixes=(target,),
        )

        response = route_workspace_request(
            f"/workspace/patch-review?patch={quote(str(patch))}",
            headers=self.auth_headers(),
            config=cfg,
        )

        self.assertEqual(response["status_code"], 200)
        self.assertIn("text/html", response["content_type"])
        self.assertIn("PASS_PATCH_REVIEW_API", response["body"])
        self.assertIn("PASS_PATCH_REVIEW", response["body"])
        self.assertFalse(response["safety"]["patch_applied"])
        self.assertFalse(response["safety"]["server_started"])
        self.assertEqual((repo / target).read_text(), "original\n")

    def test_invalid_patch_route_renders_review_html_safely(self):
        tmp, repo, patch, target = self.make_repo(valid=False)
        self.addCleanup(tmp.cleanup)

        cfg = WorkspaceRouteConfig(
            root=repo,
            expected_token="secret",
            allowed_prefixes=(target,),
        )

        response = route_workspace_request(
            f"/workspace/patch-review?patch={quote(str(patch))}",
            headers=self.auth_headers(),
            config=cfg,
        )

        self.assertEqual(response["status_code"], 200)
        self.assertIn("REVIEW_PATCH_REVIEW_API", response["body"])
        self.assertEqual((repo / target).read_text(), "original\n")

    def test_requests_route_returns_authenticated_json(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            requests_dir = root / "requests"
            requests_dir.mkdir()
            (requests_dir / "request_a.json").write_text('{"id": "a"}\n')

            cfg = WorkspaceRouteConfig(
                root=root,
                requests_dir=requests_dir,
                expected_token="secret",
            )

            response = route_workspace_request(
                "/workspace/requests",
                headers={"X-MYAI-Token": "secret"},
                config=cfg,
            )
            payload = json.loads(response["body"])

        self.assertEqual(response["status_code"], 200)
        self.assertEqual(payload["status"], "PASS_WORKSPACE_REQUESTS_LISTED")
        self.assertEqual(payload["request_count"], 1)
        self.assertFalse(response["safety"]["server_started"])

    def test_unknown_route_404(self):
        response = route_workspace_request(
            "/workspace/missing",
            headers=self.auth_headers(),
            config=WorkspaceRouteConfig(expected_token="secret"),
        )
        payload = json.loads(response["body"])

        self.assertEqual(response["status_code"], 404)
        self.assertEqual(payload["status"], "BLOCKED_ROUTE_NOT_FOUND")


if __name__ == "__main__":
    unittest.main()
