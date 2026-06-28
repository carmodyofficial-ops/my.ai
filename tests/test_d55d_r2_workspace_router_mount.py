from pathlib import Path
import ast
import unittest

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "app.py"
ROUTES = ROOT / "routes/workspace_routes.py"

class D55DR2WorkspaceRouterMountTests(unittest.TestCase):
    def test_app_imports_and_mounts_workspace_router_before_main(self):
        text = APP.read_text(errors="replace")
        self.assertIn("# BEGIN D55D_R2_WORKSPACE_PATCH_REVIEW_ROUTER_MOUNT", text)
        self.assertIn("from routes.workspace_routes import router as workspace_patch_review_router", text)
        self.assertIn('app.include_router(workspace_patch_review_router, prefix="/workspace", tags=["workspace"])', text)
        self.assertIn("# END D55D_R2_WORKSPACE_PATCH_REVIEW_ROUTER_MOUNT", text)

        block_pos = text.index("# BEGIN D55D_R2_WORKSPACE_PATCH_REVIEW_ROUTER_MOUNT")
        main_pos = text.find('if __name__ == "__main__":')
        if main_pos != -1:
            self.assertLess(block_pos, main_pos)

    def test_app_and_routes_parse(self):
        ast.parse(APP.read_text(errors="replace"))
        ast.parse(ROUTES.read_text(errors="replace"))

    def test_patch_review_routes_still_exist(self):
        tree = ast.parse(ROUTES.read_text(errors="replace"))
        found = set()
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                for dec in node.decorator_list:
                    if isinstance(dec, ast.Call) and dec.args and isinstance(dec.args[0], ast.Constant):
                        found.add((node.name, dec.args[0].value))
        expected = {
            ("workspace_patch_review_health", "/patch-review/health"),
            ("workspace_patch_review_manifest", "/patch-review/manifest"),
            ("workspace_patch_review_page", "/patch-review"),
            ("workspace_patch_review_requests", "/patch-review/requests"),
        }
        self.assertTrue(expected.issubset(found))

if __name__ == "__main__":
    unittest.main()
