Run python scripts/fetch_jobs.py
  
SARKARI JOB ALERT - OFFICIAL SOURCE CHECK
Run time UTC: 2026-10-28T12:18:24.802151+00:00
Detected notices are saved as DRAFT, not auto-published.
Checking: Staff Selection Commission
  Page read; candidates added: 0 (https://ssc.gov.in/)
  Total candidates for source: 0
Checking: UPSC
  Connection error: HTTPSConnectionPool(host='upsc.gov.in', port=443): Max retries exceeded with url: / (Caused by ConnectTimeoutError(<HTTPSConnection(host='upsc.gov.in', port=443) at 0x7fc60871c590>, 'Connection to upsc.gov.in timed out. (connect timeout=12)'))
  Page read; candidates added: 23 (https://www.upsc.gov.in/)
  Connection error: HTTPSConnectionPool(host='upsc.gov.in', port=443): Max retries exceeded with url: /recruitment/recruitment-advertisement (Caused by ConnectTimeoutError(<HTTPSConnection(host='upsc.gov.in', port=443) at 0x7fc6086ee000>, 'Connection to upsc.gov.in timed out. (connect timeout=12)'))
  Total candidates for source: 23
Checking: IBPS
  SSL error: HTTPSConnectionPool(host='www.ibps.in', port=443): Max retries exceeded with url: / (Caused by SSLError(SSLCertVerificationError(1, '[SSL: CERTIFICATE_VERIFY_FAILED] certificate verify failed: unable to get local issuer certificate (_ssl.c:1010)')))
  SSL error: HTTPSConnectionPool(host='www.ibps.in', port=443): Max retries exceeded with url: /index.php/recruitment/ (Caused by SSLError(SSLError(1, '[SSL: UNEXPECTED_MESSAGE] unexpected message (_ssl.c:1010)')))
  SSL error: HTTPSConnectionPool(host='www.ibps.in', port=443): Max retries exceeded with url: /index.php/crp-updates/ (Caused by SSLError(SSLError(1, '[SSL: UNEXPECTED_MESSAGE] unexpected message (_ssl.c:1010)')))
  Total candidates for source: 0
Checking: Railway Recruitment Boards
  Page read; candidates added: 1 (https://indianrailways.gov.in/)
  Connection error: HTTPSConnectionPool(host='www.rrbcdg.gov.in', port=443): Max retries exceeded with url: /employment-notices.php (Caused by ConnectTimeoutError(<HTTPSConnection(host='www.rrbcdg.gov.in', port=443) at 0x7fc608407350>, 'Connection to www.rrbcdg.gov.in timed out. (connect timeout=12)'))
  Total candidates for source: 1
Checking: State Bank of India Careers
  Skipped redirect outside official host: https://sbi.bank.in/web/careers
  Skipped redirect outside official host: https://sbi.bank.in/web/careers
  Skipped redirect outside official host: https://sbi.bank.in/sitemap.xml
  HTTP 404: https://sbi.co.in/sitemap_index.xml
  Skipped redirect outside official host: https://sbi.bank.in/sitemap.xml
  HTTP 404: https://bank.sbi/sitemap_index.xml
  Total candidates for source: 0
  Saved as draft [Answer Key]: Answer Keys
  Saved as draft [Syllabus]: Revised Syllabus and Scheme
  DATABASE SAVE FAILED [Recruitment Advertisements Status of Lateral Recruitment Cases (Advertisement-wise) Online Recruitment Application (ORA) Status of Recruitment Cases (Advertisement-wise) Forms for Certificates Recruitment Tests Recruitment Requisition Recruitment cas]: {'message': 'new row for relation "jobs" violates check constraint "jobs_title_check"', 'code': '23514', 'hint': None, 'details': 'Failing row contains (30945ca0-38b8-4ed3-822c-cd5e101a0e0a, Recruitment Advertisements Status of Lateral Recruitment Cases (..., UPSC, Latest Jobs, , null, , , , , https://www.upsc.gov.in/, https://www.upsc.gov.in/, Automatically detected candidate notice from an official source...., draft, null, 2026-10-28 12:20:56.756519+00, 2026-10-28 12:20:56.756519+00).'}
  Saved as draft [Latest Jobs]: Status of Lateral Recruitment Cases (Advertisement-wise)
  Saved as draft [Latest Jobs]: Status of Recruitment Cases (Advertisement-wise)
  Saved as draft [Latest Jobs]: Recruitment Tests
  Saved as draft [Latest Jobs]: Recruitment Requisition
  Saved as draft [Latest Jobs]: Recruitment cases kept on hold on account of Pending Litigations
  Saved as draft [Latest Jobs]: Notice regarding change in recruitment process for six (06) posts advertised vide Advt. No. 13-2025
  Saved as draft [Results]: Written Result (with name): Combined Section Officers' (Grade 'B') LDCE-2025 and Combined Stenographers' (Grade 'B'-Grade-'I') LDCE-2019, 2020 & 2021
  Saved as draft [Results]: Written Result: Combined Section Officers' (Grade 'B') LDCE-2025 and Combined Stenographers' (Grade 'B'-Grade-'I') LDCE-2019, 2020 & 2021
  Saved as draft [Results]: Final Result: 02 Posts of Assistant Director Grade-II (IEDS) (Leather & Footwear), Ministry of MSME
  Saved as draft [Results]: Written Result (with name): Central Armed Police Forces (ACs) Examination, 2026
  Saved as draft [Results]: Final Result: 03 Posts of Assistant Director Grade-II (IEDS) (Chemical), Ministry of MSME
  Saved as draft [Results]: Final Result: CISF AC(EXE) LDCE-2026
  Saved as draft [Results]: Written Result (with name): Combined Medical Services Examination, 2026
  Saved as draft [Results]: Written Result: Combined Medical Services Examination, 2026
  Saved as draft [Results]: Written Result: Central Armed Police Forces (ACs) Examination, 2026
  Saved as draft [Latest Jobs]: Recruitment Advertisements
  Saved as draft [Latest Jobs]: Apply Online
  Saved as draft [Results]: Written Results
  Saved as draft [Results]: Final Results
  Saved as draft [Latest Jobs]: Vacancies in UPSC
  Saved as draft [Latest Jobs]: Vacancies
================================
SARKARI JOB ALERT - CHECK REPORT
Pages successfully read: 3
Fetch errors: 8
Candidate notices: 24
New notices saved as drafts: 23
Duplicates skipped: 0
Database save failures: 1
================================
Error: Process completed with exit code 1.
