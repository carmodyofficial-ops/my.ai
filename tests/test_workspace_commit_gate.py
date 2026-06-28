from __future__ import annotations

import subprocess
import tempfile
import unittest
from pathlib import Path

from src.workspace_commit_gate import (
    DEFAULT_COMMIT_APPROVAL_PHRASE,
    create_reviewed_commit,
)


class WorkspaceCommitGateTests(unittest.TestCase):
    def run_git(self, repo: Path, args: list[str]):
        return subprocess.run(
            ["git", *args],
            cwd=repo,
            text=True,
            capture_output=True,
            check=True,
        )

    def make_repo(self):
        tmp = tempfile.TemporaryDirectory()
        repo = Path(tmp.name)
        self.run_git(repo, ["init", "-q"])
        self.run_git(repo, ["config", "user.email", "myai-test@example.local"])
        self.run_git(repo, ["config", "user.name", "my.ai Test"])
        (repo / "allowed").mkdir()
        (repo / "allowed/file.txt").write_text("original\n")
        self.run_git(repo, ["add", "."])
        self.run_git(repo, ["commit", "-q", "-m", "initial"])
        return tmp, repo

    def commit_count(self, repo: Path) -> int:
        p = subprocess.run(
            ["git", "rev-list", "--count", "HEAD"],
            cwd=repo,
            text=True,
            capture_output=True,
            check=True,
        )
        return int(p.stdout.strip())

    def test_wrong_approval_blocks_commit(self):
        tmp, repo = self.make_repo()
        self.addCleanup(tmp.cleanup)

        (repo / "allowed/file.txt").write_text("updated\n")

        result = create_reviewed_commit(
            ["allowed/file.txt"],
            commit_message="update allowed file",
            approval_phrase="WRONG_APPROVAL",
            required_approval_phrase=DEFAULT_COMMIT_APPROVAL_PHRASE,
            root=repo,
            allowed_prefixes=["allowed/"],
            tests_passed=True,
        )

        self.assertEqual(result["status"], "BLOCKED_COMMIT_APPROVAL_PHRASE_MISMATCH")
        self.assertFalse(result["commit_performed"])
        self.assertEqual(self.commit_count(repo), 1)

    def test_tests_not_passed_blocks_commit(self):
        tmp, repo = self.make_repo()
        self.addCleanup(tmp.cleanup)

        (repo / "allowed/file.txt").write_text("updated\n")

        result = create_reviewed_commit(
            ["allowed/file.txt"],
            commit_message="update allowed file",
            approval_phrase=DEFAULT_COMMIT_APPROVAL_PHRASE,
            required_approval_phrase=DEFAULT_COMMIT_APPROVAL_PHRASE,
            root=repo,
            allowed_prefixes=["allowed/"],
            tests_passed=False,
        )

        self.assertEqual(result["status"], "BLOCKED_TESTS_NOT_PASSED")
        self.assertFalse(result["commit_performed"])
        self.assertEqual(self.commit_count(repo), 1)

    def test_unexpected_dirty_path_blocks_commit(self):
        tmp, repo = self.make_repo()
        self.addCleanup(tmp.cleanup)

        (repo / "allowed/file.txt").write_text("updated\n")
        (repo / "blocked.txt").write_text("do not commit\n")

        result = create_reviewed_commit(
            ["allowed/file.txt"],
            commit_message="update allowed file",
            approval_phrase=DEFAULT_COMMIT_APPROVAL_PHRASE,
            required_approval_phrase=DEFAULT_COMMIT_APPROVAL_PHRASE,
            root=repo,
            allowed_prefixes=["allowed/"],
            tests_passed=True,
        )

        self.assertEqual(result["status"], "BLOCKED_UNEXPECTED_DIRTY_PATHS")
        self.assertFalse(result["commit_performed"])
        self.assertEqual(self.commit_count(repo), 1)

    def test_dry_run_does_not_commit(self):
        tmp, repo = self.make_repo()
        self.addCleanup(tmp.cleanup)

        (repo / "allowed/file.txt").write_text("updated\n")

        result = create_reviewed_commit(
            ["allowed/file.txt"],
            commit_message="update allowed file",
            approval_phrase=DEFAULT_COMMIT_APPROVAL_PHRASE,
            required_approval_phrase=DEFAULT_COMMIT_APPROVAL_PHRASE,
            root=repo,
            allowed_prefixes=["allowed/"],
            tests_passed=True,
            dry_run=True,
        )

        self.assertEqual(result["status"], "PASS_COMMIT_GATE_DRY_RUN")
        self.assertFalse(result["commit_performed"])
        self.assertEqual(self.commit_count(repo), 1)

    def test_exact_approval_creates_local_commit(self):
        tmp, repo = self.make_repo()
        self.addCleanup(tmp.cleanup)

        (repo / "allowed/file.txt").write_text("updated\n")

        result = create_reviewed_commit(
            ["allowed/file.txt"],
            commit_message="update allowed file",
            approval_phrase=DEFAULT_COMMIT_APPROVAL_PHRASE,
            required_approval_phrase=DEFAULT_COMMIT_APPROVAL_PHRASE,
            root=repo,
            allowed_prefixes=["allowed/"],
            tests_passed=True,
        )

        self.assertEqual(result["status"], "PASS_REVIEWED_LOCAL_COMMIT_CREATED")
        self.assertTrue(result["commit_performed"])
        self.assertFalse(result["safety"]["push_performed"])
        self.assertFalse(result["safety"]["service_restart_performed"])
        self.assertEqual(self.commit_count(repo), 2)


if __name__ == "__main__":
    unittest.main()
