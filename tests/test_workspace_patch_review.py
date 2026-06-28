from pathlib import Path
import subprocess
import tempfile
import unittest

from src.workspace_patch_review import (
    parse_changed_files_from_patch_text,
    review_patch,
    write_patch_review_report,
)


class WorkspacePatchReviewTests(unittest.TestCase):
    def test_parse_changed_files(self):
        text = """--- a/src/a.py
+++ b/src/a.py
@@ -0,0 +1 @@
+print('a')
--- a/tests/test_a.py
+++ b/tests/test_a.py
@@ -0,0 +1 @@
+def test_a(): pass
"""
        self.assertEqual(
            parse_changed_files_from_patch_text(text),
            ["src/a.py", "tests/test_a.py"],
        )

    def test_review_missing_patch(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = review_patch("missing.patch", root=Path(tmp))
            self.assertEqual(result["status"], "FAIL_PATCH_MISSING")
            self.assertFalse(result["safety"]["patch_applied"])

    def test_review_patch_apply_check_ok(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            subprocess.run(["git", "init"], cwd=str(root), check=True, capture_output=True, text=True)
            (root / "src").mkdir()
            patch = root / "change.patch"
            patch.write_text("""--- /dev/null
+++ b/src/new_file.py
@@ -0,0 +1,2 @@
+def hello():
+    return 'world'
""", encoding="utf-8")

            result = review_patch(patch, root=root, allowed_prefixes=["src"])
            self.assertEqual(result["status"], "PASS_PATCH_REVIEW")
            self.assertEqual(result["changed_files"], ["src/new_file.py"])
            self.assertTrue(result["git_apply_check_ok"])
            self.assertFalse(result["safety"]["patch_applied"])

    def test_write_patch_review_report(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            subprocess.run(["git", "init"], cwd=str(root), check=True, capture_output=True, text=True)
            patch = root / "change.patch"
            out = root / "report.json"
            patch.write_text("""--- /dev/null
+++ b/README.md
@@ -0,0 +1 @@
+hello
""", encoding="utf-8")

            report = write_patch_review_report(patch, out, root=root)
            self.assertTrue(out.exists())
            self.assertEqual(report["changed_files"], ["README.md"])


if __name__ == "__main__":
    unittest.main()
