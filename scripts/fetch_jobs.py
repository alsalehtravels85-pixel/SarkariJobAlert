import os
import re
import sys
import time
from urllib.parse import urljoin, urlparse, urldefrag

import requests
from bs4 import BeautifulSoup
from supabase import create_client

# All discovered notices remain DRAFT for manual verification.
SUPABASE_URL = os.getenv("SUPABASE_URL", "").strip()
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "").strip()

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (compatible; SarkariJobAlertBot/1.1; "
        "+https://github.com/alsalehtravels85-pixel/SarkariJobAlert)"
    )
}
TIMEOUT = (8, 18)
MAX_TITLE_LEN = 180
ALLOWED_CATEGORIES = {
    "Latest Jobs", "Admit Card", "Results", "Answer Key", "Admission", "Syllabus"
}

SOURCES = [
    {
        "name": "Staff Selection Commission",
        "urls": ["https://ssc.gov.in/"],
        "hosts": {"ssc.gov.in", "www.ssc.gov.in"},
    },
    {
        "name": "UPSC",
        "urls": [
            "https://www.upsc.gov.in/recruitment/recruitment-advertisement",
            "https://www.upsc.gov.in/",
        ],
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
        "hosts": {
            "sbi.bank.in", "www.sbi.bank.in", "sbi.co.in",
            "www.sbi.co.in", "bank.sbi", "www.bank.sbi"
        },
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
    "current openings", "career", "careers at sbi",
}
BAD_CONTAINS = [
    "privacy policy", "terms and conditions", "screen reader", "skip to",
    "accessibility", "contact us", "feedback", "site map", "sitemap",
    "cookie policy", "social media", "follow us",
]

# These phrases usually indicate a result/update, not a fresh vacancy.
RESULT_HINTS = [
    "result", "merit list", "score card", "scorecard", "marks secured",
    "candidates provisionally selected", "provisionally selected",
    "selected candidates", "list of candidates", "nil selection",
    "no candidate found suitable", "waitlist", "wait list",
    "preliminary exam", "preliminary examination", "main exam",
    "written result", "final result", "result & archive",
]
ADMIT_HINTS = ["admit card", "call letter", "hall ticket", "download call letter"]
ANSWER_HINTS = ["answer key", "answer keys", "final answer key", "provisional answer key"]
SYLLABUS_HINTS = ["syllabus", "exam scheme", "scheme of examination"]
ADMISSION_HINTS = ["admission", "entrance test", "entrance examination", "counselling", "counseling"]

# A Latest Jobs notice should look like an actual recruitment announcement.
JOB_HINTS = [
    "recruitment of", "recruitment for", "engagement of",
    "applications are invited", "inviting applications", "advertisement no",
    "advt. no", "notification for", "recruitment notification",
    "recruitment notice", "employment notice", "apply online",
    "apprentice", "probationary officer", "junior associate",
    "constable recruitment", "group d", "group c", "vacancy for",
    "vacancies for", "posts of", "post of", "recruitment drive",
]
# These are process updates, not reliable evidence of a fresh vacancy.
NON_VACANCY_HINTS = [
    "interview schedule", "interview call letter", "provisionally selected",
    "selected candidates", "marks secured", "nil selection",
    "no candidate found suitable", "recruitment cases", "kept on hold",
    "pending litigations", "result", "merit list", "score card", "scorecard",
    "waitlist", "wait list", "written test result", "preliminary exam",
    "main exam result", "final result", "revised syllabus",
]

def clean_text(value):
    return re.sub(r"\s+", " ", value or "").strip()

def normalize_title(title):
    title = clean_text(title)
    title = re.sub(
        r"^(click here|read more|view details|know more)\s*[-:|]?\s*",
        "", title, flags=re.I
    )
    # Remove common file-size suffixes from link text.
    title = re.sub(r"\s*\(\s*\d+(?:\.\d+)?\s*(?:kb|mb)\s*\)\s*$", "", title, flags=re.I)
    return title.strip(" -|:;")

def title_key(title):
    return re.sub(r"[^a-z0-9]+", " ", clean_text(title).lower()).strip()

def classify(title):
    low = title.lower()
    # More specific categories first.
    if any(x in low for x in ANSWER_HINTS):
        return "Answer Key"
    if any(x in low for x in ADMIT_HINTS):
        return "Admit Card"
    if any(x in low for x in SYLLABUS_HINTS):
        return "Syllabus"
    if any(x in low for x in ADMISSION_HINTS):
        return "Admission"
    if any(x in low for x in RESULT_HINTS):
        return "Results"
    return "Latest Jobs"

def is_valid_candidate(title, href, source_hosts):
    title = clean_text(title)
    if not title or len(title) < 14:
        return False

    low = title.lower().strip(" .:-")
    if low in BAD_EXACT or any(term in low for term in BAD_CONTAINS):
        return False

    parsed = urlparse(href)
    host = (parsed.hostname or "").lower()
    if parsed.scheme not in ("http", "https") or host not in source_hosts:
        return False
    if parsed.path in ("", "/"):
        return False

    category = classify(title)

    if category == "Latest Jobs":
        # Don't mislabel selection/result/process notices as new vacancies.
        if any(term in low for term in NON_VACANCY_HINTS):
            return False
        # Require a strong recruitment clue, not just words like "assistant" or "officer".
        if not any(hint in low for hint in JOB_HINTS):
            return False
        if len(title.split()) < 3:
            return False

    return True

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
        href, _fragment = urldefrag(href)
        href = href.rstrip("/") if urlparse(href).path not in ("", "/") else href

        if not is_valid_candidate(title, href, hosts):
            continue

        category = classify(title)
        if category not in ALLOWED_CATEGORIES:
            continue

        found[href] = {
            "title": title[:MAX_TITLE_LEN].strip(" -|:;"),
            "notification_url": href,
            # The real application link may be inside the notice; do not pretend this is confirmed.
            "apply_url": href,
            "department": source["name"],
            "category": category,
            "status": "draft",
            "description": (
                "Automatically detected link from an official source. "
                "This record is a draft. Verify notice date, eligibility, "
                "vacancies, last date, and the official application link before publishing."
            ),
        }

    return list(found.values())

def load_existing(db):
    """Load existing URLs and titles so the script avoids duplicates across the current table."""
    existing_urls = set()
    existing_titles = set()
    page_size = 1000
    start = 0

    while True:
        result = (
            db.table("jobs")
            .select("notification_url,title,department")
            .range(start, start + page_size - 1)
            .execute()
        )
        rows = result.data or []
        for row in rows:
            url = clean_text(row.get("notification_url"))
            title = title_key(row.get("title", ""))
            department = title_key(row.get("department", ""))
            if url:
                existing_urls.add(url.rstrip("/"))
            if title:
                existing_titles.add((title, department))
        if len(rows) < page_size:
            break
        start += page_size

    return existing_urls, existing_titles

def main():
    if not SUPABASE_URL or not SUPABASE_KEY:
        print("ERROR: SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be set as GitHub secrets.")
        return 2

    try:
        db = create_client(SUPABASE_URL, SUPABASE_KEY)
        existing_urls, existing_titles = load_existing(db)
    except Exception as exc:
        print(f"ERROR: Could not connect to Supabase or read existing records: {exc}")
        return 2

    session = requests.Session()
    session.headers.update(HEADERS)

    candidates = []
    pages_read = 0
    fetch_errors = 0
    seen_urls = set()
    seen_titles = set()

    print("SARKARI JOB ALERT - OFFICIAL SOURCE CHECK")
    print("All detected notices are saved as DRAFT for manual verification.")
    print(f"Existing database records checked: {len(existing_urls)} URLs")

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
            added_this_page = 0

            for item in page_candidates:
                href_key = item["notification_url"].rstrip("/")
                title_key_value = (title_key(item["title"]), title_key(item["department"]))

                if href_key in seen_urls or href_key in existing_urls:
                    continue
                # Prevent same source/title being saved again via a different URL.
                if title_key_value in seen_titles or title_key_value in existing_titles:
                    continue

                candidates.append(item)
                seen_urls.add(href_key)
                seen_titles.add(title_key_value)
                source_count += 1
                added_this_page += 1

            print(f"  Page read; new candidates found: {added_this_page} ({final_url})")
            time.sleep(0.5)

        print(f"  Total new candidates for source: {source_count}")

    saved = 0
    duplicates = 0
    failures = 0
    rejected = 0

    for item in candidates:
        try:
            title = normalize_title(item["title"])
            if len(title) < 14 or len(title) > MAX_TITLE_LEN:
                rejected += 1
                print(f"  Skipped invalid title: {title[:80]}")
                continue

            if item["category"] not in ALLOWED_CATEGORIES:
                rejected += 1
                print(f"  Skipped invalid category: {item['category']}")
                continue

            # Recheck the database before insert to reduce race-condition duplicates.
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
            print(f"  Saved as draft [{item['category']}]: {title}")

        except Exception as exc:
            failures += 1
            print(f"  DATABASE SAVE FAILED [{item.get('title', '')[:80]}]: {exc}")

    print("================================")
    print("SARKARI JOB ALERT - CHECK REPORT")
    print(f"Pages successfully read: {pages_read}")
    print(f"Fetch errors: {fetch_errors}")
    print(f"Candidate notices after filtering: {len(candidates)}")
    print(f"New notices saved as drafts: {saved}")
    print(f"Duplicates skipped: {duplicates}")
    print(f"Invalid records skipped: {rejected}")
    print(f"Database save failures: {failures}")
    print("================================")
    print("NOTE: Website access errors (403/SSL/timeouts) need source-specific handling.")
    print("NOTE: Confirm dates, eligibility, vacancies, and application URLs before publishing.")

    if failures or pages_read == 0:
        return 1
    return 0

if __name__ == "__main__":
    sys.exit(main())
