#!/usr/bin/env python3
"""Conservative, retry-aware official recruitment scanner for SarkariJobAlert.

Safety policy:
- Reads only official government recruitment portals.
- Never disables TLS certificate verification.
- Requires a clear recruitment notice and an explicit future last date.
- PDF is optional; an official HTML notice is acceptable.
- Auto-publishes a vacancy only when a readable official PDF confirms all core facts and a future deadline.
- Keeps HTML-only notices and uncertain/incomplete PDF notices as DRAFT.
- UP Admit Card/Result are UP-only and auto-publish only when an official UP page confirms the update and contains a relevant official action link.
- Inserts new rows only; never edits existing jobs.
- Inserts new rows only; never edits existing jobs or changes the database schema.
"""
import io
import os
import re
import sys
import time
from datetime import datetime, timedelta
from urllib.parse import urljoin, urlparse, urldefrag
from zoneinfo import ZoneInfo

import requests
from bs4 import BeautifulSoup
from pypdf import PdfReader
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

DB = os.getenv("SUPABASE_URL", "").strip().rstrip("/")
KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "").strip()
MARKER = "#sja-auto-scanner-managed"
HEADERS = {
    "User-Agent": "SarkariJobAlertRecruitmentScanner/3.0 (+https://github.com/alsalehtravels85-pixel/SarkariJobAlert)",
    "Accept": "text/html,application/pdf,application/xhtml+xml;q=0.9,*/*;q=0.8",
}
TIMEOUT = (12, 35)
MAX_HTML = 7 * 1024 * 1024
MAX_PDF = 16 * 1024 * 1024
TODAY = datetime.now(ZoneInfo("Asia/Kolkata")).date()

# Uttar Pradesh sources are intentionally checked first.
UP_SOURCES = [
    ("UPSSSC", "https://upsssc.gov.in/"),
    ("UPPSC", "https://uppsc.up.nic.in/"),
    ("UP Police", "https://uppbpb.gov.in/"),
    ("UP NHM", "https://upnrhm.gov.in/"),
]
CENTRAL_SOURCES = [
    ("UP Government Jobs - NCS", "https://www.ncs.gov.in/pages/govt-job-vacancies.aspx"),
    ("UPSC", "https://www.upsc.gov.in/recruitment/recruitment-advertisement"),
    ("SSC", "https://ssc.gov.in/"),
    ("IBPS", "https://www.ibps.in/index.php/recruitment/"),
    ("India Post", "https://www.indiapost.gov.in/vacancies"),
    ("RBI", "https://opportunities.rbi.org.in/scripts/vacancies.aspx"),
    ("SBI Careers", "https://sbi.co.in/web/careers/current-openings"),
    ("DRDO", "https://www.drdo.gov.in/drdo/careers"),
    ("ISRO", "https://www.isro.gov.in/Careers.html"),
    ("Indian Railways", "https://indianrailways.gov.in/railwayboard/"),
    ("NABARD", "https://www.nabard.org/careers-notices1.aspx"),
    ("SEBI", "https://www.sebi.gov.in/sebiweb/about/AboutAction.do?doVacancies=yes"),
    ("TNPSC", "https://www.tnpsc.gov.in/"),
    ("Kerala PSC", "https://www.keralapsc.gov.in/"),
    ("RPSC", "https://rpsc.rajasthan.gov.in/"),
    ("BPSC", "https://bpsc.bihar.gov.in/"),
    ("MPPSC", "https://mppsc.mp.gov.in/"),
    ("Employment News", "https://employmentnews.gov.in/"),
]
SOURCES = UP_SOURCES + CENTRAL_SOURCES

EXACT_HOSTS = {
    "upsssc.gov.in", "uppsc.up.nic.in", "uppbpb.gov.in", "upnrhm.gov.in",
    "upsc.gov.in", "upsconline.nic.in", "ssc.gov.in", "ibps.in",
    "sbi.co.in", "indiapost.gov.in", "opportunities.rbi.org.in",
    "drdo.gov.in", "isro.gov.in", "indianrailways.gov.in", "rrbapply.gov.in",
    "nabard.org", "sebi.gov.in", "tnpsc.gov.in", "keralapsc.gov.in", "sbi.bank.in",
    "rpsc.rajasthan.gov.in", "bpsc.bihar.gov.in", "mppsc.mp.gov.in",
    "ncs.gov.in", "employmentnews.gov.in", "upcons2025.com",
}
RECRUITMENT_HINTS = (
    "recruitment", "vacancy", "vacancies", "applications invited",
    "advertisement no", "advt no", "direct recruitment", "posts of",
    "post of", "apprentice", "probationary officer", "junior associate",
    "constable", "group c", "group d", "staff nurse", "assistant professor",
    "non faculty", "technical assistant", "officer", "clerk", "driver",
    "apply online", "online application",
)
EXCLUDE_HINTS = (
    "result", "answer key", "admit card", "call letter", "interview schedule",
    "interview notice", "interview", "shortlisted candidates", "shortlist",
    "selected candidates", "selection panel", "selection list", "skill test date",
    "score card", "corrigendum", "extension of last date", "extension of time",
    "citizen engagement", "syllabus", "exam calendar", "tender", "deputation",
    "transfer", "revised", "recruitment rules", "recruitment process",
)
DATE_TOKEN = (
    r"(\d{1,2}[./-]\d{1,2}[./-]\d{2,4}|"
    r"\d{1,2}[\s-]+[A-Za-z]{3,9}[\s-]+\d{4}|"
    r"[A-Za-z]{3,9}[\s-]+\d{1,2},?\s+\d{4})"
)

def clean(value):
    """Normalize whitespace without altering Hindi or English wording."""
    value = str(value or "").replace("\x00", " ")
    value = re.sub(r"[\u200b\ufeff]", "", value)
    value = re.sub(r"\s+", " ", value)
    return value.strip()


def has_corrupt_text(value):
    """Flag common PDF/OCR encoding damage."""
    value = str(value or "")
    if any(mark in value for mark in ("�", "Ã", "Â", "â€", "\x00")):
        return True
    visible = [ch for ch in value if not ch.isspace()]
    return bool(visible and sum(not ch.isprintable() for ch in visible) / len(visible) > 0.02)


def valid_extracted_field(value, kind):
    """Reject noisy PDF extraction fragments instead of saving misleading facts."""
    value = clean(value)
    if not value:
        return None
    lowered = value.lower()
    bad_markers = ("page ", "table of contents", "advertisement no.")
    if has_corrupt_text(value) or any(marker in lowered for marker in bad_markers):
        return None
    if kind == "qualification":
        if len(value) < 18 or len(value) > 220:
            return None
        if re.search(r"\b(page|chapter|annexure|serial no)\b", lowered):
            return None
        if re.match(r"^(for the post|those who possess|as on)\b", lowered):
            return None
    elif kind == "fees":
        if len(value) < 5 or len(value) > 100 or re.match(r"^(पद\s*सं|post\s*no)\b", lowered):
            return None
    elif kind == "age":
        if len(value) < 8 or len(value) > 90 or re.match(r"^\(?as on\b", lowered):
            return None
    elif kind == "selection":
        if len(value) < 8 or len(value) > 120 or re.match(r"^(पद\s*सं|post\s*no)\b", lowered):
            return None
    return value

def host(url):
    return (urlparse(url).hostname or "").lower().rstrip(".")

def official(url):
    h = host(url)
    return (
        h in EXACT_HOSTS
        or h.endswith(".gov.in")
        or h.endswith(".nic.in")
        or h.endswith(".gov")
    )

def safe_url(raw, base):
    if not raw:
        return None
    url = urldefrag(urljoin(base, raw.strip()))[0]
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https") or not official(url):
        return None
    return url

def normalized_url(url):
    return urldefrag((url or "").strip())[0].rstrip("/").lower()

