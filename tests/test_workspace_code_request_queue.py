from pathlib import Path
import tempfile
import unittest

from src.workspace_code_request_queue import (
    DEFAULT_SAFETY,
    create_code_request,
    list_code_requests,
    read_code_request,
    update_code_request_status,
)


class WorkspaceCodeRequestQueueTests(unittest.TestCase):
    def test_create_code_request_persists_required_fields(self):
        with tempfile.TemporaryDirectory() as tmp:
            queue_dir = Path(tmp)
            request = create_code_request(
                "Build a tiny feature in the mirror only.",
                title="Tiny Feature",
                queue_dir=queue_dir,
                metadata={"source": "unit-test"},
            )

            self.assertTrue(request["request_id"].startswith("wcr_"))
            self.assertEqual(request["title"], "Tiny Feature")
            self.assertEqual(request["prompt"], "Build a tiny feature in the mirror only.")
            self.assertEqual(request["status"], "queued")
            self.assertTrue(request["created_at"])
            self.assertEqual(request["metadata"], {"source": "unit-test"})

            for key, expected in DEFAULT_SAFETY.items():
                self.assertEqual(request["safety"][key], expected)
                self.assertIsInstance(request["safety"][key], bool)

            saved = queue_dir / f"{request['request_id']}.json"
            self.assertTrue(saved.exists())

            read_back = read_code_request(request["request_id"], queue_dir=queue_dir)
            self.assertEqual(read_back, request)

    def test_list_code_requests_filters_by_status(self):
        with tempfile.TemporaryDirectory() as tmp:
            queue_dir = Path(tmp)
            first = create_code_request("First prompt", title="First", queue_dir=queue_dir)
            second = create_code_request("Second prompt", title="Second", queue_dir=queue_dir)

            updated_second = update_code_request_status(second["request_id"], "review", queue_dir=queue_dir)

            queued = list_code_requests(queue_dir=queue_dir, status="queued")
            review = list_code_requests(queue_dir=queue_dir, status="review")

            self.assertEqual({item["request_id"] for item in queued}, {first["request_id"]})
            self.assertEqual({item["request_id"] for item in review}, {updated_second["request_id"]})

    def test_status_update_rejects_invalid_status(self):
        with tempfile.TemporaryDirectory() as tmp:
            queue_dir = Path(tmp)
            request = create_code_request("Prompt", title="Status", queue_dir=queue_dir)

            with self.assertRaises(ValueError):
                update_code_request_status(request["request_id"], "../bad", queue_dir=queue_dir)

    def test_invalid_request_id_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(ValueError):
                read_code_request("../bad", queue_dir=Path(tmp))

    def test_empty_prompt_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(ValueError):
                create_code_request("   ", title="No Prompt", queue_dir=Path(tmp))

    def test_missing_request_raises_file_not_found(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(FileNotFoundError):
                read_code_request("wcr_missing", queue_dir=Path(tmp))


if __name__ == "__main__":
    unittest.main()
