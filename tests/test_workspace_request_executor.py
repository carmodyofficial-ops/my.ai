from pathlib import Path
import tempfile
import textwrap
import unittest

from src.workspace_code_request_queue import create_code_request, read_code_request
from src.workspace_request_executor import execute_request_to_dev_mirror, next_queued_request


def write_tool(path: Path, body: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(textwrap.dedent(body), encoding="utf-8")
    path.chmod(0o755)


class WorkspaceRequestExecutorTests(unittest.TestCase):
    def test_next_queued_request(self):
        with tempfile.TemporaryDirectory() as tmp:
            queue = Path(tmp)
            created = create_code_request("Prompt", title="Title", queue_dir=queue)
            found = next_queued_request(queue)
            self.assertEqual(found["request_id"], created["request_id"])

    def test_execute_request_to_dev_mirror_with_fake_tools(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "repo"
            queue = root / "data/workspace/requests"
            tools = root / "tools"
            request = create_code_request("Prompt", title="Title", queue_dir=queue)

            write_tool(tools / "create_d42_dev_request.py", """
            #!/usr/bin/env python3
            import json
            print(json.dumps({"status":"PASS_D42_DEV_REQUEST_CREATED","request_id":"d42_req_fake"}))
            """)
            write_tool(tools / "create_d42_dev_mirror.py", """
            #!/usr/bin/env python3
            import json
            print(json.dumps({"status":"PASS_D42_DEV_MIRROR_CREATED","run_id":"d42_run_fake","mirror_path":"/tmp/fake"}))
            """)
            write_tool(tools / "run_d42_dev_mirror_checks.py", """
            #!/usr/bin/env python3
            import json
            print(json.dumps({"status":"PASS_D42_DEV_MIRROR_CHECKS"}))
            """)
            write_tool(tools / "package_d42_dev_change.py", """
            #!/usr/bin/env python3
            import json
            print(json.dumps({"status":"PASS_D42_DEV_CHANGE_PACKAGED_NOOP","patch_file":"fake.patch"}))
            """)

            result = execute_request_to_dev_mirror(request["request_id"], queue_dir=queue, root=root, d42_tools=tools)

            self.assertEqual(result["status"], "PASS_WORKSPACE_REQUEST_EXECUTED_TO_DEV_MIRROR")
            self.assertEqual(result["d42_request_id"], "d42_req_fake")
            self.assertEqual(result["d42_run_id"], "d42_run_fake")
            self.assertEqual(result["checks_status"], "PASS_D42_DEV_MIRROR_CHECKS")
            self.assertEqual(result["package_status"], "PASS_D42_DEV_CHANGE_PACKAGED_NOOP")
            self.assertFalse(result["safety"]["patch_apply_allowed"])
            self.assertEqual(read_code_request(request["request_id"], queue_dir=queue)["status"], "dev_mirror_packaged")


if __name__ == "__main__":
    unittest.main()
