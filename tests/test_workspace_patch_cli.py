from __future__ import annotations

import contextlib
import io
import json
import subprocess
import tempfile
import unittest
from pathlib import Path

from src.workspace_patch_approval import DEFAULT_APPROVAL_PHRASE
from src.workspace_patch_cli import main


class WorkspacePatchCliTests(unittest.TestCase):
    def make_repo(self):
        tmp = tempfile.TemporaryDirectory()
        repo = Path(tmp.name)
        subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
        (repo / "sandbox_file.txt").write_text("original\n")
        patch = repo / "valid.patch"
        patch.write_text(
            "diff --git a/sandbox_file.txt b/sandbox_file.txt\n"
            "--- a/sandbox_file.txt\n"
            "+++ b/sandbox_file.txt\n"
            "@@ -1 +1 @@\n"
            "-original\n"
            "+updated\n"
        )
        return tmp, repo, patch

    def invoke(self, args):
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            code = main(args)
        return code, json.loads(buf.getvalue())

    def test_review_cli_passes_valid_patch(self):
        tmp, repo, patch = self.make_repo()
        self.addCleanup(tmp.cleanup)

        code, payload = self.invoke([
            "review",
            str(patch),
            "--root",
            str(repo),
            "--allowed-prefix",
            "sandbox_file.txt",
        ])

        self.assertEqual(code, 0)
        self.assertEqual(payload["status"], "PASS_PATCH_REVIEW")
        self.assertEqual((repo / "sandbox_file.txt").read_text(), "original\n")

    def test_apply_cli_blocks_wrong_approval(self):
        tmp, repo, patch = self.make_repo()
        self.addCleanup(tmp.cleanup)

        code, payload = self.invoke([
            "apply",
            str(patch),
            "--root",
            str(repo),
            "--allowed-prefix",
            "sandbox_file.txt",
            "--approval",
            "WRONG_APPROVAL_PHRASE",
            "--required-approval",
            DEFAULT_APPROVAL_PHRASE,
        ])

        self.assertNotEqual(code, 0)
        self.assertEqual(payload["status"], "BLOCKED_APPROVAL_PHRASE_MISMATCH")
        self.assertEqual((repo / "sandbox_file.txt").read_text(), "original\n")

    def test_apply_cli_applies_valid_patch_with_exact_approval(self):
        tmp, repo, patch = self.make_repo()
        self.addCleanup(tmp.cleanup)

        code, payload = self.invoke([
            "apply",
            str(patch),
            "--root",
            str(repo),
            "--allowed-prefix",
            "sandbox_file.txt",
            "--approval",
            DEFAULT_APPROVAL_PHRASE,
            "--required-approval",
            DEFAULT_APPROVAL_PHRASE,
        ])

        self.assertEqual(code, 0)
        self.assertEqual(payload["status"], "PASS_REVIEWED_PATCH_APPLIED")
        self.assertEqual((repo / "sandbox_file.txt").read_text(), "updated\n")


if __name__ == "__main__":
    unittest.main()
