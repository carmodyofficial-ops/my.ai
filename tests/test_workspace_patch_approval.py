from pathlib import Path
import subprocess
import tempfile
import unittest

from src.workspace_patch_approval import (
    DEFAULT_APPROVAL_PHRASE,
    apply_reviewed_patch,
)


class WorkspacePatchApprovalTests(unittest.TestCase):
    def _init_repo(self, root: Path):
        subprocess.run(["git", "init"], cwd=str(root), check=True, capture_output=True, text=True)

    def test_blocks_approval_phrase_mismatch(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._init_repo(root)
            patch = root / "change.patch"
            patch.write_text("""--- /dev/null
+++ b/README.md
@@ -0,0 +1 @@
+hello
""", encoding="utf-8")

            result = apply_reviewed_patch(
                patch,
                root=root,
                approval_phrase="WRONG",
                allowed_prefixes=["README.md"],
            )

            self.assertEqual(result["status"], "BLOCKED_APPROVAL_PHRASE_MISMATCH")
            self.assertFalse(result["patch_applied"])
            self.assertFalse((root / "README.md").exists())

    def test_blocks_failed_patch_review(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._init_repo(root)
            patch = root / "change.patch"
            patch.write_text("""--- /dev/null
+++ b/secret.txt
@@ -0,0 +1 @@
+no
""", encoding="utf-8")

            result = apply_reviewed_patch(
                patch,
                root=root,
                approval_phrase=DEFAULT_APPROVAL_PHRASE,
                allowed_prefixes=["src"],
            )

            self.assertEqual(result["status"], "BLOCKED_PATCH_REVIEW_NOT_PASS")
            self.assertFalse(result["patch_applied"])
            self.assertFalse((root / "secret.txt").exists())

    def test_applies_reviewed_patch_with_exact_approval(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._init_repo(root)
            (root / "src").mkdir()
            patch = root / "change.patch"
            patch.write_text("""--- /dev/null
+++ b/src/approved_file.py
@@ -0,0 +1,2 @@
+def ok():
+    return True
""", encoding="utf-8")

            result = apply_reviewed_patch(
                patch,
                root=root,
                approval_phrase=DEFAULT_APPROVAL_PHRASE,
                allowed_prefixes=["src"],
            )

            self.assertEqual(result["status"], "PASS_REVIEWED_PATCH_APPLIED")
            self.assertTrue(result["patch_applied"])
            self.assertTrue((root / "src/approved_file.py").exists())
            self.assertFalse(result["safety"]["commit_performed"])
            self.assertFalse(result["safety"]["push_performed"])
            self.assertFalse(result["safety"]["service_restart_performed"])


if __name__ == "__main__":
    unittest.main()