def make_session():
    session = requests.Session()
    session.headers.update(HEADERS)
    retry = Retry(
        total=3, connect=3, read=2, status=3,
        backoff_factor=1.0,
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=frozenset(["GET", "HEAD"]),
        respect_retry_after_header=True,
        raise_on_status=False,
    )
    adapter = HTTPAdapter(max_retries=retry, pool_connections=12, pool_maxsize=12)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    return session

def fetch(session, url, limit=MAX_HTML):
    try:
        response = session.get(url, timeout=TIMEOUT, allow_redirects=True, stream=True)
        if response.status_code >= 400:
            print("HTTP SKIP", response.status_code, url)
            response.close()
            return None, None, None
        if not official(response.url):
            print("REDIRECT BLOCKED", url, "=>", response.url)
            response.close()
            return None, None, None
        chunks = bytearray()
        for chunk in response.iter_content(65536):
            if chunk:
                chunks.extend(chunk)
                if len(chunks) > limit:
                    print("SIZE LIMIT", url)
                    response.close()
                    return None, None, None
        final_url = response.url
        content_type = (response.headers.get("Content-Type") or "").lower()
        response.close()
        return bytes(chunks), final_url, content_type
    except requests.exceptions.SSLError as exc:
        # TLS verification deliberately remains enabled. Do not weaken it to force a fetch.
        print("TLS ERROR (verification kept enabled)", url, str(exc)[:240])
    except requests.RequestException as exc:
        print("FETCH ERROR", url, str(exc)[:300])
    return None, None, None

def extract_pdf_text(session, url):
    data, final_url, content_type = fetch(session, url, MAX_PDF)
    if not data:
        return "", None
    if "pdf" not in content_type and not final_url.lower().split("?")[0].endswith(".pdf") and data[:4] != b"%PDF":
        return "", None
    try:
        reader = PdfReader(io.BytesIO(data))
        text = clean(" ".join(page.extract_text() or "" for page in reader.pages[:60]))
        return text, final_url
    except Exception as exc:
        print("PDF PARSE ERROR", url, str(exc)[:200])
        return "", final_url

def parse_date(value):
    value = clean(value).replace(",", " ")
    value = re.sub(r"(\d)(st|nd|rd|th)\b", r"\1", value, flags=re.I)
    value = re.sub(r"\s+", " ", value)
    formats = (
        "%d/%m/%Y", "%d-%m-%Y", "%d.%m.%Y",
        "%d/%m/%y", "%d-%m-%y", "%d.%m.%y",
        "%Y-%m-%d", "%Y/%m/%d",
        "%d %B %Y", "%d %b %Y", "%B %d %Y", "%b %d %Y",
        "%d-%B-%Y", "%d-%b-%Y",
    )
    for fmt in formats:
        try:
            return datetime.strptime(value, fmt).date().isoformat()
        except ValueError:
            continue
    return None

def labelled_date(text, labels):
    for label in labels:
        pattern = rf"(?:{label})\s*(?:is|:|-|–|to)?\s*{DATE_TOKEN}"
        match = re.search(pattern, text, flags=re.I)
        if match:
            parsed = parse_date(match.group(1))
            if parsed:
                return parsed
    return None

def extract_fields(text):
    vacancy = None
    patterns = (
        r"(?:total\s+(?:number\s+of\s+)?vacanc(?:y|ies)|total\s+posts?|"
        r"number\s+of\s+vacanc(?:y|ies)|no\.?\s*of\s*(?:vacanc(?:y|ies)|posts?)|"
        r"number\s+of\s+posts?|posts?\s+available|"
        r"vacant\s+posts?|total\s+vacant\s+posts?)"
        r"\s*[:\-]?\s*(\d[\d,]*)",
        r"(\d[\d,]*)\s+(?:vacancies|vacant posts|posts)\b",
    )
    for pattern in patterns:
        match = re.search(pattern, text, re.I)
        if match:
            number = int(match.group(1).replace(",", ""))
            if 0 < number < 1_000_000:
                vacancy = str(number)
                break

    last_date = labelled_date(text, (
        r"last\s+date(?:\s+for|\s+of)?\s+(?:(?:submission|receipt|apply|application)(?:\s+of)?\s*)?",
        r"closing\s+date(?:\s+for\s+(?:online\s+)?application)?",
        r"apply\s+online\s+up\s+to",
        r"applications?\s+may\s+be\s+submitted\s+up\s+to",
        r"last\s+date\s+to\s+apply",
        r"online\s+application\s+(?:ends?|closes?)",
        r"application\s+(?:closing|submission)\s+date",
        r"applications?\s+close(?:s)?\s+on",
        r"apply\s+before",
        r"due\s+date",
        r"closing\s+date\s+of\s+online\s+submission",
    ))
    notification_date = labelled_date(text, (
        r"date\s+of\s+notification", r"notification\s+date",
        r"date\s+of\s+advertisement", r"advertisement\s+date",
        r"published\s+on",
    ))
    qualification = re.search(
        r"(?:educational|essential|minimum|prescribed|eligibility)\s+"
        r"(?:qualification|criteria|requirements?)(?:s)?"
        r"\s*[:\-]?\s*(.{20,320}?)(?:\b(?:age limit|pay scale|salary|"
        r"application fee|selection process|how to apply|important dates|"
        r"number of vacancies|total posts?)\b)",
        text, re.I,
    )
    fee = re.search(r"(?:application fee|examination fee|exam fee|registration fee)\s*[:\-]?\s*([^\n.]{3,120})", text, re.I)
    age = re.search(r"(?:age limit|age criteria)\s*[:\-]?\s*([^\n.]{3,100})", text, re.I)
    selection = re.search(r"(?:selection process|mode of selection|selection procedure)\s*[:\-]?\s*([^\n.]{3,140})", text, re.I)
    return {
        "vacancies": vacancy,
        "last_date": last_date,
        "notification_date": notification_date,
        "qualification": valid_extracted_field(qualification.group(1), "qualification") if qualification else None,
        "fees": valid_extracted_field(fee.group(1), "fees") if fee else None,
        "age_limit": valid_extracted_field(age.group(1), "age") if age else None,
        "selection_process": valid_extracted_field(selection.group(1), "selection") if selection else None,
    }

def has_stale_notice_date(value, max_age_days=540):
    """Reject archive links when the oldest explicit notice date is clearly stale."""
    matches = re.findall(DATE_TOKEN, clean(value), flags=re.I)
    parsed = [parse_date(item) for item in matches]
    dates = [datetime.strptime(item, "%Y-%m-%d").date() for item in parsed if item]
    # Archive rows often contain both an old advertisement date and a later
    # result/update date. Using max() allowed those old notices through.
    return bool(dates and min(dates) < TODAY - timedelta(days=max_age_days))


def listing_notification_date(title):
    """Read a leading publication date from dated recruitment-list entries."""
    title = clean(title)
    match = re.match(rf"^\s*{DATE_TOKEN}", title, flags=re.I)
    return parse_date(match.group(1)) if match else None


def discover_links(html, page_url):
    soup = BeautifulSoup(html, "html.parser")
    found = []
    seen = set()
    for anchor in soup.select("a[href]"):
        label = clean(anchor.get_text(" ", strip=True))
        parent = anchor.find_parent(["tr", "li", "article"])
        context = clean(parent.get_text(" ", strip=True)) if parent else label
        title = context if len(context) > len(label) + 8 else label
        searchable = (title + " " + label).lower()
        if len(title) < 12 or len(title) > 420:
            continue
        # Ignore archive links with an explicitly old notice date.
        if has_stale_notice_date(title):
            continue
        if any(term in searchable for term in EXCLUDE_HINTS):
            continue
        if not any(term in searchable for term in RECRUITMENT_HINTS):
            continue
        url = safe_url(anchor.get("href"), page_url)
        if url and normalized_url(url) != normalized_url(page_url) and normalized_url(url) not in seen:
            seen.add(normalized_url(url))
            found.append((title[:240], url))
    return found


