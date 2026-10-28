import os
import re
import sys
import time
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup
from supabase import create_client

# This script deliberately saves records as DRAFT for manual verification.
SUPABASE_URL = os.getenv("SUPABASE_URL", "").strip()
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "").strip()

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; SarkariJobAlertBot/1.0; +https://github.com/alsalehtravels85-pixel/SarkariJobAlert)"
}
TIMEOUT = (8, 18)
MAX_TITLE_LEN = 180

SOURCES = [
    {
        "name": "Staff Selection Commission",
        "urls": ["https://ssc.gov.in/"],
        "hosts": {"ssc.gov.in", "www.ssc.gov.in"},
    },
    {
        "name": "UPSC",
        "urls": ["https://www.upsc.gov.in/recruitment/recruitment-advertisement",
                 "https://www.upsc.gov.in/"],
        "hosts": {"upsc.gov.in", "www.upsc.gov.in"},
    },
    {
        "name": "IBPS",
        "urls": ["https://www.ibps.in/"],
        "hosts": {"ibps.in", "www.ibps.in"},
    },
    {
        "name": "Railway Recruitment Boards",
        "urls": ["https://indianrailways.gov.in/"],
        "hosts": {"indianrailways.gov.in", "www.indianrailways.gov.in"},
    },
    {
        "name": "State Bank of India Careers",
        "urls": ["https://sbi.bank.in/web/careers/current-openings"],
        "hosts": {"sbi.bank.in", "www.sbi.bank.in", "sbi.co.in", "www.sbi.co.in", "bank.sbi", "www.bank.sbi"},
    },
]

BAD_EXACT = {
    "home", "homepage", "careers", "recruitment", "recruitment advertisements",
    "recruitment advertisement", "recruitment tests", "recruitment requisition",
    "apply online", "vacancies", "vacancy", "results", "written results",
    "final results", "answer keys", "answer key", "revised syllabus and scheme",
    "syllabus", "admit card", "admit cards", "archives", "tenders", "notice",
    "notices", "latest updates", "view all", "read more", "click here",
    "online recruitment application (ora)", "forms for certificates",
}
BAD_CONTAINS = [
    "privacy policy", "terms and conditions", "screen reader", "skip to",
    "accessibility", "contact us", "feedback", "site map", "sitemap",
]

JOB_HINTS = [
    "recruitment of", "recruitment for", "engagement of", "applications are invited",
    "invited for", "apply online", "advertisement no", "advt. no", "vacancy",
    "vacancies", "post of", "posts of", "selection post", "notification",
    "apprentice", "probationary officer", "clerk", "officer", "constable",
    "assistant", "engineer", "technician", "group d", "group c", "junior",
    "recruitment notice", "employment notice",
]
RESULT_HINTS = ["result", "merit list", "score card", "scorecard"]
ADMIT_HINTS = ["admit card", "call letter", "hall ticket"]
ANSWER_HINTS = ["answer key", "answer keys"]
SYLLABUS_HINTS = ["syllabus", "exam scheme"]
ADMISSION_HINTS = ["admission", "entrance test", "entrance examination"]

def clean_text(value):
    return re.sub(r"\s+", " ", value or "").strip()

def normalize_title(title):
    title = clean_text(title)
    title = re.sub(r"^(click here|read more|view details)\s*[-:|]?\s*", "", title, flags=re.I)
    return title[:MAX_TITLE_LEN].strip(" -|:;")

def classify(title):
    low = title.lower()
    if any(x in low for x in RESULT_HINTS):
        return "Results"
    if any(x in low for x in ADMIT_HINTS):
        return "Admit Card"
    if any(x in low for x in ANSWER_HINTS):
        return "Answer Key"
    if any(x in low for x in SYLLABUS_HINTS):
        return "Syllabus"
    if any(x in low for x in ADMISSION_HINTS):
        return "Admission"
    return "Latest Jobs"

def is_valid_candidate(title, href, source_hosts):
    title = clean_text(title)
    if not title or len(title) < 14:
        return False
    low = title.lower().strip(" .:-")
    if low in BAD_EXACT:
        return False
    if any(term in low for term in BAD_CONTAINS):
        return False
    parsed = urlparse(href)
    if parsed.scheme not in ("http", "https") or parsed.hostname not in source_hosts:
        return False
    # Require a notice-like title; do not turn every navigation link into a job.
    if classify(title) != "Latest Jobs":
        return True
    return any(hint in low for hint in JOB_HINTS) and len(title.split()) >= 3

