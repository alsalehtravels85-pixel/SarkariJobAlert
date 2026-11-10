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

    def test_sarkaritoday_is_not_an_official_host(self):
        self.assertFalse(fetch_jobs.official("https://sarkaritoday.com/latest-job/"))
        self.assertEqual(fetch_jobs.host("https://sarkaritoday.com/latest-job/"), "sarkaritoday.com")

    def test_sarkaritoday_article_table_fields_are_extracted(self):
        html = """
        <html><head><title>Test Recruitment - SarkariToday</title></head>
        <body><h1>Test Department Recruitment 2026</h1>
        <table>
          <tr><td>Total Vacancies</td><td>120</td></tr>
          <tr><td>Last Date</td><td>18 November 2026</td></tr>
          <tr><td>Qualification</td><td>MBBS degree from a recognized university</td></tr>
          <tr><td>Age Limit</td><td>18 to 35 years</td></tr>
          <tr><td>Application Fee</td><td>₹200 for all candidates</td></tr>
          <tr><td>Selection Process</td><td>Interview and document verification</td></tr>
        </table>
        <a href="https://example.gov.in/notice.pdf">Official Notification PDF</a>
        <a href="https://example.gov.in/apply">Apply Online</a>
        </body></html>
        """
        result = fetch_jobs.extract_sarkaritoday_article(html, "https://sarkaritoday.com/test-recruitment/")
        self.assertEqual(result["title"], "Test Department Recruitment 2026")
        self.assertEqual(result["vacancies"], "120")
        self.assertEqual(result["last_date"], "2026-11-18")
        self.assertEqual(result["qualification"], "MBBS degree from a recognized university")
        self.assertEqual(result["age_limit"], "18 to 35 years")
        self.assertEqual(result["fees"], "₹200 for all candidates")
        self.assertEqual(result["selection_process"], "Interview and document verification")
        self.assertEqual(result["official_url"], "https://example.gov.in/notice.pdf")
        self.assertEqual(result["apply_url"], "https://example.gov.in/apply")

    def test_sarkaritoday_never_uses_article_or_non_pdf_as_official_notice(self):
        html = """
        <html><body><h1>Test Recruitment 2026</h1>
        <table>
          <tr><td>Total Vacancies</td><td>120</td></tr>
          <tr><td>Last Date</td><td>18 November 2026</td></tr>
          <tr><td>Qualification</td><td>Graduate</td></tr>
        </table>
        <a href="https://example.gov.in/recruitment">Department Website</a>
        </body></html>
        """
        result = fetch_jobs.extract_sarkaritoday_article(
            html, "https://sarkaritoday.com/test-recruitment/"
        )
        self.assertIsNone(result["official_url"])
        self.assertIsNone(result["apply_url"])

    def test_existing_public_text_cleanup_removes_discovery_brand_but_keeps_title(self):
        self.assertEqual(
            fetch_jobs.clean_public_sarkaritoday_title(
                "RRC NWR Apprentice 2026 - SarkariToday"
            ),
            "RRC NWR Apprentice 2026",
        )
        description = fetch_jobs.clean_public_sarkaritoday_text(
            "भर्ती की जानकारी नीचे है।\\nजानकारी का स्रोत: https://sarkaritoday.com/job/\\nअंतिम तिथि: 22 November 2026"
        )
        self.assertNotIn("sarkaritoday", description.lower())
        self.assertIn("भर्ती की जानकारी", description)
        self.assertIn("अंतिम तिथि", description)

    def test_sarkaritoday_draft_description_has_no_discovery_brand_or_link(self):
        description = fetch_jobs.build_sarkaritoday_draft_description(
            "Test Recruitment 2026",
            {"vacancies": "120", "qualification": "Graduate", "last_date": "2026-11-18"},
            "https://sarkaritoday.com/test-recruitment/",
        )
        self.assertNotIn("SarkariToday", description)
        self.assertNotIn("sarkaritoday.com", description)

    def test_sarkaritoday_official_pdf_must_match_vacancy_deadline_and_qualification(self):
        article = {
            "department": "Health Department",
            "vacancies": "120",
            "last_date": "2026-11-18",
            "qualification": "MBBS degree from a recognized university",
        }
        pdf = (
            "Health Department Recruitment Notice. Total Number of Vacancies: 120 "
            "Last Date to Apply: 18 November 2026 "
            "Educational Qualification: MBBS degree from a recognized university. "
            "Age Limit: 18 to 35 years. Read all instructions before applying. "
        ) * 4
        verified, _ = fetch_jobs.verify_sarkaritoday_official_pdf(
            article, pdf, "https://example.gov.in/notice.pdf"
        )
        self.assertTrue(verified)

    def test_sarkaritoday_pdf_mismatch_stays_unverified(self):
        article = {
            "department": "Health Department",
            "vacancies": "120",
            "last_date": "2026-11-18",
            "qualification": "MBBS degree from a recognized university",
        }
        pdf = (
            "Health Department Recruitment Notice. Total Number of Vacancies: 80 "
            "Last Date to Apply: 18 November 2026 "
            "Educational Qualification: MBBS degree from a recognized university. "
            "Age Limit: 18 to 35 years. Read all instructions before applying. "
        ) * 4
        verified, _ = fetch_jobs.verify_sarkaritoday_official_pdf(
            article, pdf, "https://example.gov.in/notice.pdf"
        )
        self.assertFalse(verified)

    def test_sarkaritoday_article_discovery_rejects_external_hosts(self):
        html = """
        <html><body>
        <a href="/job-1/">Latest Recruitment Vacancy 2026</a>
        <a href="https://evil.example/job/">Latest Recruitment Vacancy 2026</a>
        </body></html>
        """
        found = fetch_jobs.discover_sarkaritoday_articles(html, "https://sarkaritoday.com/latest-job/")
        self.assertEqual(len(found), 1)
        self.assertEqual(found[0][1], "https://sarkaritoday.com/job-1/")

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
