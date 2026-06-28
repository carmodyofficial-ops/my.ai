from __future__ import annotations

import subprocess
import tempfile
import unittest
from pathlib import Path

from src.workspace_patch_review_api import (
    authenticate_request,
    list_workspace_requests_api,
    review_patch_api,
)


class WorkspacePatchReviewApiTests(unittest.TestCase):
    def make_repo(self, target_file="sandbox_file.txt"):
        tmp = tempfile.TemporaryDirectory()
        repo = Path(tmp.name)
        subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
        (repo / target_file).parent.mkdir(parents=True, exist_ok=True)
        (repo / target_file).write_text("original\n")

        patch = repo / "valid.patch"
        patch.write_text(
            f"diff --git a/{target_file} b/{target_file}\n"
            f"--- a/{target_file}\n"
            f"+++ b/{target_file}\n"
            "@@ -1 +1 @@\n"
            "-original\n"
            "+updated\n"
        )
        return tmp, repo, patch, target_file

    def test_auth_blocks_missing_token(self):
        auth = authenticate_request(None, expected_token="secret")
        self.assertFalse(auth["authenticated"])
        self.assertEqual(auth["status"], "BLOCKED_AUTH_TOKEN_MISSING")

    def test_auth_blocks_wrong_token(self):
        auth = authenticate_request("wrong", expected_token="secret")
        self.assertFalse(auth["authenticated"])
        self.assertEqual(auth["status"], "BLOCKED_AUTH_TOKEN_MISMATCH")

    def test_review_patch_api_passes_valid_patch_without_applying(self):
        tmp, repo, patch, target = self.make_repo()
        self.addCleanup(tmp.cleanup)

        result = review_patch_api(
            patch,
            token="secret",
            expected_token="secret",
            root=repo,
            allowed_prefixes=[target],
        )

        self.assertTrue(result["authenticated"])
        self.assertEqual(result["status"], "PASS_PATCH_REVIEW_API")
        self.assertEqual(result["review_status"], "PASS_PATCH_REVIEW")
        self.assertFalse(result["safety"]["patch_applied"])
        self.assertEqual((repo / target).read_text(), "original\n")

    def test_review_patch_api_blocks_unauthenticated_review(self):
        tmp, repo, patch, target = self.make_repo()
        self.addCleanup(tmp.cleanup)

        result = review_patch_api(
            patch,
            token="wrong",
            expected_token="secret",
            root=repo,
            allowed_prefixes=[target],
        )

        self.assertFalse(result["authenticated"])
        self.assertEqual(result["status"], "BLOCKED_AUTH_TOKEN_MISMATCH")
        self.assertNotIn("review", result)
        self.assertEqual((repo / target).read_text(), "original\n")

    def test_review_patch_api_reports_invalid_patch_safely(self):
        tmp, repo, patch, target = self.make_repo()
        self.addCleanup(tmp.cleanup)

        bad_patch = repo / "bad.patch"
        bad_patch.write_text("not a valid patch\n")

        result = review_patch_api(
            bad_patch,
            token="secret",
            expected_token="secret",
            root=repo,
            allowed_prefixes=[target],
        )

        self.assertTrue(result["authenticated"])
        self.assertEqual(result["status"], "REVIEW_PATCH_REVIEW_API")
        self.assertNotEqual(result["review_status"], "PASS_PATCH_REVIEW")
        self.assertEqual((repo / target).read_text(), "original\n")

    def test_allowed_prefix_blocks_unexpected_file(self):
        tmp, repo, patch, target = self.make_repo("blocked/file.txt")
        self.addCleanup(tmp.cleanup)

        result = review_patch_api(
            patch,
            token="secret",
            expected_token="secret",
            root=repo,
            allowed_prefixes=["allowed/"],
        )

        self.assertTrue(result["authenticated"])
        self.assertEqual(result["status"], "REVIEW_PATCH_REVIEW_API")
        self.assertNotEqual(result["review_status"], "PASS_PATCH_REVIEW")
        self.assertEqual((repo / target).read_text(), "original\n")

    def test_list_workspace_requests_requires_auth(self):
        with tempfile.TemporaryDirectory() as td:
            result = list_workspace_requests_api(
                td,
                token="wrong",
                expected_token="secret",
            )

        self.assertFalse(result["authenticated"])
        self.assertEqual(result["status"], "BLOCKED_AUTH_TOKEN_MISMATCH")
        self.assertEqual(result["requests"], [])

    def test_list_workspace_requests_authenticated(self):
        with tempfile.TemporaryDirectory() as td:
            requests_dir = Path(td)
            (requests_dir / "request_a.json").write_text('{"id": "a", "status": "queued"}\n')
            result = list_workspace_requests_api(
                requests_dir,
                token="secret",
                expected_token="secret",
                include_payload=True,
            )

        self.assertTrue(result["authenticated"])
        self.assertEqual(result["status"], "PASS_WORKSPACE_REQUESTS_LISTED")
        self.assertEqual(result["request_count"], 1)
        self.assertEqual(result["requests"][0]["payload"]["id"], "a")


if __name__ == "__main__":
    unittest.main()
