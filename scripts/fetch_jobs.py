#!/usr/bin/env python3
"""Conservative, retry-aware official recruitment scanner for SarkariJobAlert.

Safety policy:
- Reads only official government recruitment portals.
- Never disables TLS certificate verification.
- Requires a clear recruitment notice and an explicit future last date.
- PDF is optional; an official HTML notice is acceptable.
- Saves verified candidates as DRAFT for human review. It never auto-publishes.
- Inserts new rows only; never edits existing jobs or changes the database schema.
"""
import io
import os
import re
import sys
import time
from datetime import datetime
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
    "nabard.org", "sebi.gov.in", "tnpsc.gov.in", "keralapsc.gov.in",
    "rpsc.rajasthan.gov.in", "bpsc.bihar.gov.in", "mppsc.mp.gov.in",
    "ncs.gov.in", "employmentnews.gov.in",
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
    r"\d{1,2}\s+[A-Za-z]{3,9}\s+\d{4}|"
    r"[A-Za-z]{3,9}\s+\d{1,2},?\s+\d{4})"
)

def clean(value):
    return re.sub(r"\s+", " ", value or "").strip()

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
    formats = (
        "%d/%m/%Y", "%d-%m-%Y", "%d.%m.%Y",
        "%d/%m/%y", "%d-%m-%y", "%d.%m.%y",
        "%d %B %Y", "%d %b %Y", "%B %d %Y", "%b %d %Y",
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
        r"number\s+of\s+vacanc(?:y|ies)|no\.\s*of\s*vacanc(?:y|ies))"
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
        r"last\s+date(?:\s+for|\s+of)?\s+(?:submission|receipt|apply|application)?",
        r"closing\s+date",
        r"apply\s+online\s+up\s+to",
        r"applications?\s+may\s+be\s+submitted\s+up\s+to",
        r"last\s+date\s+to\s+apply",
        r"online\s+application\s+ends?",
    ))
    notification_date = labelled_date(text, (
        r"date\s+of\s+notification", r"notification\s+date",
        r"date\s+of\s+advertisement", r"advertisement\s+date",
        r"published\s+on",
    ))
    qualification = re.search(
        r"(?:educational|essential|minimum|prescribed)\s+qualification(?:s)?"
        r"\s*[:\-]?\s*(.{20,260}?)(?:\b(?:age limit|pay scale|salary|"
        r"application fee|selection process|how to apply|important dates)\b)",
        text, re.I,
    )
    fee = re.search(r"(?:application fee|examination fee|exam fee|registration fee)\s*[:\-]?\s*([^\n.]{3,120})", text, re.I)
    age = re.search(r"(?:age limit|age criteria)\s*[:\-]?\s*([^\n.]{3,100})", text, re.I)
    selection = re.search(r"(?:selection process|mode of selection|selection procedure)\s*[:\-]?\s*([^\n.]{3,140})", text, re.I)
    return {
        "vacancies": vacancy,
        "last_date": last_date,
        "notification_date": notification_date,
        "qualification": clean(qualification.group(1))[:240] if qualification else None,
        "fees": clean(fee.group(1))[:120] if fee else None,
        "age_limit": clean(age.group(1))[:100] if age else None,
        "selection_process": clean(selection.group(1))[:140] if selection else None,
    }

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
        if any(term in searchable for term in EXCLUDE_HINTS):
            continue
        if not any(term in searchable for term in RECRUITMENT_HINTS):
            continue
        url = safe_url(anchor.get("href"), page_url)
        if url and normalized_url(url) != normalized_url(page_url) and normalized_url(url) not in seen:
            seen.add(normalized_url(url))
            found.append((title[:240], url))
    return found

def find_notice_pdf(session, html, page_url):
    soup = BeautifulSoup(html, "html.parser")
    pdf_urls = []
    for anchor in soup.select("a[href]"):
        label = clean(anchor.get_text(" ", strip=True)).lower()
        url = safe_url(anchor.get("href"), page_url)
        if not url:
            continue
        is_pdf = ".pdf" in urlparse(url).path.lower()
        notice_link = any(word in label for word in ("notification", "advertisement", "detailed notice", "download notice"))
        if is_pdf or notice_link:
            if normalized_url(url) not in [normalized_url(x) for x in pdf_urls]:
                pdf_urls.append(url)
    best_text, best_url = "", None
    for url in pdf_urls[:6]:
        text, final_url = extract_pdf_text(session, url)
        if len(text) > len(best_text):
            best_text, best_url = text, final_url
    return best_text, best_url

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

def main():
    if not DB.startswith("https://") or not KEY:
        print("CONFIG ERROR: GitHub secrets SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY are required.")
        return 2

    session = make_session()
    try:
        known_urls, known_titles = load_existing(session)
    except Exception as exc:
        print("SUPABASE READ ERROR:", str(exc)[:300])
        return 2

    candidates = []
    seen_links = set()
    source_errors = 0
    print("SCAN DATE (Asia/Kolkata):", TODAY.isoformat())
    print("SOURCE ORDER: Uttar Pradesh first, then central/national portals.")
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
        except Exception as exc:
            source_errors += 1
            print("SOURCE PARSE ERROR", source_name, str(exc)[:200])
        time.sleep(0.2)

    saved = skipped = duplicates = process_errors = 0
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
                notice_text, pdf_url = extract_pdf_text(session, detail_url)
                html = None
            else:
                html = data
                soup = BeautifulSoup(data, "html.parser")
                page_text = clean(soup.get_text(" ", strip=True))
                pdf_text, pdf_url = find_notice_pdf(session, data, detail_url)
                # Keep the page's own context and supplement it with PDF text.
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
            missing = []
            if not official(detail_url):
                missing.append("official notice URL")
            if not fields["last_date"]:
                missing.append("explicit last date")
            elif fields["last_date"] < TODAY.isoformat():
                missing.append("application deadline already passed")
            if len(clean(candidate_title)) < 12:
                missing.append("clear recruitment title")
            if missing:
                print("SKIP - essential verification missing:", ", ".join(missing), "|", candidate_title[:180])
                skipped += 1
                continue

            notification_url = pdf_url or detail_url
            title = clean(candidate_title)[:180]
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
                "description": (
                    "Official recruitment notice detected by SarkariJobAlert scanner. "
                    "This entry is saved as Draft for admin verification. "
                    "PDF is optional; open the official notice/source link and confirm all "
                    "eligibility, dates, fees, age relaxation and application instructions before publishing."
                ),
                "status": "draft",
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
            optional_missing = [
                key for key in ("vacancies", "qualification", "fees", "age_limit", "selection_process")
                if not fields.get(key)
            ]
            print("DRAFT SAVED:", title, "| optional fields not extracted:", ", ".join(optional_missing) or "none")
        except Exception as exc:
            process_errors += 1
            print("PROCESS ERROR:", candidate_title[:160], str(exc)[:280])
        time.sleep(0.2)

    print(
        "\nSCAN REPORT | date:", TODAY.isoformat(),
        "| official source pages:", len(SOURCES),
        "| source fetch/parse issues:", source_errors,
        "| candidate links:", len(candidates),
        "| drafts saved:", saved,
        "| skipped:", skipped,
        "| duplicates:", duplicates,
        "| processing errors:", process_errors,
        "| published: 0 (manual admin approval required)",
    )
    return 1 if process_errors else 0

if __name__ == "__main__":
    sys.exit(main())
