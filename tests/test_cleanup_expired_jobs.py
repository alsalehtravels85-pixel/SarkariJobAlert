import unittest
from datetime import datetime as RealDateTime
from unittest.mock import Mock, patch

from scripts import cleanup_expired_jobs


class FixedDateTime:
    @staticmethod
    def now(tz=None):
        return RealDateTime(2026, 11, 11, 12, 0, tzinfo=tz)


class CleanupExpiredJobsTests(unittest.TestCase):
    def setUp(self):
        self.env = patch.multiple(
            cleanup_expired_jobs,
            DB="https://example.supabase.co",
            KEY="test-service-key",
            HEADERS={"apikey": "test", "Authorization": "Bearer test"},
        )
        self.env.start()
        self.addCleanup(self.env.stop)

    @staticmethod
    def response(rows):
        response = Mock()
        response.json.return_value = rows
        response.content = b"[]" if rows else b""
        response.raise_for_status.return_value = None
        return response

    @patch.object(cleanup_expired_jobs, "datetime", FixedDateTime)
    @patch.object(cleanup_expired_jobs.requests, "Session")
    def test_only_expired_published_vacancies_are_moved_to_draft(self, session_cls):
        session = session_cls.return_value
        session.get.side_effect = [
            self.response([{"id": 1, "title": "Expired vacancy", "last_date": "2026-11-10"}]),
            self.response([]),
        ]
        session.patch.return_value = self.response(
            [{"id": 1, "title": "Expired vacancy", "last_date": "2026-11-10"}]
        )

        self.assertEqual(cleanup_expired_jobs.main(), 0)
        params = session.patch.call_args.kwargs
        self.assertEqual(params["json"], {"status": "draft"})
        self.assertIn("id", params["params"])
        self.assertEqual(session.patch.call_count, 1)
        self.assertEqual(session.delete.call_count, 0)

    @patch.object(cleanup_expired_jobs, "datetime", FixedDateTime)
    @patch.object(cleanup_expired_jobs.requests, "Session")
    def test_empty_result_does_not_update_or_delete(self, session_cls):
        session = session_cls.return_value
        session.get.return_value = self.response([])

        self.assertEqual(cleanup_expired_jobs.main(), 0)
        session.patch.assert_not_called()
        session.delete.assert_not_called()

    @patch.object(cleanup_expired_jobs, "datetime", FixedDateTime)
    @patch.object(cleanup_expired_jobs.requests, "Session")
    def test_failed_update_returns_error(self, session_cls):
        session = session_cls.return_value
        session.get.return_value = self.response(
            [{"id": 2, "title": "Expired", "last_date": "2026-11-10"}]
        )
        failed = Mock()
        failed.raise_for_status.side_effect = RuntimeError("update failed")
        session.patch.return_value = failed

        self.assertEqual(cleanup_expired_jobs.main(), 1)

    @patch.object(cleanup_expired_jobs, "datetime", FixedDateTime)
    @patch.object(cleanup_expired_jobs.requests, "Session")
    def test_unexpected_non_list_response_is_rejected(self, session_cls):
        session = session_cls.return_value
        session.get.return_value = self.response({"unexpected": "object"})

        self.assertEqual(cleanup_expired_jobs.main(), 1)
        session.patch.assert_not_called()


if __name__ == "__main__":
    unittest.main()
