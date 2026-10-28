# SarkariJobAlert — setup guide (Hinglish)

Yeh lightweight static website starter hai. Aapke laptop par local server chalana zaroori nahi; ise browser-based GitHub/Cloudflare Pages workflow se host kar sakte hain. Live database ke liye Supabase use hoga.

## Files
- `index.html` — public homepage, search, categories, job details and admin login.
- `styles.css` — responsive/mobile-first styling.
- `app.js` — public job loading and authenticated admin CRUD.
- `config.js` — Supabase project URL and anon/public key.
- `schema.sql` — jobs + push tables, missing-column migration, and Row Level Security policies.
- `about.html`, `contact.html`, `privacy.html`, `disclaimer.html` — basic information pages.

## Step 1 — Create Supabase database
1. Open https://supabase.com/ and create a project. Use a strong database password and keep it private.
2. In the Supabase project, open **SQL Editor**.
3. Open this folder's `schema.sql`, copy all of it, paste into SQL Editor, and click **Run**.
4. Go to **Project Settings → API** (or API Keys depending on the dashboard).
5. Copy the **Project URL** and the **anon/public key** only.
6. Open `config.js`; replace the two placeholder values.
   - Never put a `service_role` or secret key in `config.js`.
   - The anon key is designed for frontend use only because database access is restricted by RLS policies.

## Step 2 — Create private admin account
1. Supabase Dashboard → **Authentication → Users**.
2. Create/add a user using your admin email and a strong password.
3. Public signups are not used by this starter. Keep the admin email/password private.
4. Log in on your website using the **Admin Login** button.
5. If admin CRUD returns permission errors, check that the `jobs` table and RLS policies from `schema.sql` were created correctly.

## Step 3 — Deploy without loading your laptop
Recommended: Cloudflare Pages static hosting.
1. Open https://pages.cloudflare.com/ and sign in/create account.
2. Put the project files in a GitHub repository (GitHub web interface can upload files; no local install required).
3. In Cloudflare Pages choose **Create a project / Connect to Git**, select the repository.
4. Framework preset: **None**. Build command: leave blank. Output directory: `/` (if accepted) or the root directory setting shown by the dashboard.
5. Deploy. The website runs on Cloudflare's servers; your laptop can be off after deployment.
6. The exact free plan limits can change. Do not enter payment details unless you choose a paid plan.

## Step 4 — Test before publishing
- Open the live site in an incognito/private window.
- Public visitors should see only posts with status `published`.
- Admin login should require the Supabase user account.
- Add a draft first, confirm it is not public, then publish it.
- Test official notification/apply links.
- Never publish sample/demo records as real vacancies. Remove the demo cards after the database is configured.

## Important safety and accuracy notes
- This is an MVP starter, not a fully audited production system.
- Verify the RLS behavior with a non-admin test browser/account before real use.
- The included policies allow a signed-in user to edit/delete rows they created. For a single-owner portal, create only your own admin user and do not give credentials to others. A future multi-admin role table/policy is recommended before adding staff accounts.
- Do not store Aadhaar, passwords, payment data, or other sensitive customer information in this job portal.
- The GitHub Actions workflow runs the source checker daily (08:00 AM IST) and can also be run manually from Actions. It installs `pypdf` to read text-based PDF notices.
- Add GitHub repository secrets `SUPABASE_URL` and `SUPABASE_SERVICE_ROLE_KEY` for the scraper. Never place the service-role key in `config.js` or commit it into Git.
- The fetcher now opens candidate official notice pages and tries to extract explicitly labeled fields from HTML or text-based PDF notices. It publishes only when it finds a clear application link, last date, qualification, vacancy count, official notification link, and department.
- GitHub Actions sets `AUTO_PUBLISH_VERIFIED=true`; incomplete records remain drafts. This is a conservative auto-publishing gate, not a guarantee that every government notice can be parsed. Scanned/image-only PDFs, JavaScript-only pages, CAPTCHA, blocked pages, or unusual formats may not parse and may remain drafts or be skipped.
- SarkariResult scraping is not enabled because the site's published terms prohibit automated scraping without permission. It can be added if you obtain written permission or a supported feed/API. Use official recruitment notices as the final source for deadlines, eligibility, fees, and application links.
- Existing jobs are not deleted by this package. Back up the database before any cleanup.
- AdSense approval is not guaranteed; add original, accurate content and review Google policies before applying.
- Replace `https://example.com/` canonical URL in `index.html` with the final domain after you purchase/choose it.
- The About/Contact/Privacy/Disclaimer pages are starter templates. Replace placeholder contact details and review privacy terms before going live.

## Current scope
Included: responsive homepage, search, category filters, job detail dialog, Supabase connection, admin login, add/edit/delete, draft/publish, official link fields.
Not included yet: automated vacancy scraping/feed integration, email alerts, user accounts, application submissions, analytics, PWA install prompt, or custom domain.


## Changes in this updated package
- `schema.sql` now creates the `jobs` table for fresh projects and adds missing columns for older projects without deleting existing job rows.
- The scraper no longer incorrectly sets the notification URL as `apply_url`.
- Scraped records retain `source_name` and `source_url`, and are marked draft until the details can be verified.
- Public preview no longer shows fake sample vacancies when Supabase is not configured.
- "More" category now filters Admission and Syllabus; header category buttons also respond.
- Automatic publishing is deliberately gated: link-only records remain drafts. Do not disable this safety gate without testing accurate source-specific parsers.
