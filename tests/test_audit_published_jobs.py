import tempfile
import unittest
from pathlib import Path

from scripts.audit_published_jobs import assess, write_report


class PublishedJobsAuditTests(unittest.TestCase):
    def test_thin_vacancy_is_flagged_not_deleted(self):
        row = {
            "id": "1", "title": "Recruitment", "department": "Department",
            "category": "Vacancy", "status": "published",
            "description": "Short description", "notification_url": "https://example.gov.in/notice.pdf",
            "apply_url": "https://example.gov.in/apply", "qualification": "Graduate",
            "last_date": "2099-01-01",
        }
        flags, action = assess(row)
        self.assertIn("thin_description_under_350_chars", flags)
        self.assertEqual(action, "REVIEW_BEFORE_PUBLISH")

    def test_complete_record_passes_basic_checks(self):
        row = {
            "id": "2", "title": "Recruitment", "department": "Department",
            "category": "Vacancy", "description": "Useful details " * 40,
            "notification_url": "https://example.gov.in/notice.pdf",
            "apply_url": "https://example.gov.in/apply",
            "qualification": "Graduate", "last_date": "2099-01-01",
        }
        flags, action = assess(row)
        self.assertEqual(flags, [])
        self.assertEqual(action, "PASSES_BASIC_CHECKS")

    def test_result_category_accepts_official_notification_page(self):
        row = {
            "id": "4", "title": "Board Result", "department": "Board",
            "category": "Result", "description": "Useful details " * 30,
            "notification_url": "https://example.gov.in/results",
        }
        flags, action = assess(row)
        self.assertNotIn("missing_result_link", flags)
        self.assertEqual(action, "PASSES_BASIC_CHECKS")

    def test_report_is_csv_and_read_only(self):
        row = {"id": "3", "title": "Old", "category": "Vacancy", "description": "x", "last_date": "2020-01-01"}
        with tempfile.TemporaryDirectory() as tmp:
            path = write_report([row], Path(tmp))
            content = path.read_text(encoding="utf-8-sig")
            self.assertIn("expired_vacancy", content)
            self.assertIn("REVIEW_BEFORE_PUBLISH", content)
            self.assertTrue(path.exists())
            self.assertTrue((Path(tmp) / "published-jobs-backup.json").exists())


if __name__ == "__main__":
    unittest.main()