UP_OFFICIAL_HOSTS = {
    "upsssc.gov.in", "uppsc.up.nic.in", "uppbpb.gov.in", "upnrhm.gov.in",
    # Dedicated UP Police result portal linked from the official UPPRPB website.
    "upcons2025.com",
}
UP_RESULT_HINTS = (
    "result", "merit list", "merit-list", "score card", "scorecard",
    "final selection list", "selected candidates", "परिणाम", "रिजल्ट",
)
UP_ADMIT_HINTS = (
    "admit card", "admit-card", "hall ticket", "download admit",
    "प्रवेश पत्र", "प्रवेशपत्र",
)

def up_official(url):
    h = host(url)
    return h in UP_OFFICIAL_HOSTS or h.endswith(".up.gov.in") or h.endswith(".up.nic.in")

def discover_up_updates(html, page_url):
    soup = BeautifulSoup(html, "html.parser")
    found, seen = [], set()
    for anchor in soup.select("a[href]"):
        label = clean(anchor.get_text(" ", strip=True))
        parent = anchor.find_parent(["tr", "li", "article"])
        context = clean(parent.get_text(" ", strip=True)) if parent else label
        searchable = (context + " " + label).lower()
        category = None
        if any(term in searchable for term in UP_ADMIT_HINTS):
            category = "Admit Card"
        elif any(term in searchable for term in UP_RESULT_HINTS):
            category = "Result"
        if not category or has_stale_notice_date(context + " " + label):
            continue
        url = safe_url(anchor.get("href"), page_url)
        if not url or not up_official(url):
            continue
        key = normalized_url(url)
        if key == normalized_url(page_url) or key in seen:
            continue
        seen.add(key)
        generic_label = label.lower() in {"click here", "click to view", "click to download", "view", "download", "here", "result", "admit card"}
        # Keep row/list context even when the action anchor itself is generic.
        title = context if generic_label or len(label) < 12 or len(context) > len(label) + 18 else label
        title = clean(title)[:220]
        if len(title) >= 5:
            found.append((category, title, url))
    return found

def find_notice_pdf(session, html, page_url):
    """Choose the most relevant current recruitment PDF, not simply the longest PDF."""
    soup = BeautifulSoup(html, "html.parser")
    candidates, seen = [], set()
    for anchor in soup.select("a[href]"):
        label = clean(anchor.get_text(" ", strip=True)).lower()
        url = safe_url(anchor.get("href"), page_url)
        if not url or host(url) != host(page_url):
            continue
        is_pdf = ".pdf" in urlparse(url).path.lower()
        notice_link = any(word in label for word in ("notification", "advertisement", "detailed notice", "download notice"))
        if not (is_pdf or notice_link):
            continue
        key = normalized_url(url)
        if key in seen or any(word in (label + " " + url.lower()) for word in ("result", "answer key", "syllabus", "tender", "annual-report", "old")):
            continue
        seen.add(key)
        candidates.append((label, url))

    best = None
    for label, url in candidates[:16]:
        text, final_url = extract_pdf_text(session, url)
        if not text or not final_url or host(final_url) != host(page_url):
            continue
        fields = extract_fields(text)
        core = sum((
            bool(fields["last_date"] and fields["last_date"] >= TODAY.isoformat()),
            bool(fields["vacancies"]),
            bool(fields["qualification"]),
        ))
        lowered = (label + " " + text[:12000]).lower()
        relevance = sum(term in lowered for term in (
            "recruitment", "vacancy", "advertisement", "notification",
            "applications are invited", "apply online", "पदों पर भर्ती", "सीधी भर्ती",
        ))
        score = core * 100 + relevance * 8 + min(len(text), 12000) / 12000
        if best is None or score > best[0]:
            best = (score, text, final_url)
        if core == 3 and relevance >= 1:
            break
    return (best[1], best[2]) if best else ("", None)

def find_apply_url(session, html, page_url, notice_text):
    candidates = []
    if html:
        soup = BeautifulSoup(html, "html.parser")
        for anchor in soup.select("a[href]"):
            label = clean(anchor.get_text(" ", strip=True)).lower()
            url = safe_url(anchor.get("href"), page_url)
            if url and any(word in label for word in ("apply online", "online application", "registration", "apply now", "application portal")):
                candidates.append(url)
    for raw in re.findall(r"https?://[A-Za-z0-9._~:/?#\[\]@!$&'()*+,;=%-]+", notice_text):
        url = safe_url(raw.rstrip(".,;)"), page_url)
        if url and any(word in url.lower() for word in ("apply", "registration", "online", "ora", "recruit")):
            candidates.append(url)
    for url in dict.fromkeys(candidates):
        data, final_url, _ = fetch(session, url, 1024 * 1024)
        if data is not None and final_url and official(final_url):
            return final_url
    return None

def normalize_text(value):
    return re.sub(r"[^a-z0-9]+", " ", clean(value).lower()).strip()

def db_headers():
    return {
        "apikey": KEY,
        "Authorization": "Bearer " + KEY,
        "Content-Type": "application/json",
        "Prefer": "return=representation",
    }

def clean_public_sarkaritoday_text(value):
    """Remove third-party publisher branding/attribution from public-facing text."""
    text = str(value or "")
    kept = []
    for line in re.split(r"\\n|\r?\n", text):
        low = line.lower()
        if "sarkaritoday" in low or "sarkaritoday.com" in low:
            continue
        kept.append(line)
    text = "\n".join(kept)
    text = re.sub(r"(?i)\s*[-|–—:]?\s*sarkaritoday\s*$", "", text)
    return clean(text)


def clean_public_sarkaritoday_title(value):
    title = re.sub(r"(?i)sarkaritoday(?:\.com)?", "", str(value or ""))
    return clean(re.sub(r"\s*[-|–—:]\s*", " ", title)).strip(" -|–—:")


def cleanup_existing_sarkaritoday_rows(session):
    """Sanitize already-saved rows; preserve internal source_url for deduplication."""
    offset = 0
    scanned = changed = 0
    while True:
        response = session.get(
            DB + "/rest/v1/jobs",
            headers=db_headers(),
            params={"select": "id,title,description,notification_url,source_url", "limit": 500, "offset": offset},
            timeout=30,
        )
        response.raise_for_status()
        rows = response.json()
        for row in rows:
            scanned += 1
            patch = {}
            title = clean_public_sarkaritoday_title(row.get('title'))
            description = clean_public_sarkaritoday_text(row.get('description'))
            notification_url = row.get('notification_url') or ''
            if title != (row.get('title') or ''):
                patch['title'] = title
            if description != (row.get('description') or ''):
                patch['description'] = description
            if host(notification_url) in SARKARITODAY_HOSTS:
                patch['notification_url'] = ''
            # Keep source_url as an internal dedupe marker; it is never rendered publicly.
            if patch:
                update = session.patch(
                    DB + "/rest/v1/jobs",
                    headers={**db_headers(), "Prefer": "return=minimal"},
                    params={"id": "eq." + str(row["id"])},
                    json=patch,
                    timeout=30,
                )
                update.raise_for_status()
                changed += 1
        if len(rows) < 500:
            break
        offset += 500
    print("EXISTING THIRD-PARTY BRAND CLEANUP | scanned:", scanned, "| updated:", changed)
    return changed

def load_existing(session):
    known_urls, known_titles = set(), set()
    offset = 0
    while True:
        response = session.get(
            DB + "/rest/v1/jobs",
            headers=db_headers(),
            params={"select": "id,title,department,notification_url,source_url", "limit": 1000, "offset": offset},
            timeout=30,
        )
        response.raise_for_status()
        rows = response.json()
        for row in rows:
            for key in ("notification_url", "source_url"):
                if row.get(key):
                    known_urls.add(normalized_url(row[key]))
            known_titles.add((normalize_text(row.get("title")), normalize_text(row.get("department"))))
        if len(rows) < 1000:
            break
        offset += 1000
    return known_urls, known_titles


