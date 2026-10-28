import os
import re
import time
import requests

from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from supabase import create_client


# ==================================================
# SUPABASE
# ==================================================

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    raise RuntimeError(
        "GitHub Secrets missing: SUPABASE_URL / "
        "SUPABASE_SERVICE_ROLE_KEY"
    )

db = create_client(SUPABASE_URL, SUPABASE_KEY)


# ==================================================
# OFFICIAL NOTICE PAGES
# ==================================================

SOURCES = [
    {
        "name": "Staff Selection Commission",
        "url": "https://ssc.gov.in/",
        "hosts": ["ssc.gov.in"],
    },
    {
        "name": "UPSC Recruitment Advertisements",
        "url": "https://www.upsc.gov.in/recruitment/recruitment-advertisement",
        "hosts": ["upsc.gov.in"],
    },
    {
        "name": "IBPS Recruitment",
        "url": "https://www.ibps.in/index.php/recruitment/",
        "hosts": ["ibps.in"],
    },
    {
        "name": "IBPS Recent Updates",
        "url": "https://www.ibps.in/index.php/crp-updates/",
        "hosts": ["ibps.in"],
    },
    {
        "name": "Railway Recruitment Notices",
        "url": "https://www.rrbcdg.gov.in/employment-notices.php",
        "hosts": ["rrbcdg.gov.in"],
    },
    {
        "name": "State Bank of India Careers",
        "url": "https://sbi.co.in/web/careers",
        "hosts": ["sbi.co.in", "bank.sbi"],
    },
]


# ==================================================
# ALLOWED CATEGORIES
# ==================================================

ALLOWED_CATEGORIES = {
    "Latest Jobs",
    "Admit Card",
    "Results",
    "Answer Key",
    "Admission",
    "Syllabus",
}


# ==================================================
# KEYWORD RULES
# ==================================================

CATEGORY_RULES = [
    (
        "Results",
        re.compile(
            r"\b(result|results|merit list|score card|"
            r"scorecard|marks of candidates|final result)\b",
            re.I,
        ),
    ),
    (
        "Admit Card",
        re.compile(
            r"\b(admit card|hall ticket|call letter|"
            r"admission certificate)\b",
            re.I,
        ),
    ),
    (
        "Answer Key",
        re.compile(r"\b(answer key|answer keys)\b", re.I),
    ),
    (
        "Syllabus",
        re.compile(r"\b(syllabus|exam pattern)\b", re.I),
    ),
    (
        "Admission",
        re.compile(r"\b(admission|entrance application)\b", re.I),
    ),
]

JOB_KEYWORDS = re.compile(
    r"\b(recruitment|vacancy|vacancies|"
    r"apply online|online application|"
    r"employment notice|recruitment notice|"
    r"recruitment advertisement|"
    r"invites applications|invited applications|"
    r"notification for recruitment|"
    r"engagement of|appointment of|"
    r"selection posts|combined graduate level|"
    r"combined higher secondary|"
    r"junior engineer examination|"
    r"assistant loco pilot|station master|"
    r"rrb ntpc|group d|group-d|"
    r"po/mt|crp-rrb|crp-spl|clerk recruitment)\b",
    re.I,
)

EXCLUDED_KEYWORDS = re.compile(
    r"\b(tender|procurement|auction|"
    r"vendor registration|press release|"
    r"annual report|investor relations|"
    r"recruitment results archive|"
    r"results archive|archives|"
    r"old notices|previous notices)\b",
    re.I,
)


def classify_notice(title):
    for category, pattern in CATEGORY_RULES:
        if pattern.search(title):
            return category

    if JOB_KEYWORDS.search(title):
        return "Latest Jobs"

    return None


# ==================================================
# HTTP SESSION
# ==================================================

def create_session():
    session = requests.Session()

    retry = Retry(
        total=2,
        connect=2,
        read=2,
        backoff_factor=1,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET"],
    )

    adapter = HTTPAdapter(max_retries=retry)

    session.mount("https://", adapter)
    session.mount("http://", adapter)

    session.headers.update({
        "User-Agent": (
            "Mozilla/5.0 (compatible; SarkariJobAlertBot/1.0)"
        ),
        "Accept": "text/html,application/xhtml+xml",
    })

    return session


