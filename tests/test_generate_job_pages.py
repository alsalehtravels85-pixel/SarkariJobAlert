import tempfile
import unittest
from pathlib import Path
from scripts.generate_job_pages import generate, render_page, public_rows


class StaticJobPageTests(unittest.TestCase):
    def sample(self, **updates):
        row = {
            "id": "abc-123", "title": "Test Recruitment 2026",
            "department": "Test Department", "category": "Vacancy",
            "vacancies": 10, "qualification": "12th Pass",
            "last_date": "2099-12-31", "fees": "100",
            "age_limit": "18-25 years", "selection_process": "Written Exam",
            "notification_url": "https://example.gov.in/notice.pdf",
            "apply_url": "https://example.gov.in/apply",
            "description": "उम्मीदवार आधिकारिक अधिसूचना पढ़ें।",
            "status": "published",
        }
        row.update(updates)
        return row

    def test_page_has_unique_canonical_metadata_and_official_links(self):
        page = render_page(self.sample())
        self.assertIn("https://sarkari-jobalert.com/jobs/test-recruitment-2026-abc-123.html", page)
        self.assertIn("<title>Test Recruitment 2026 | Sarkari Job Alert</title>", page)
        self.assertIn("12th Pass", page)
        self.assertIn("https://example.gov.in/notice.pdf", page)
        self.assertIn('rel="noopener noreferrer"', page)
        self.assertIn("स्वतंत्र सूचना वेबसाइट", page)

    def test_untrusted_html_is_escaped(self):
        page = render_page(self.sample(title="<script>alert(1)</script>"))
        self.assertNotIn("<script>alert(1)</script>", page)
        self.assertIn("&lt;script&gt;", page)

    def test_drafts_and_expired_vacancies_are_excluded(self):
        rows = [
            self.sample(),
            self.sample(id="draft-1", status="draft"),
            self.sample(id="expired-1", last_date="2000-01-01"),
        ]
        self.assertEqual([x["id"] for x in public_rows(rows)], ["abc-123"])

    def test_admit_card_and_result_fields_are_rendered(self):
        admit = self.sample(category="Admit Card", exam_date="2099-01-01",
                            admit_card_release_date="2098-12-20",
                            admit_card_url="https://example.gov.in/admit")
        self.assertIn("प्रवेश पत्र डाउनलोड करें", render_page(admit))
        result = self.sample(category="Result", result_date="2099-02-01",
                             result_status="Declared", result_url="https://example.gov.in/result")
        self.assertIn("परिणाम / नोटिस देखें", render_page(result))
        self.assertIn("Declared", render_page(result))

    def test_result_page_prefers_specific_official_notice_over_homepage(self):
        row = self.sample(
            category="Result",
            result_url="https://bpsc.bihar.gov.in/",
            notification_url="https://bpsc.bihar.gov.in/wp-content/uploads/result.pdf",
            merit_list_url="https://bpsc.bihar.gov.in/",
        )
        page = render_page(row)
        self.assertIn('href="https://bpsc.bihar.gov.in/wp-content/uploads/result.pdf"', page)
        self.assertNotIn(">मेरिट सूची ↗</a>", page)

    def test_generator_removes_stale_html_but_preserves_other_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "jobs"
            out.mkdir()
            (out / "old.html").write_text("old", encoding="utf-8")
            (out / "keep.txt").write_text("keep", encoding="utf-8")
            generate([self.sample()], output=out)
            self.assertTrue((out / "test-recruitment-2026-abc-123.html").exists())
            self.assertFalse((out / "old.html").exists())
            self.assertTrue((out / "keep.txt").exists())


if __name__ == "__main__":
    unittest.main()
