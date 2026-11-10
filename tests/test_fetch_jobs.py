import unittest

from scripts import fetch_jobs


class ScannerRegressionTests(unittest.TestCase):

    def test_stale_dated_archive_notice_is_filtered(self):
        self.assertTrue(fetch_jobs.has_stale_notice_date("Recruitment notice dated 24-Sep-2016"))
        self.assertFalse(fetch_jobs.has_stale_notice_date("Recruitment notice dated 24-Oct-2026"))

    def test_stale_archive_row_with_old_and_new_dates_is_filtered(self):
        self.assertTrue(fetch_jobs.has_stale_notice_date(
            "Recruitment notice dated 24-Sep-2016 updated 24-Oct-2026"
        ))

    def test_leading_employment_news_date_is_notification_date_not_deadline(self):
        self.assertEqual(
            fetch_jobs.listing_notification_date(
                "19 Dec 2026 NOTICE REGARDING ADVT. NO. D-6/E-1/2025"
            ),
            "2026-12-19",
        )
        self.assertIsNone(fetch_jobs.listing_notification_date(
            "NOTICE REGARDING ADVT. NO. D-6/E-1/2025 dated 19 Dec 2026"
        ))

    def test_discover_links_ignores_old_archive_entries(self):
        html = """
        <html><body><ul>
        <li><a href="/old.pdf">Recruitment of Officer Grade A dated 21-Aug-2015</a></li>
        <li><a href="/new.pdf">Recruitment of Assistant dated 24-Oct-2026</a></li>
        </ul></body></html>
        """
        found = fetch_jobs.discover_links(html, "https://sebi.gov.in/vacancies")
        self.assertEqual(len(found), 1)
        self.assertIn("new.pdf", found[0][1])

    def test_vacancy_and_deadline_regexes_extract_real_values(self):
        text = (
            "Total Number of Vacancies: 125 "
            "Last Date to Apply: 30 November 2026 "
            "Educational Qualification: Graduation in any discipline with "
            "minimum 50 percent marks. Age Limit: 18 to 30 years."
        )
        fields = fetch_jobs.extract_fields(text)
        self.assertEqual(fields["vacancies"], "125")
        self.assertEqual(fields["last_date"], "2026-11-30")
        self.assertIsNotNone(fields["qualification"])

    def test_extended_last_date_labels_are_supported(self):
        text = "Closing date for online application: 30 November 2026"
        self.assertEqual(fetch_jobs.extract_fields(text)["last_date"], "2026-11-30")

    def test_year_first_date_is_supported(self):
        self.assertEqual(fetch_jobs.parse_date("2026-11-30"), "2026-11-30")

    def test_officially_linked_up_police_result_host_is_allowed(self):
        url = "https://upcons2025.com/finalResultsupConstable/homepage_new.aspx"
        self.assertTrue(fetch_jobs.official(url))
        self.assertTrue(fetch_jobs.up_official(url))

    def test_upprpb_notice_discovers_external_official_result_portal(self):
        html = """
        <html><body><div>
        <a href="https://upcons2025.com/finalResultsupConstable/homepage_new.aspx">
        उत्तर प्रदेश पुलिस में आरक्षी नागरिक पुलिस एवं समकक्ष पदों पर
        सीधी भर्ती-2025 के अन्तर्गत अन्तिम चयन परिणाम देखने हेतु लिंक
        </a></div></body></html>
        """
        found = fetch_jobs.discover_up_updates(html, "https://uppbpb.gov.in/Home/Notice")
        self.assertEqual(len(found), 1)
        self.assertEqual(found[0][0], "Result")
        self.assertIn("upcons2025.com", found[0][2])

    def test_result_landing_page_is_valid_action_when_lists_use_generic_buttons(self):
        url = "https://upcons2025.com/finalResultsupConstable/homepage_new.aspx"
        html = """
        <html><body><h1>FINAL RESULT</h1>
        <a href="/finalResultsupConstable/Postwisedisplay.aspx?postID=1">
        Click here to View List 1 to 6 of Constable Civil Police
        </a></body></html>
        """
        text = "FINAL RESULT Click here to View List 1 to 6 of Constable Civil Police"
        self.assertEqual(fetch_jobs.verified_up_action_link(html, url, "Result", text), url)


if __name__ == "__main__":
    unittest.main()