SESSION = create_session()


# ==================================================
# DOMAIN VALIDATION
# ==================================================

def is_allowed_official_link(link, allowed_hosts):
    parsed = urlparse(link)

    if parsed.scheme != "https":
        return False

    host = (parsed.hostname or "").lower()

    for allowed in allowed_hosts:
        allowed = allowed.lower()

        if host == allowed or host.endswith("." + allowed):
            return True

    return False


# ==================================================
# FETCH NOTICES
# ==================================================

def collect_notices(source):
    print(f"\nChecking: {source['name']}")
    notices = {}

    try:
        response = SESSION.get(
            source["url"],
            timeout=(15, 45),
        )
        response.raise_for_status()

        soup = BeautifulSoup(response.text, "html.parser")

        for anchor in soup.select("a[href]"):
            href = anchor.get("href", "").strip()

            if not href:
                continue

            link = urljoin(response.url, href)

            if not is_allowed_official_link(
                link,
                source["hosts"],
            ):
                continue

            # Use nearby text if PDF link has no visible title.
            anchor_text = " ".join(
                anchor.get_text(" ", strip=True).split()
            )

            parent = anchor.find_parent(
                ["tr", "li", "article"]
            )

            nearby_text = ""

            if parent:
                nearby_text = " ".join(
                    parent.get_text(" ", strip=True).split()
                )

            title = anchor_text

            if len(title) < 8 and len(nearby_text) >= 8:
                title = nearby_text

            if not title or len(title) < 8:
                continue

            title = title[:250]

            if EXCLUDED_KEYWORDS.search(title):
                continue

            category = classify_notice(title)

            if category not in ALLOWED_CATEGORIES:
                continue

            # Ignore links which only say generic navigation text.
            if title.lower() in {
                "view all",
                "read more",
                "click here",
                "home",
                "careers",
                "recruitment",
                "results",
            }:
                continue

            notices[link] = {
                "title": title,
                "department": source["name"],
                "category": category,
                "notification_url": link,
                "apply_url": link,
                "description": (
                    "Official source link collected automatically. "
                    "Verify the original notification for eligibility, "
                    "vacancies, fees, dates and application details."
                ),
                "status": "draft",
            }

        print(f"Candidate notices found: {len(notices)}")

        for notice in notices.values():
            print(
                f"  [{notice['category']}] "
                f"{notice['title']}"
            )

    except requests.exceptions.SSLError as error:
        print(f"SSL error: {source['name']}: {error}")

    except requests.exceptions.RequestException as error:
        print(f"Connection error: {source['name']}: {error}")

    except Exception as error:
        print(f"Unexpected error: {source['name']}: {error}")

    return list(notices.values())


# ==================================================
# CHECK DUPLICATES AND SAVE
# ==================================================

def save_notice(notice):
    try:
        if notice["category"] not in ALLOWED_CATEGORIES:
            print(
                f"Skipped invalid category: "
                f"{notice['category']}"
            )
            return False

        result = (
            db.table("jobs")
            .select("id")
            .eq(
                "notification_url",
                notice["notification_url"],
            )
            .limit(1)
            .execute()
        )

        if result.data:
            print(f"Already exists: {notice['title']}")
            return False

        db.table("jobs").insert(notice).execute()

        print(
            f"Saved as draft: "
            f"[{notice['category']}] {notice['title']}"
        )

        return True

    except Exception as error:
        print(
            f"Database save failed for "
            f"{notice['title']}: {error}"
        )
        return False


# ==================================================
# MAIN
# ==================================================

def main():
    total_found = 0
    total_saved = 0
    total_failed = 0

    for source in SOURCES:
        notices = collect_notices(source)

        total_found += len(notices)

        for notice in notices:
            if save_notice(notice):
                total_saved += 1

        time.sleep(2)

    print("\n================================")
    print("SARKARI JOB ALERT - CHECK REPORT")
    print(f"Candidate notices: {total_found}")
    print(f"New notices saved: {total_saved}")
    print(f"Save failures: {total_failed}")
    print("================================")


if __name__ == "__main__":
    main()