def contains_devanagari(value):
    """Detect Hindi/Devanagari text without translating or changing source wording."""
    return bool(re.search(r"[\u0900-\u097F]", value or ""))


def build_vacancy_description(title, department, vacancies, qualification, last_date, fees, age_limit, selection_process, pdf_verified, source_notice_text=''):
    """Write a readable article in the language used by the source notice."""
    facts = " ".join(str(x or "") for x in (title, qualification, fees, age_limit, selection_process, source_notice_text))
    hindi = contains_devanagari(facts)
    qualification = valid_extracted_field(qualification, "qualification") if qualification else None
    fees = valid_extracted_field(fees, "fees") if fees else None
    age_limit = valid_extracted_field(age_limit, "age") if age_limit else None
    selection_process = valid_extracted_field(selection_process, "selection") if selection_process else None

    if hindi:
        parts = [
            f"{title} के संबंध में {department} की आधिकारिक वेबसाइट पर भर्ती सूचना उपलब्ध है।",
            "इस लेख में वही जानकारी शामिल की गई है जो उपलब्ध आधिकारिक सूचना से स्पष्ट रूप से पढ़ी जा सकी है।"
        ]
        if vacancies:
            parts.append(f"इस भर्ती में कुल {vacancies} पद बताए गए हैं।")
        if qualification:
            parts.append(f"शैक्षणिक योग्यता: {qualification}")
        if age_limit:
            parts.append(f"आयु सीमा: {age_limit}")
        if fees:
            parts.append(f"आवेदन शुल्क: {fees}")
        if selection_process:
            parts.append(f"चयन प्रक्रिया: {selection_process}")
        if last_date:
            parts.append(f"आवेदन की अंतिम तिथि {last_date} है।")
        else:
            parts.append("आवेदन की अंतिम तिथि उपलब्ध पाठ से स्पष्ट नहीं हुई है। कृपया आधिकारिक अधिसूचना में इसकी पुष्टि करें।")
        parts.extend([
            "आवेदन करने से पहले आधिकारिक अधिसूचना ध्यान से पढ़ें और पद के अनुसार अपनी पात्रता जाँच लें।",
            ("इस भर्ती की जानकारी आधिकारिक अधिसूचना PDF से मिलान करके तैयार की गई है।" if pdf_verified else "यह जानकारी ड्राफ्ट में है; प्रकाशित करने से पहले मूल अधिसूचना से जाँच आवश्यक है।")
        ])
    else:
        parts = [
            f"{title} is listed on the official {department} recruitment portal.",
            "This article includes only details that could be clearly identified in the available official notice."
        ]
        if vacancies:
            parts.append(f"The notice lists {vacancies} vacancies.")
        if qualification:
            parts.append(f"Educational qualification: {qualification}")
        if age_limit:
            parts.append(f"Age limit: {age_limit}")
        if fees:
            parts.append(f"Application fee: {fees}")
        if selection_process:
            parts.append(f"Selection process: {selection_process}")
        if last_date:
            parts.append(f"The last date to apply is {last_date}.")
        else:
            parts.append("The application deadline could not be clearly extracted. Confirm it in the official notification.")
        parts.extend([
            "Read the official notification carefully and check your eligibility for the post before applying.",
            ("The recruitment details above were cross-checked against the readable official notification PDF." if pdf_verified else "This entry remains a Draft until its details are checked against the original notice.")
        ])
    return "\n\n".join(parts)



def seo_vacancy_title(title):
    """Keep official recruitment titles readable, concise and free of CTA clutter."""
    title = clean(title).strip(" |•:-")
    title = re.sub(r"\s+", " ", title)
    title = re.sub(r"^(click here|download|view details)[: -]*", "", title, flags=re.I)
    if len(title) < 12 or title.lower() in {"recruitment notification", "latest vacancy", "click here"}:
        return ""
    return title[:180]


def seo_update_title(title, category):
    """Make titles clear and search-friendly without keyword stuffing."""
    title = clean(title).strip(" |•:-")
    if title.lower() in {"click here", "view", "download", "click to view", "click to download", "here", "result notification", "admit card notification", "admit card", "result"} or len(title) < 12:
        return ""
    hindi = contains_devanagari(title)
    if category == "Admit Card":
        if not any(x in title.lower() for x in ("admit card", "hall ticket", "प्रवेश पत्र", "प्रवेशपत्र")):
            title += " " + ("प्रवेश पत्र" if hindi else "Admit Card")
    else:
        if not any(x in title.lower() for x in ("result", "परिणाम", "रिजल्ट", "merit list", "scorecard")):
            title += " " + ("परिणाम" if hindi else "Result")
    return re.sub(r"\s+", " ", title).strip()[:180]


def official_action_link(html, page_url, category):
    """Find a clearly labelled action link hosted on an approved UP government domain."""
    if not html:
        return None
    soup = BeautifulSoup(html, "html.parser")
    terms = (("admit card", "hall ticket", "download admit", "प्रवेश पत्र", "प्रवेशपत्र")
             if category == "Admit Card"
             else ("result", "merit list", "scorecard", "score card", "परिणाम", "रिजल्ट"))
    for anchor in soup.select("a[href]"):
        label = clean(anchor.get_text(" ", strip=True)).lower()
        parent = anchor.find_parent(["tr", "li", "article", "div"])
        context = clean(parent.get_text(" ", strip=True)).lower() if parent else label
        searchable = label + " " + context
        href = safe_url(anchor.get("href"), page_url)
        # The surrounding row can identify the action when the button only says
        # "Download" or "Click here"; the destination must still be on an UP host.
        has_category = any(term in searchable for term in terms)
        has_action = any(term in searchable for term in (
            "download", "view", "check", "result", "admit", "hall ticket",
            "प्रवेश", "परिणाम", "रिजल्ट", "प्रकाशन", "जारी",
        ))
        if href and up_official(href) and has_category and has_action:
            return href
    return None



def verified_up_action_link(html, page_url, category, detail_text):
    """Return a verified action URL, including the board-linked UP Police result landing page."""
    action_url = official_action_link(html, page_url, category)
    if (not action_url and category == "Result"
            and host(page_url) == "upcons2025.com"
            and any(term in (detail_text or "").lower() for term in ("final result", "परिणाम"))
            and any(term in (detail_text or "").lower() for term in ("click here", "view list", "merit"))):
        return page_url
    return action_url

def build_up_update_description(title, department, category, action_url, exam_date=None, release_date=None, result_date=None, merit_url=None, source_text=""):
    """Write a clean, useful article in the language of the official source."""
    hindi = contains_devanagari(title + " " + source_text)
    parts = []
    if hindi and category == "Admit Card":
        parts = [f"{title} का प्रवेश पत्र {department} की आधिकारिक वेबसाइट पर उपलब्ध है।",
                 "आधिकारिक डाउनलोड लिंक खोलें और प्रवेश पत्र डाउनलोड करने से पहले अपना परीक्षा/भर्ती विवरण मिलान करें।"]
        if exam_date: parts.append(f"परीक्षा की तिथि: {exam_date}")
        if release_date: parts.append(f"प्रवेश पत्र जारी होने की तिथि: {release_date}")
        parts.append("डाउनलोड के बाद परीक्षा केंद्र, रिपोर्टिंग समय और प्रवेश पत्र पर दिए गए निर्देश ध्यान से पढ़ें।")
    elif hindi:
        parts = [f"{title} का परिणाम {department} की आधिकारिक वेबसाइट पर जारी किया गया है।",
                 "आधिकारिक परिणाम लिंक खोलें और मांगी गई जानकारी भरकर अपना परिणाम देखें।"]
        if result_date: parts.append(f"परिणाम जारी होने की तिथि: {result_date}")
        if merit_url: parts.append("आधिकारिक मेरिट सूची/चयन सूची का लिंक भी उपलब्ध है।")
        parts.append("परिणाम में अपना नाम, रोल नंबर और दिए गए निर्देशों का मिलान अवश्य करें।")
    elif category == "Admit Card":
        parts = [f"{title} is available on the official {department} website.",
                 "Open the official download link and match your exam/recruitment details before downloading."]
        if exam_date: parts.append(f"Exam date: {exam_date}")
        if release_date: parts.append(f"Admit card release date: {release_date}")
        parts.append("After downloading, check the exam centre, reporting time and instructions.")
    else:
        parts = [f"{title} has been published on the official {department} website.",
                 "Open the official result link and enter the required details to check your result."]
        if result_date: parts.append(f"Result date: {result_date}")
        if merit_url: parts.append("An official merit/selection-list link is also available.")
        parts.append("Check your name, roll number and all instructions shown with the result.")
    parts.append(f"Official {('admit card download' if category == 'Admit Card' else 'result check')} link: {action_url}")
    return "\n\n".join(parts)

