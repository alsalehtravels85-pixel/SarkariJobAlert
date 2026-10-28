import os
import re
import sys
import time
import io
from urllib.parse import urljoin, urlparse, urldefrag

import requests
from bs4 import BeautifulSoup
from supabase import create_client

try:
    from pypdf import PdfReader
except ImportError:
    PdfReader = None

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
    {
        "name": "UPSSSC",
        "urls": ["https://upsssc.gov.in/"],
        "hosts": {"upsssc.gov.in", "www.upsssc.gov.in"},
    },
    {
        "name": "UPPSC",
        "urls": ["https://uppsc.up.nic.in/"],
        "hosts": {"uppsc.up.nic.in", "uppsc.up.gov.in", "www.uppsc.up.nic.in"},
    },
    {
        "name": "National Career Service",
        "urls": ["https://www.ncs.gov.in/"],
        "hosts": {"ncs.gov.in", "www.ncs.gov.in"},
    },
    {
        "name": "India Post",
        "urls": ["https://www.indiapost.gov.in/"],
        "hosts": {"indiapost.gov.in", "www.indiapost.gov.in"},
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
        print("  Safe action: certificate verification remains enabled; this source may need an alternate official endpoint.")
    except requests.exceptions.RequestException as exc:
        print(f"  Connection error for {url}: {exc}")
    return None, None


def extract_pdf_text(session, url, allowed_hosts):
    if PdfReader is None:
        return ""
    try:
        response = session.get(url, timeout=TIMEOUT, allow_redirects=True)
        host = (urlparse(response.url).hostname or "").lower()
        if response.status_code >= 400 or host not in allowed_hosts:
            return ""
        ctype = (response.headers.get("Content-Type") or "").lower()
        if not (urlparse(response.url).path.lower().endswith(".pdf") or "pdf" in ctype):
            return ""
        reader = PdfReader(io.BytesIO(response.content))
        return clean_text(" ".join((page.extract_text() or "") for page in reader.pages[:35]))
    except Exception as exc:
        print(f"  PDF extraction unavailable for {url}: {exc}")
        return ""

def extract_notice_details(session, url, allowed_hosts):
    html, final_url = fetch_page(session, url, allowed_hosts)
    text = ""
    if html:
        soup = BeautifulSoup(html, "html.parser")
        for node in soup(["script", "style", "noscript", "nav", "footer", "header"]):
            node.decompose()
        text = clean_text(soup.get_text(" ", strip=True))
        if len(text) < 250:
            for link in soup.select("a[href]"):
                pdf_url = urljoin(final_url, link.get("href", ""))
                if (urlparse(pdf_url).hostname or "").lower() in allowed_hosts and urlparse(pdf_url).path.lower().endswith(".pdf"):
                    pdf_text = extract_pdf_text(session, pdf_url, allowed_hosts)
                    if len(pdf_text) > len(text): text = pdf_text
    elif urlparse(url).path.lower().endswith(".pdf"):
        text = extract_pdf_text(session, url, allowed_hosts)
    if len(text) < 80:
        return {"description": "Official notice detected; readable details could not be extracted. Verify manually before publishing."}
    details = {}
    patterns = {
        "vacancies": [r"(?:total\s+(?:number\s+of\s+)?vacanc(?:y|ies)|total\s+posts?|number\s+of\s+posts?)\s*[:\-]?\s*(\d[\d,]*)"],
        "fees": [r"(?:application\s+fee|exam(?:ination)?\s+fee|registration\s+fee)\s*[:\-]?\s*([^.;]{1,100})"],
        "age_limit": [r"(?:age\s+limit|age\s+criteria|maximum\s+age|minimum\s+age)\s*[:\-]?\s*([^.;]{1,100})"],
        "qualification": [r"(?:educational\s+qualification|minimum\s+qualification|essential\s+qualification|qualification)\s*[:\-]?\s*([^.;]{1,180})"],
        "selection_process": [r"(?:selection\s+process|mode\s+of\s+selection|selection\s+procedure)\s*[:\-]?\s*([^.;]{1,140})"],
    }
    for field, regexes in patterns.items():
        for pattern in regexes:
            m = re.search(pattern, text, flags=re.I)
            if m:
                value = clean_text(m.group(1))
                if value and len(value) <= 180:
                    details[field] = value
                    break
    from datetime import datetime
    date_patterns = {
        "notification_date": r"(?:notification\s+date|advertisement\s+date|published\s+on|date\s+of\s+notification)\s*[:\-]?\s*(\d{1,2}[./-]\d{1,2}[./-]\d{2,4})",
        "last_date": r"(?:last\s+date(?:\s+to\s+apply)?|closing\s+date|apply\s+before)\s*[:\-]?\s*(\d{1,2}[./-]\d{1,2}[./-]\d{2,4})",
        "dob_from": r"(?:date\s+of\s+birth\s+not\s+before|born\s+not\s+before|dob\s+from)\s*[:\-]?\s*(\d{1,2}[./-]\d{1,2}[./-]\d{2,4})",
        "dob_to": r"(?:date\s+of\s+birth\s+not\s+after|born\s+not\s+after|dob\s+to)\s*[:\-]?\s*(\d{1,2}[./-]\d{1,2}[./-]\d{2,4})",
    }
    for field, pattern in date_patterns.items():
        m = re.search(pattern, text, flags=re.I)
        if m:
            raw = m.group(1)
            for fmt in ("%d/%m/%Y", "%d-%m-%Y", "%d.%m.%Y", "%d/%m/%y", "%d-%m-%y", "%d.%m.%y"):
                try:
                    details[field] = datetime.strptime(raw, fmt).date().isoformat()
                    break
                except ValueError:
                    pass
    details["description"] = "Automatically extracted draft. Verify every field against the official notification before publishing."
    return details

def extract_candidates(html, page_url, source, session=None):
    """Extract notice links using link text plus nearby card/row text.

    Official portals often put the title, date and PDF icon in separate elements;
    using only the <a> text misses many valid notices.
    """
    soup = BeautifulSoup(html, "html.parser")
    found = {}
    hosts = source["hosts"]
    links_seen = 0
    rejected_host = 0
    rejected_title = 0

    for a in soup.select("a[href]"):
        href = urljoin(page_url, a.get("href", "").strip())
        href, _fragment = urldefrag(href)
        parsed = urlparse(href)
        host = (parsed.hostname or "").lower()
        if parsed.scheme not in ("http", "https") or host not in hosts:
            rejected_host += 1
            continue
        if parsed.path in ("", "/"):
            continue
        links_seen += 1

        # Combine anchor label with the containing card/list row; many official
        # notice boards use an icon-only PDF link next to the actual title.
        anchor_label = clean_text(" ".join((a.get_text(" ", strip=True), a.get("title", ""), a.get("aria-label", ""))))
        chunks = [anchor_label]
        # Only borrow nearby row/card text when the link itself has no useful label;
        # otherwise a large parent container can merge several unrelated notices.
        if len(anchor_label) < 14 or anchor_label.lower() in {"pdf", "view", "download", "click here", "read more"}:
            for parent in (a.parent, a.parent.parent if a.parent else None):
                if parent:
                    parent_text = clean_text(parent.get_text(" ", strip=True))
                    if len(parent_text) > len(anchor_label):
                        chunks.append(parent_text)
                        if len(parent_text) >= 14:
                            break
        title = normalize_title(" ".join(chunks))
        title = re.sub(r"\b(?:pdf|view|download)\b", " ", title, flags=re.I)
        title = re.sub(r"\s+", " ", title).strip(" -|:;()")
        # Strip repeated site navigation labels, but preserve useful notice text.
        if len(title) > MAX_TITLE_LEN:
            title = title[:MAX_TITLE_LEN].rsplit(" ", 1)[0]

        if not title or len(title) < 14:
            rejected_title += 1
            continue
        low = title.lower()
        if low in BAD_EXACT or any(term in low for term in BAD_CONTAINS):
            rejected_title += 1
            continue
        if any(term in low for term in ("privacy policy", "terms of use", "skip to main", "screen reader")):
            rejected_title += 1
            continue

        # Keep official notices across jobs, results, admit cards, keys and
        # syllabi. Do not require a narrow English phrase like "recruitment of".
        category = classify(title)
        if category == "Latest Jobs" and any(term in low for term in NON_VACANCY_HINTS):
            category = classify(title)
        # Filter generic navigation by requiring a meaningful exam/post clue or
        # a dated/numbered notice. This is deliberately more permissive than before.
        useful_clue = any(term in low for term in (
            "exam", "examination", "recruit", "vacanc", "post", "advertisement",
            "notification", "application", "selection", "constable", "clerk",
            "stenographer", "junior engineer", "group", "answer key", "admit card",
            "result", "merit", "syllabus", "notice", "appointment", "counselling"
        )) or bool(re.search(r"\b(20\d{2}|no\.?\s*\d{1,4})\b", low))
        if not useful_clue:
            rejected_title += 1
            continue

        item = {
            "title": title[:MAX_TITLE_LEN].strip(" -|:;"),
            "notification_url": href,
            "source_url": page_url,
            "apply_url": "",
            "department": source["name"],
            "category": category,
            "status": "draft",
            "description": "Automatically detected official-source notice. Verify the original notice and all fields before publishing.",
        }
        if session is not None and category in {"Latest Jobs", "Admit Card", "Results", "Answer Key", "Admission", "Syllabus"}:
            details = extract_notice_details(session, href, hosts)
            item.update(details)
        # Prefer the more descriptive title if the same URL appears more than once.
        if href not in found or len(item["title"]) > len(found[href]["title"]):
            found[href] = item

    print(f"  Link scan diagnostics: official links={links_seen}, rejected host={rejected_host}, rejected title={rejected_title}, accepted={len(found)}")
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
            .select("notification_url,title,department,category")
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
                existing_titles.add((title, department, title_key(row.get("category", ""))))
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

    print("SARKARI JOB ALERT - OFFICIAL NOTICE + DETAIL EXTRACTION")
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
            page_candidates = extract_candidates(html, final_url, source, session=session)
            added_this_page = 0

            for item in page_candidates:
                href_key = item["notification_url"].rstrip("/")
                title_key_value = (title_key(item["title"]), title_key(item["department"]), item["category"])

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
            title = normalize_title(item
