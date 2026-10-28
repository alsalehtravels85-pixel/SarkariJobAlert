# SarkariJobAlert update notes

## Fixed
- Added a complete, rerunnable Supabase schema for `jobs` and missing columns.
- Scraper no longer sets a notice URL as the application URL.
- Scraper saves source attribution and keeps discovered links in draft until complete fields are verified.
- Removed fake demo job cards when database configuration is missing.
- Fixed the "More" category filter for Admission and Syllabus.
- Fixed header category controls to filter the listing.

## Important limitation
This package is not a fully reliable hands-free auto-publisher yet. The existing target sites have different page layouts and sometimes block automated requests. The generic crawler discovers notice links but cannot safely infer all fields (especially DOB eligibility, fee, last date, and the true application URL). Such records remain drafts. Source-specific detail parsers plus tests are required before enabling production auto-publishing.

## Data safety
No job rows were deleted. Back up Supabase before any manual cleanup. Never commit `SUPABASE_SERVICE_ROLE_KEY`.

- Added best-effort detail extraction from official notice HTML and text-based PDFs for explicitly labeled last date, notification date, vacancies, qualification, fee, age, selection process, and application links.
- GitHub Actions enables strict auto-publishing; incomplete or unparseable records stay draft.
- Added `pypdf` to the workflow. Scanned PDFs and unsupported/blocked pages still require review.
- SarkariResult scraping remains disabled unless permission or an authorized feed/API is available.