SARKARITODAY_LISTING = "https://sarkaritoday.com/latest-job/"
SARKARITODAY_HOSTS = {"sarkaritoday.com", "www.sarkaritoday.com"}

def fetch_sarkaritoday(session, url, limit=MAX_HTML):
    """Fetch discovery-only pages; never treat this publisher as official."""
    try:
        response = session.get(url, timeout=TIMEOUT, allow_redirects=True, stream=True)
        final_url = response.url
        if response.status_code >= 400 or host(final_url) not in SARKARITODAY_HOSTS:
            print("SARKARITODAY HTTP/REDIRECT SKIP", response.status_code, url, "=>", final_url)
            response.close()
            return None, None, None
        chunks = bytearray()
        for chunk in response.iter_content(65536):
            if chunk:
                chunks.extend(chunk)
                if len(chunks) > limit:
                    response.close()
                    return None, None, None
        content_type = (response.headers.get("Content-Type") or "").lower()
        response.close()
        return bytes(chunks), final_url, content_type
    except requests.RequestException as exc:
        print("SARKARITODAY FETCH ERROR", url, str(exc)[:240])
        return None, None, None


def discover_sarkaritoday_articles(html, page_url):
    if host(page_url) not in SARKARITODAY_HOSTS:
        return []
    soup = BeautifulSoup(html, "html.parser")
    found, seen = [], set()
    for anchor in soup.select("a[href]"):
        url = urldefrag(urljoin(page_url, anchor.get("href", "")))[0]
        if urlparse(url).scheme not in ("http", "https") or host(url) not in SARKARITODAY_HOSTS:
            continue
        path = urlparse(url).path.lower().rstrip("/")
        if not path or path in ("/", "/latest-job", "/latestjob") or any(
            part in path for part in ("/category/", "/tag/", "/page/", "/wp-content/", "/author/")
        ):
            continue
        title = clean(anchor.get_text(" ", strip=True))
        if len(title) < 12 or len(title) > 220:
            continue
        searchable = title.lower()
        if any(term in searchable for term in EXCLUDE_HINTS):
            continue
        if not any(term in searchable for term in RECRUITMENT_HINTS + ("bharti", "भर्ती", "job")):
            continue
        key = normalized_url(url)
        if key not in seen:
            seen.add(key)
            found.append((title[:180], url))
    return found[:80]


def extract_sarkaritoday_article(html, article_url):
    """Read the complete article: tables, headings, paragraphs and official links."""
    soup = BeautifulSoup(html, "html.parser")
    for node in soup.select("script,style,noscript,header,footer,nav"):
        node.decompose()
    heading = soup.find(["h1", "h2"])
    title = clean(heading.get_text(" ", strip=True)) if heading else ""
    if len(title) < 10:
        title = clean(soup.title.get_text(" ", strip=True)) if soup.title else ""
        title = re.sub(r"\s*[-|].*$", "", title).strip()

    rows = {}
    for table in soup.find_all("table"):
        for tr in table.find_all("tr"):
            cells = [clean(cell.get_text(" ", strip=True)) for cell in tr.find_all(["th", "td"])]
            cells = [cell for cell in cells if cell]
            if len(cells) >= 2:
                label = re.sub(r"[^a-z0-9\u0900-\u097f]+", " ", cells[0].lower()).strip()
                value = clean(" ".join(cells[1:]))
                if label and value:
                    rows[label] = value

    # Include article paragraphs and headings as labelled facts, not only table cells.
    for node in soup.select("p, li, h2, h3, h4, strong, b"):
        line = clean(node.get_text(" ", strip=True))
        if len(line) < 4 or len(line) > 700:
            continue
        match = re.match(r"^([^:：|]{2,65})\s*[:：|]\s*(.{2,})$", line)
        if match:
            label = re.sub(r"[^a-z0-9\u0900-\u097f]+", " ", match.group(1).lower()).strip()
            rows.setdefault(label, clean(match.group(2)))

    full_text = clean(soup.get_text(" ", strip=True))

    def pick(*labels):
        for label, value in rows.items():
            if any(token in label for token in labels):
                return value
        return None

    vacancy_raw = pick("total vacancy", "total post", "number of vacancy", "no of vacancy", "vacancies", "total seats", "रिक्त पद", "कुल पद")
    vacancy_match = re.search(r"\b(\d[\d,]*)\b", vacancy_raw or "")
    vacancies = vacancy_match.group(1).replace(",", "") if vacancy_match else None

    def table_date(raw):
        if not raw:
            return None
        match = re.search(DATE_TOKEN, raw, re.I)
        return parse_date(match.group(1)) if match else parse_date(raw)

    fallback = extract_fields(full_text)
    last_date = table_date(pick("last date", "closing date", "apply last", "application end", "अंतिम तिथि", "आवेदन की अंतिम")) or fallback.get("last_date")
    notification_date = table_date(pick("notification date", "published date", "start date", "application start", "आवेदन शुरू", "प्रकाशित")) or fallback.get("notification_date")
    qualification = pick("qualification", "educational qualification", "eligibility", "शैक्षणिक योग्यता", "योग्यता") or fallback.get("qualification")
    age_limit = pick("age limit", "age criteria", "आयु सीमा") or fallback.get("age_limit")
    fees = pick("application fee", "exam fee", "registration fee", "आवेदन शुल्क", "परीक्षा शुल्क") or fallback.get("fees")
    selection = pick("selection process", "mode of selection", "चयन प्रक्रिया") or fallback.get("selection_process")
    department = pick("department", "organization", "organisation", "board", "authority", "विभाग", "संस्था", "बोर्ड")

    apply_url = None
    notification_url = None
    for a in soup.select("a[href]"):
        raw = safe_url(a.get("href", ""), article_url)
        if not raw:
            continue
        label = clean(a.get_text(" ", strip=True)).lower()
        path = urlparse(raw).path.lower()
        is_pdf = path.endswith(".pdf") or ".pdf/" in path or "pdf" in label
        is_apply = any(term in label for term in (
            "apply online", "online application", "registration", "apply now",
            "application portal", "click here to apply", "आवेदन करें", "ऑनलाइन आवेदन",
        )) or any(term in raw.lower() for term in ("apply", "registration", "recruitmentportal"))
        if is_pdf and official(raw) and not notification_url:
            notification_url = raw
        if is_apply and official(raw) and not apply_url:
            apply_url = raw

    return {
        "title": seo_vacancy_title(title),
        "department": clean(department) if department else None,
        "vacancies": vacancies or fallback.get("vacancies"),
        "last_date": last_date,
        "notification_date": notification_date,
        "qualification": clean(qualification) if qualification else None,
        "age_limit": clean(age_limit) if age_limit else None,
        "fees": clean(fees) if fees else None,
        "selection_process": clean(selection) if selection else None,
        "apply_url": apply_url,
        "official_url": notification_url,
        "article_text": full_text,
    }