def fetch_page(session, url, allowed_hosts):
    try:
        response = session.get(url, timeout=TIMEOUT, allow_redirects=True)
        final_host = (urlparse(response.url).hostname or "").lower()
        if final_host not in allowed_hosts:
            print(f"  Skipped redirect outside official host: {response.url}")
            return None, None
        if response.status_code >= 400:
            print(f"  HTTP {response.status_code}: {response.url}")
            return None, None
        response.encoding = response.apparent_encoding or response.encoding
        return response.text, response.url
    except requests.exceptions.SSLError as exc:
        print(f"  SSL error for {url}: {exc}")
    except requests.exceptions.RequestException as exc:
        print(f"  Connection error for {url}: {exc}")
    return None, None

def extract_candidates(html, page_url, source):
    soup = BeautifulSoup(html, "html.parser")
    found = {}
    hosts = source["hosts"]
    for a in soup.select("a[href]"):
        title = normalize_title(a.get_text(" ", strip=True))
        href = urljoin(page_url, a.get("href", "").strip())
        if not is_valid_candidate(title, href, hosts):
            continue
        # Avoid generic homepage links being used as both notification and application URL.
        if urlparse(href).path in ("", "/"):
            continue
        found[href] = {
            "title": title,
            "notification_url": href,
            "apply_url": href,
            "department": source["name"],
            "category": classify(title),
            "status": "draft",
            "description": "Automatically detected candidate notice from an official source. Verify the official notice, eligibility, dates, and application link before publishing.",
        }
    return list(found.values())

def main():
    if not SUPABASE_URL or not SUPABASE_KEY:
        print("ERROR: SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be set as environment secrets.")
        return 2

    db = create_client(SUPABASE_URL, SUPABASE_KEY)
    session = requests.Session()
    session.headers.update(HEADERS)
    candidates = []
    pages_read = 0
    fetch_errors = 0
    seen_urls = set()

    print("SARKARI JOB ALERT - OFFICIAL SOURCE CHECK")
    print("Detected notices are saved as DRAFT, not auto-published.")

    for source in SOURCES:
        print(f"Checking: {source['name']}")
        source_count = 0
        for url in source["urls"]:
            html, final_url = fetch_page(session, url, source["hosts"])
            if not html:
                fetch_errors += 1
                continue
            pages_read += 1
            page_candidates = extract_candidates(html, final_url, source)
            for item in page_candidates:
                href = item["notification_url"]
                if href not in seen_urls:
                    candidates.append(item)
                    seen_urls.add(href)
                    source_count += 1
            print(f"  Page read; candidates added: {len(page_candidates)} ({final_url})")
            time.sleep(0.5)
        print(f"  Total candidates for source: {source_count}")

    saved = 0
    duplicates = 0
    failures = 0

    for item in candidates:
        try:
            # The database constraint is preserved. Reject rather than truncate to a misleading title.
            title = normalize_title(item["title"])
            if len(title) < 14 or len(title) > MAX_TITLE_LEN:
                print(f"  Skipped invalid title: {title[:80]}")
                continue
            item["title"] = title
            existing = (
                db.table("jobs")
                .select("id")
                .eq("notification_url", item["notification_url"])
                .limit(1)
                .execute()
            )
            if existing.data:
                duplicates += 1
                continue
            db.table("jobs").insert(item).execute()
            saved += 1
            print(f"  Saved as draft [{item['category']}]: {item['title']}")
        except Exception as exc:
            failures += 1
            print(f"  DATABASE SAVE FAILED [{item.get('title', '')[:80]}]: {exc}")

    print("================================")
    print("SARKARI JOB ALERT - CHECK REPORT")
    print(f"Pages successfully read: {pages_read}")
    print(f"Fetch errors: {fetch_errors}")
    print(f"Candidate notices: {len(candidates)}")
    print(f"New notices saved as drafts: {saved}")
    print(f"Duplicates skipped: {duplicates}")
    print(f"Database save failures: {failures}")
    print("================================")

    # Fail only for database failures or total inability to read sources.
    if failures or pages_read == 0:
        return 1
    return 0

if __name__ == "__main__":
    sys.exit(main())
