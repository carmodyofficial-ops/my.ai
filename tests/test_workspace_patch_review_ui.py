from __future__ import annotations

import subprocess
import tempfile
import unittest
from pathlib import Path

from src.workspace_patch_review_ui import (
    render_patch_review_page,
    render_patch_review_ui,
)


class WorkspacePatchReviewUiTests(unittest.TestCase):
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
            patch.write_text("not a patch\n")

        return tmp, repo, patch, target_file

    def test_authenticated_valid_patch_renders_pass_without_applying(self):
        tmp, repo, patch, target = self.make_repo()
        self.addCleanup(tmp.cleanup)

        result = render_patch_review_page(
            patch_file=patch,
            token="secret",
            expected_token="secret",
            root=repo,
            allowed_prefixes=[target],
        )

        self.assertEqual(result["status"], "PASS_PATCH_REVIEW_UI_RENDERED")
        self.assertIn("PASS_PATCH_REVIEW_API", result["html"])
        self.assertIn("PASS_PATCH_REVIEW", result["html"])
        self.assertFalse(result["safety"]["patch_applied"])
        self.assertEqual((repo / target).read_text(), "original\n")

    def test_unauthenticated_page_blocks_review(self):
        tmp, repo, patch, target = self.make_repo()
        self.addCleanup(tmp.cleanup)

        result = render_patch_review_page(
            patch_file=patch,
            token="wrong",
            expected_token="secret",
            root=repo,
            allowed_prefixes=[target],
        )

        model = result["model"]
        self.assertEqual(model["review"]["status"], "BLOCKED_AUTH_TOKEN_MISMATCH")
        self.assertIn("BLOCKED_AUTH_TOKEN_MISMATCH", result["html"])
        self.assertEqual((repo / target).read_text(), "original\n")

    def test_invalid_patch_renders_review_status_safely(self):
        tmp, repo, patch, target = self.make_repo(valid=False)
        self.addCleanup(tmp.cleanup)

        result = render_patch_review_page(
            patch_file=patch,
            token="secret",
            expected_token="secret",
            root=repo,
            allowed_prefixes=[target],
        )

        self.assertIn("REVIEW_PATCH_REVIEW_API", result["html"])
        self.assertFalse(result["safety"]["patch_applied"])
        self.assertEqual((repo / target).read_text(), "original\n")

    def test_html_escaping_for_patch_preview(self):
        tmp, repo, patch, target = self.make_repo()
        self.addCleanup(tmp.cleanup)

        patch.write_text(
            f"diff --git a/{target} b/{target}\n"
            f"--- a/{target}\n"
            f"+++ b/{target}\n"
            "@@ -1 +1 @@\n"
            "-original\n"
            "+<script>alert(1)</script>\n"
        )

        result = render_patch_review_page(
            patch_file=patch,
            token="secret",
            expected_token="secret",
            root=repo,
            allowed_prefixes=[target],
        )

        self.assertNotIn("<script>alert(1)</script>", result["html"])
        self.assertIn("&lt;script&gt;alert(1)&lt;/script&gt;", result["html"])
        self.assertEqual((repo / target).read_text(), "original\n")

    def test_workspace_requests_render_authenticated(self):
        tmp, repo, patch, target = self.make_repo()
        self.addCleanup(tmp.cleanup)

        requests_dir = repo / "requests"
        requests_dir.mkdir()
        (requests_dir / "request_a.json").write_text('{"id": "a"}\n')

        result = render_patch_review_page(
            patch_file=patch,
            token="secret",
            expected_token="secret",
            root=repo,
            allowed_prefixes=[target],
            requests_dir=requests_dir,
        )

        self.assertIn("PASS_WORKSPACE_REQUESTS_LISTED", result["html"])
        self.assertIn("request_a.json", result["html"])

    def test_render_patch_review_ui_accepts_minimal_model(self):
        html = render_patch_review_ui({
            "status": "PASS_PATCH_REVIEW_UI_MODEL_BUILT",
            "patch_file": "x.patch",
            "root": ".",
            "allowed_prefixes": [],
            "review": {"status": "BLOCKED_AUTH_TOKEN_MISSING", "authenticated": False},
            "requests": {"status": "PASS_WORKSPACE_REQUESTS_NOT_REQUESTED", "requests": []},
            "safety": {
                "patch_applied": False,
                "commit_performed": False,
                "push_performed": False,
                "server_started": False,
                "service_restart_performed": False,
                "lan_exposure_allowed": False,
            },
            "updated_at": "now",
        })

        self.assertIn("my.ai Workspace Patch Review", html)
        self.assertIn("BLOCKED_AUTH_TOKEN_MISSING", html)


if __name__ == "__main__":
    unittest.main()