def verify_sarkaritoday_official_pdf(article_fields, pdf_text, pdf_url):
    """Verify third-party-discovered facts against a readable official PDF."""
    if not pdf_url or not official(pdf_url) or len(clean(pdf_text)) < 300 or has_corrupt_text(pdf_text):
        return False, {}
    official_fields = extract_fields(clean(pdf_text))
    if not (
        article_fields.get("vacancies")
        and official_fields.get("vacancies") == article_fields.get("vacancies")
        and article_fields.get("last_date")
        and official_fields.get("last_date") == article_fields.get("last_date")
        and article_fields.get("qualification")
        and official_fields.get("qualification")
    ):
        return False, official_fields

    def tokens(value):
        return {
            token for token in re.findall(r"[a-z0-9\u0900-\u097f]+", clean(value).lower())
            if len(token) > 1
        }

    department_tokens = tokens(article_fields.get("department") or "")
    pdf_tokens = tokens(pdf_text)
    if not department_tokens or len(department_tokens & pdf_tokens) / len(department_tokens) < 0.5:
        return False, official_fields

    article_tokens = tokens(article_fields["qualification"])
    official_tokens = tokens(official_fields["qualification"])
    if not article_tokens or not official_tokens:
        return False, official_fields
    overlap = len(article_tokens & official_tokens) / len(article_tokens | official_tokens)
    return overlap >= 0.45, official_fields


def build_sarkaritoday_draft_description(title, fields, source_url=None):
    """Build a clean, useful Hindi job article using only extracted/verified facts."""
    parts = [
        f"{title}",
        f"{title} भर्ती से जुड़ी महत्वपूर्ण जानकारी नीचे दी गई है। आवेदन करने से पहले उम्मीदवार आधिकारिक अधिसूचना ध्यान से पढ़ें और अपनी पात्रता की पुष्टि करें।",
    ]

    details = []
    labels = (
        ("department", "भर्ती विभाग"),
        ("vacancies", "कुल पद"),
        ("qualification", "शैक्षणिक योग्यता"),
        ("age_limit", "आयु सीमा"),
        ("fees", "आवेदन शुल्क"),
        ("selection_process", "चयन प्रक्रिया"),
        ("notification_date", "नोटिफिकेशन / आवेदन प्रारंभ तिथि"),
        ("last_date", "आवेदन की अंतिम तिथि"),
    )
    for key, label in labels:
        value = clean(fields.get(key) or "")
        if value:
            details.append(f"{label}: {value}")
    if details:
        parts.extend(["महत्वपूर्ण भर्ती विवरण", *details])

    if fields.get("apply_url"):
        parts.extend([
            "आवेदन कैसे करें",
            "आवेदन करने के लिए ऊपर दिए गए आधिकारिक Apply Online लिंक का उपयोग करें। फॉर्म भरने से पहले सभी निर्देश पढ़ें, सही जानकारी दर्ज करें और सबमिट करने से पहले विवरण जाँच लें।",
        ])
    else:
        parts.append("आवेदन प्रक्रिया और उपलब्ध विकल्पों की जानकारी के लिए आधिकारिक अधिसूचना देखें।")

    if fields.get("official_url"):
        parts.append("उम्मीदवार आवेदन से पहले ऊपर दिए गए आधिकारिक नोटिफिकेशन PDF को जरूर पढ़ें।")
    parts.append("ध्यान दें: आयु में छूट, पद-वार योग्यता, शुल्क और अन्य शर्तें संबंधित विभाग की आधिकारिक अधिसूचना के अनुसार लागू होंगी।")
    parts.append("सरकारी नौकरी की ताज़ा और उपयोगी जानकारी के लिए SarkariJobAlert पर विज़िट करें: https://sarkari-jobalert.com")
    return "\\n\\n".join(parts)


