from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ROUTE_FILE = ROOT / "routes/workspace_routes.py"
MARKER_BEGIN = "# BEGIN D53B_R3_FASTAPI_WORKSPACE_PATCH_REVIEW_APP_WIRING"
MARKER_END = "# END D53B_R3_FASTAPI_WORKSPACE_PATCH_REVIEW_APP_WIRING"


def wiring_block() -> str:
    text = ROUTE_FILE.read_text(errors="replace")
    start = text.index(MARKER_BEGIN)
    end = text.index(MARKER_END)
    return text[start:end]


class WorkspacePatchReviewFastAPIAppWiringStaticTests(unittest.TestCase):
    def test_wiring_block_present(self):
        text = ROUTE_FILE.read_text(errors="replace")
        self.assertIn(MARKER_BEGIN, text)
        self.assertIn(MARKER_END, text)

    def test_routes_are_fastapi_get_routes(self):
        block = wiring_block()
        self.assertIn('@router.get("/patch-review/health")', block)
        self.assertIn('@router.get("/patch-review/manifest")', block)
        self.assertIn('@router.get("/patch-review")', block)
        self.assertIn('@router.get("/patch-review/requests")', block)
        self.assertNotIn('@router.route(', block)

    def test_fastapi_response_adapter_is_used(self):
        block = wiring_block()
        self.assertIn("from fastapi import Request", block)
        self.assertIn("from fastapi.responses import Response", block)
        self.assertIn("_handle_workspace_app_request", block)
        self.assertIn("_WorkspaceAppIntegrationConfig", block)

    def test_auth_and_prefix_configuration_present(self):
        block = wiring_block()
        self.assertIn("MYAI_WORKSPACE_REVIEW_API_TOKEN", block)
        self.assertIn("MYAI_WORKSPACE_PATCH_REVIEW_TOKEN", block)
        self.assertIn("MYAI_WORKSPACE_REVIEW_ALLOWED_PREFIXES", block)

    def test_wiring_block_is_non_launching_and_non_mutating(self):
        block = wiring_block()
        forbidden = [
            "app.run(",
            ".bind(",
            "socket.",
            "systemctl",
            "subprocess.",
            "git push",
            "service_restart",
            "docker compose up",
        ]
        for value in forbidden:
            self.assertNotIn(value, block)

    def test_workspace_patch_review_paths_are_namespaced(self):
        block = wiring_block()
        self.assertIn("/workspace/patch-review", block)
        self.assertIn("/workspace/requests", block)


if __name__ == "__main__":
    unittest.main()