def main():
    if not DB.startswith("https://") or not KEY:
        print("CONFIG ERROR: GitHub secrets SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY are required.")
        return 2

    session = make_session()
    try:
        cleanup_existing_sarkaritoday_rows(session)
        known_urls, known_titles = load_existing(session)
    except Exception as exc:
        print("SUPABASE READ ERROR:", str(exc)[:300])
        return 2

    candidates = []
    up_update_candidates = []
    sarkaritoday_candidates = []
    seen_up_updates = set()
    seen_links = set()
    seen_sarkaritoday = set()
    source_errors = 0
    print("SCAN DATE (Asia/Kolkata):", TODAY.isoformat())
    print("SOURCE ORDER: Uttar Pradesh first, then central/national portals; SarkariToday is discovery-only.")
    for source_name, source_url in SOURCES:
        print("CHECK", source_name, source_url)
        data, final_url, content_type = fetch(session, source_url)
        if not data or "pdf" in (content_type or ""):
            source_errors += 1
            continue
        try:
            for title, link in discover_links(data, final_url):
                key = normalized_url(link)
                if key not in known_urls and key not in seen_links:
                    seen_links.add(key)
                    candidates.append((source_name, title, link))
            if source_name in {name for name, _ in UP_SOURCES}:
                for category, title, link in discover_up_updates(data, final_url):
                    key = normalized_url(link)
                    if key not in known_urls and key not in seen_up_updates:
                        seen_up_updates.add(key)
                        up_update_candidates.append((source_name, category, title, link))
        except Exception as exc:
            source_errors += 1
            print("SOURCE PARSE ERROR", source_name, str(exc)[:200])
        time.sleep(0.2)

    # SarkariToday is discovery-only and is never added to official().
    print("CHECK SarkariToday discovery", SARKARITODAY_LISTING)
    listing_data, listing_url, _ = fetch_sarkaritoday(session, SARKARITODAY_LISTING)
    if listing_data:
        try:
            for candidate_title, article_url in discover_sarkaritoday_articles(listing_data, listing_url):
                key = normalized_url(article_url)
                if key not in known_urls and key not in seen_sarkaritoday:
                    seen_sarkaritoday.add(key)
                    sarkaritoday_candidates.append((candidate_title, article_url))
        except Exception as exc:
            source_errors += 1
            print("SARKARITODAY LIST PARSE ERROR", str(exc)[:220])
    else:
        source_errors += 1

    saved = drafts = published = skipped = duplicates = process_errors = 0
    for source_name, candidate_title, link in candidates:
        try:
            if any(word in candidate_title.lower() for word in EXCLUDE_HINTS):
                skipped += 1
                continue
            data, detail_url, content_type = fetch(session, link)
            if not data:
                skipped += 1
                continue

            page_is_pdf = "pdf" in (content_type or "") or data[:4] == b"%PDF"
            if page_is_pdf:
                # The PDF bytes were already downloaded by fetch(). Parse those
                # same verified bytes rather than requesting the URL a second time.
                # A second request can time out or return a different response.
                try:
                    pdf_reader = PdfReader(io.BytesIO(data))
                    pdf_text = clean(" ".join(page.extract_text() or "" for page in pdf_reader.pages[:60]))
                    pdf_url = detail_url
                except Exception as exc:
                    print("PDF PARSE ERROR", detail_url, str(exc)[:200])
                    pdf_text, pdf_url = "", None
                html = None
                page_text = ""
            else:
                html = data
                soup = BeautifulSoup(data, "html.parser")
                page_text = clean(soup.get_text(" ", strip=True))
                pdf_text, pdf_url = find_notice_pdf(session, data, detail_url)
            # Page context can help prepare a draft, but auto-publishing is
            # decided only from substantive text extracted from the official PDF.
            notice_text = clean(page_text + " " + pdf_text)

            if len(notice_text) < 180:
                print("SKIP - notice text too short:", candidate_title)
                skipped += 1
                continue

            combined = (candidate_title + " " + notice_text).lower()
            if any(word in candidate_title.lower() for word in EXCLUDE_HINTS):
                skipped += 1
                continue
            if not any(word in combined for word in RECRUITMENT_HINTS):
                print("SKIP - no clear recruitment wording:", candidate_title)
                skipped += 1
                continue

            fields = extract_fields(notice_text)
            # Employment News and other official bulletin pages often prefix
            # each listing with its publication date. Preserve it as a
            # notification date for an admin-review draft, never as a deadline.
            if not fields["notification_date"]:
                listing_date = listing_notification_date(candidate_title)
                # A future date in a listing title may be an application/event
                # date rather than its publication date; do not mislabel it.
                if listing_date and listing_date <= TODAY.isoformat():
                    fields["notification_date"] = listing_date
            missing = []
            if not official(detail_url):
                missing.append("official notice URL")
            if not fields["last_date"]:
                missing.append("application last date not found")
            elif fields["last_date"] < TODAY.isoformat():
                missing.append("application deadline already passed")
            if len(clean(candidate_title)) < 12:
                missing.append("clear recruitment title")

            # A recruitment is never saved, even as Draft, unless its application
            # last date is explicitly extracted and still valid. Other facts may
            # remain incomplete for admin review, but deadline is mandatory.
            core_facts = sum((
                bool(fields["last_date"] and fields["last_date"] >= TODAY.isoformat()),
                bool(fields["vacancies"]),
                bool(fields["qualification"]),
            ))
            dated_official_bulletin = bool(
                fields["notification_date"] and fields["notification_date"] <= TODAY.isoformat()
            )
            if core_facts < 1 and not dated_official_bulletin:
                missing.append("no confirmed core fact or dated official bulletin: future deadline, vacancy count, qualification")
            if missing:
                print("SKIP - insufficient verified recruitment evidence:", ", ".join(dict.fromkeys(missing)), "|", candidate_title[:180])
                skipped += 1
                continue

            # Strict vacancy auto-publish gate: the readable PDF must be hosted
            # on the same official host and confirm all three core facts.
            title = seo_vacancy_title(candidate_title)
            if not title or has_corrupt_text(title):
                print("SKIP - unclear or corrupted recruitment title:", candidate_title[:160])
                skipped += 1
                continue
            pdf_is_publishable = bool(
                pdf_url and official(pdf_url) and host(pdf_url) == host(detail_url)
                and len(pdf_text) >= 300 and not has_corrupt_text(pdf_text)
                and fields["last_date"] and fields["last_date"] >= TODAY.isoformat()
                and fields["vacancies"] and fields["qualification"] and core_facts == 3
                and not has_corrupt_text(title)
            )
            notification_url = pdf_url or detail_url
            department = source_name
            if " | " in title:
                department = clean(title.split(" | ", 1)[0])[:120] or source_name
            title_key = (normalize_text(title), normalize_text(department))
            if normalized_url(notification_url) in known_urls or normalized_url(detail_url) in known_urls or title_key in known_titles:
                duplicates += 1
                continue

            apply_url = find_apply_url(session, html, detail_url, notice_text) if html else None
            record = {
                "title": title,
                "department": department,
                "category": "Latest Jobs",
                "vacancies": fields["vacancies"] or "",
                "notification_date": fields["notification_date"],
                "last_date": fields["last_date"],
                "qualification": fields["qualification"] or "",
                "fees": fields["fees"] or "",
                "age_limit": fields["age_limit"] or "",
                "selection_process": fields["selection_process"] or "",
                "notification_url": notification_url,
                "apply_url": apply_url or "",
                "source_url": detail_url + MARKER,
                "description": build_vacancy_description(
                    title=title,
                    department=department,
                    vacancies=fields["vacancies"],
                    qualification=fields["qualification"],
                    last_date=fields["last_date"],
                    fees=fields["fees"],
                    age_limit=fields["age_limit"],
                    selection_process=fields["selection_process"],
                    pdf_verified=pdf_is_publishable,
                    source_notice_text=notice_text,
                ),
                "status": "draft",  # Human editor must add original value before public publication.
            }
            response = session.post(
                DB + "/rest/v1/jobs",
                headers=db_headers(),
                json=record,
                timeout=30,
            )
            response.raise_for_status()
            known_urls.update((normalized_url(notification_url), normalized_url(detail_url)))
            known_titles.add(title_key)
            saved += 1
            drafts += 1
            optional_missing = [
                key for key in ("vacancies", "qualification", "fees", "age_limit", "selection_process")
                if not fields.get(key)
            ]
            print(
                "DRAFT SAVED FOR EDITORIAL REVIEW:",
                title,
                "| PDF verified:", "yes" if pdf_is_publishable else "no",
                "| confirmed core facts:", core_facts, "/3",
                "| optional fields not extracted:", ", ".join(optional_missing) or "none"
            )
        except Exception as exc:
            process_errors += 1
            print("PROCESS ERROR:", candidate_title[:160], str(exc)[:280])
        time.sleep(0.2)


    # Read the full discovery article, enrich missing department from the official notice,
    # and apply the user's explicit skip/draft/publish rules.
    sarkaritoday_saved = sarkaritoday_skipped = sarkaritoday_duplicates = 0
    for candidate_title, article_url in sarkaritoday_candidates:
        try:
            data, detail_url, _ = fetch_sarkaritoday(session, article_url)
            if not data or not detail_url:
                sarkaritoday_skipped += 1
                continue
            fields = extract_sarkaritoday_article(data, detail_url)
            title = clean_public_sarkaritoday_title(fields.get("title") or seo_vacancy_title(candidate_title))
            if not title or has_corrupt_text(title) or "sarkaritoday" in title.lower():
                sarkaritoday_skipped += 1
                continue

            notification_url = fields.get("official_url") or ""
            apply_url = fields.get("apply_url") or ""
            # Search the complete article for an official application link if button labels vary.
            if not apply_url:
                apply_url = find_apply_url(session, data, detail_url, fields.get("article_text") or "")
            if not notification_url and not apply_url:
                print("SARKARITODAY SKIP - no official PDF or apply link:", title)
                sarkaritoday_skipped += 1
                continue

            last_date = fields.get("last_date")
            if not last_date or last_date < TODAY.isoformat():
                print("SARKARITODAY SKIP - missing/expired last date:", title)
                sarkaritoday_skipped += 1
                continue

            pdf_text = ""
            verified_pdf_url = None
            if notification_url:
                pdf_text, verified_pdf_url = extract_pdf_text(session, notification_url)

            # Department may be named in the official PDF even when the article omits it.
            department = fields.get("department")
            if not department and pdf_text:
                candidates_dept = []
                for line in pdf_text.splitlines():
                    line = clean(line)
                    if (8 <= len(line) <= 150 and
                            (re.search(r"\b(ministry|department|board|commission|railway|university|corporation|authority|विभाग|आयोग|बोर्ड|विश्वविद्यालय)\b", line, re.I)
                             or (line.isupper() and len(line.split()) >= 2))):
                        candidates_dept.append(line)
                if candidates_dept:
                    department = candidates_dept[0]
            if not department:
                # Use a named recruiting organisation from the article title only when explicit.
                m = re.match(r"^(.{3,80}?)\s+(?:recruitment|vacancy|bharti|apprentice)", title, re.I)
                if m:
                    department = clean(m.group(1))

            # Fill missing article values from readable official PDF text.
            if pdf_text:
                pdf_fields = extract_fields(pdf_text)
                for key in ("vacancies", "last_date", "notification_date", "qualification", "age_limit", "fees", "selection_process"):
                    if not fields.get(key) and pdf_fields.get(key):
                        fields[key] = pdf_fields[key]
            last_date = fields.get("last_date")
            if not last_date or last_date < TODAY.isoformat():
                print("SARKARITODAY SKIP - official/article last date missing or expired:", title)
                sarkaritoday_skipped += 1
                continue
            fields["department"] = department
            pdf_verified, official_fields = verify_sarkaritoday_official_pdf(fields, pdf_text, verified_pdf_url) if pdf_text and verified_pdf_url else (False, {})
            if not department:
                print("SARKARITODAY SKIP - department could not be identified:", title)
                sarkaritoday_skipped += 1
                continue
            if not fields.get("vacancies") or not fields.get("qualification"):
                print("SARKARITODAY SKIP - core admin details incomplete:", title)
                sarkaritoday_skipped += 1
                continue

            title_key = (normalize_text(title), normalize_text(department))
            if (normalized_url(detail_url) in known_urls
                    or (verified_pdf_url and normalized_url(verified_pdf_url) in known_urls)
                    or title_key in known_titles):
                sarkaritoday_duplicates += 1
                continue

            # Publish only if the official PDF is readable and verifies the key facts.
            # An official apply URL alone is enough for a draft, never automatic publishing.
            status = "draft"  # Discovery-source content requires human editorial review.
            fields["last_date"] = last_date
            fields["department"] = department
            fields["official_url"] = verified_pdf_url or ""
            fields["apply_url"] = apply_url
            record = {
                "title": title,
                "department": department,
                "category": "Latest Jobs",
                "vacancies": fields.get("vacancies") or "",
                "notification_date": fields.get("notification_date"),
                "last_date": last_date,
                "qualification": fields.get("qualification") or "",
                "fees": fields.get("fees") or "",
                "age_limit": fields.get("age_limit") or "",
                "selection_process": fields.get("selection_process") or "",
                "notification_url": verified_pdf_url or "",
                "apply_url": apply_url,
                "source_url": detail_url + MARKER,
                "description": build_sarkaritoday_draft_description(title, fields),
                "status": status,
            }
            response = session.post(DB + "/rest/v1/jobs", headers=db_headers(), json=record, timeout=30)
            response.raise_for_status()
            known_urls.add(normalized_url(detail_url))
            if verified_pdf_url:
                known_urls.add(normalized_url(verified_pdf_url))
            known_titles.add(title_key)
            sarkaritoday_saved += 1
            drafts += 1
            saved += 1
            print(
                "SARKARITODAY", status.upper(), "SAVED:", title,
                "| department:", department,
                "| PDF verified:", "yes" if pdf_verified else "no",
                "| apply link:", "yes" if apply_url else "no",
                "| deadline:", last_date,
            )
        except Exception as exc:
            process_errors += 1
            print("SARKARITODAY ARTICLE PROCESS ERROR:", candidate_title[:140], str(exc)[:240])
        time.sleep(0.2)

    # UP Admit Card + Result updates: official UP portal verification only.
    # No PDF, vacancy-count, qualification, or application-deadline requirement.
    up_updates_saved = up_updates_duplicates = up_updates_skipped = 0
    for source_name, category, candidate_title, link in up_update_candidates:
        try:
            data, detail_url, content_type = fetch(session, link)
            if not data or not detail_url or not up_official(detail_url):
                up_updates_skipped += 1
                print("UP UPDATE SKIP - official UP detail page unavailable:", candidate_title[:160])
                continue
            is_pdf_page = "pdf" in (content_type or "") or data[:4] == b"%PDF"
            if is_pdf_page:
                # Reuse the fetched PDF bytes; never turn an unreadable PDF into
                # a published update merely because its URL looks official.
                try:
                    pdf_reader = PdfReader(io.BytesIO(data))
                    detail_text = clean(" ".join(page.extract_text() or "" for page in pdf_reader.pages[:60]))
                    action_url = detail_url if detail_text and up_official(detail_url) else None
                except Exception as exc:
                    print("UP PDF PARSE ERROR", detail_url, str(exc)[:200])
                    detail_text, action_url = "", None
                html_soup = None
            else:
                html_soup = BeautifulSoup(data, "html.parser")
                detail_text = clean(html_soup.get_text(" ", strip=True))
                action_url = verified_up_action_link(data, detail_url, category, detail_text)
            lowered = (candidate_title + " " + detail_text).lower()
            hints = UP_ADMIT_HINTS if category == "Admit Card" else UP_RESULT_HINTS
            release_hints = (
                "available", "released", "download", "declared", "published",
                "now live", "check result", "view result", "final result",
                "final selection result", "प्रवेश पत्र डाउनलोड",
                "परिणाम जारी", "जारी किया", "उपलब्ध",
            )
            if (not any(term in lowered for term in hints) or len(detail_text) < 100
                    or not any(term in lowered for term in release_hints)
                    or has_corrupt_text(detail_text) or not action_url or not up_official(action_url)):
                up_updates_skipped += 1
                print("UP UPDATE SKIP - official category/action link not sufficiently verified:", candidate_title[:160])
                continue
            title = seo_update_title(candidate_title, category)
            if not title:
                up_updates_skipped += 1
                print("UP UPDATE SKIP - unclear SEO title:", candidate_title[:160])
                continue
            department = source_name
            title_key = (normalize_text(title), normalize_text(department))
            if normalized_url(detail_url) in known_urls or title_key in known_titles:
                up_updates_duplicates += 1
                continue
            record = {
                "title": title,
                "department": department,
                "category": category,
                "notification_url": detail_url,
                "description": build_up_update_description(
                    title, department, category, action_url,
                    exam_date=labelled_date(detail_text, (r"exam(?:ination)\s+date", r"date\s+of\s+exam")),
                    release_date=labelled_date(detail_text, (r"admit\s+card\s+(?:available|released|download)", r"release\s+date")),
                    result_date=labelled_date(detail_text, (r"result\s+(?:declared|published|date)", r"date\s+of\s+result")),
                    merit_url=action_url if category == "Result" and any(x in lowered for x in ("merit list", "merit-list", "selection list")) else None,
                    source_text=detail_text,
                ),
                "status": "draft",  # Official update is saved for human review before publication.
                "source_url": detail_url + MARKER,
            }
            if category == "Admit Card":
                record["admit_card_url"] = action_url
                record["exam_date"] = labelled_date(detail_text, (r"exam(?:ination)?\s+date", r"date\s+of\s+exam"))
                record["admit_card_release_date"] = labelled_date(detail_text, (r"admit\s+card\s+(?:available|released|download)", r"release\s+date"))
            else:
                record["result_url"] = action_url
                record["result_date"] = labelled_date(detail_text, (r"result\s+(?:declared|published|date)", r"date\s+of\s+result"))
                record["result_status"] = "परिणाम जारी" if contains_devanagari(detail_text) else "Declared"
                record["merit_list_url"] = action_url if any(x in lowered for x in ("merit list", "merit-list", "selection list")) else None
            response = session.post(DB + "/rest/v1/jobs", headers=db_headers(), json=record, timeout=30)
            response.raise_for_status()
            known_urls.add(normalized_url(detail_url))
            known_titles.add(title_key)
            up_updates_saved += 1
            print("UP UPDATE SAVED FOR EDITORIAL REVIEW:", category, title, "| official action:", action_url, "| source:", source_name)
        except Exception as exc:
            process_errors += 1
            print("UP UPDATE PROCESS ERROR:", candidate_title[:160], str(exc)[:260])
        time.sleep(0.2)

    print(
        "\nSCAN REPORT | date:", TODAY.isoformat(),
        "| official source pages:", len(SOURCES),
        "| source fetch/parse issues:", source_errors,
        "| candidate links:", len(candidates),
        "| SarkariToday discovery candidates:", len(sarkaritoday_candidates),
        "| SarkariToday drafts saved:", sarkaritoday_saved,
        "| SarkariToday skipped:", sarkaritoday_skipped,
        "| SarkariToday duplicates:", sarkaritoday_duplicates,
        "| rows saved:", saved,
        "| drafts saved:", drafts,
        "| skipped:", skipped,
        "| duplicates:", duplicates,
        "| processing errors:", process_errors,
        "| vacancy auto-published:", published, "(human review required; expected 0)",
        "| UP admit/result candidates:", len(up_update_candidates),
        "| UP admit/result saved for editorial review:", up_updates_saved,
        "| UP admit/result skipped (not verified/duplicate/fetch issue):", up_updates_skipped + up_updates_duplicates,
        "| all automatically discovered public posts remain Draft pending human editorial review",
    )
    return 1 if process_errors else 0

if __name__ == "__main__":
    sys.exit(main())
