import os
import re
import time
import requests

from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from supabase import create_client


# =========================
# SUPABASE CONFIGURATION
# =========================

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    raise RuntimeError(
        "Missing GitHub Secrets: SUPABASE_URL or "
        "SUPABASE_SERVICE_ROLE_KEY"
    )

db = create_client(SUPABASE_URL, SUPABASE_KEY)


# =========================
# OFFICIAL JOB SOURCES
# =========================

SOURCES = [
    {
        "name": "Staff Selection Commission",
        "category": "Latest Jobs",
        "url": "https://ssc.gov.in/",
    },
    {
        "name": "Union Public Service Commission",
        "category": "Latest Jobs",
        "url": "https://upsc.gov.in/",
    },
    {
        "name": "Institute of Banking Personnel Selection",
        "category": "Latest Jobs",
        "url": "https://www.ibps.in/",
    },
    {
        "name": "State Bank of India",
        "category": "Latest Jobs",
        "url": "https://sbi.co.in/web/careers",
    },
    {
        "name": "Railway Recruitment Boards",
        "category": "Latest Jobs",
        "url": "https://rrb.indianrailways.gov.in/",
    },
]


# =========================
# LINK CLASSIFICATION
# =========================

CATEGORY_RULES = [
    (
        "Results",
        re.compile(
            r"\b(result|results|final result|merit list|"
            r"selection list|score card|scorecard)\b",
            re.I,
        ),
    ),
    (
        "Admit Card",
        re.compile(
            r"\b(admit card|hall ticket|call letter|"
            r"e-admission certificate)\b",
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
        re.compile(
            r"\b(admission|admissions|entrance application)\b",
            re.I,
        ),
    ),
]

JOB_KEYWORDS = re.compile(
    r"\b(recruitment|vacancies|vacancy|"
    r"advertisement|notification|apply online|"
    r"online application|employment|"
    r"direct recruitment|recruitment notice|"
    r"job opening|job openings)\b",
    re.I,
)

RELEVANT_KEYWORDS = re.compile(
    r"\b(recruitment|vacancies|vacancy|"
    r"advertisement|notification|apply online|"
    r"online application|employment|"
    r"admit card|hall ticket|call letter|"
    r"answer key|result|results|merit list|"
    r"scorecard|score card|syllabus|admission)\b",
    re.I,
)

EXCLUDED_KEYWORDS = re.compile(
    r"\b(tender|procurement|auction|"
    r"vendor registration|press release|"
    r"annual report|investor relations)\b",
    re.I,
)


def get_category(title):
    for category, pattern in CATEGORY_RULES:
        if pattern.search(title):
            return category

    return "Latest Jobs"


# =========================
# HTTP SESSION
# =========================

def create_session():
    session = requests.Session()

    retries = Retry(
        total=2,
        connect=2,
        read=2,
        backoff_factor=1,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET"],
    )

    adapter = HTTPAdapter(max_retries=retries)
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


# =========================
# FETCH OFFICIAL NOTICES
# =========================

def collect_links(source):
    print(f"\nChecking: {source['name']}")

    try:
        response = SESSION.get(
            source["url"],
            timeout=(15, 45),
            allow_redirects=True,
        )
        response.raise_for_status()

        soup = BeautifulSoup(response.text, "html.parser")
        found = {}

        for anchor in soup.find_all("a", href=True):
            title = " ".join(
                anchor.get_text(" ", strip=True).split()
            )

            href = anchor.get("href", "").strip()

            if not title or len(title) < 8:
                continue

            if not RELEVANT_KEYWORDS.search(title):
                continue

            if EXCLUDED_KEYWORDS.search(title):
                continue

            link = urljoin(response.url, href)

            parsed = urlparse(link)

            if parsed.scheme != "https":
                continue

            if parsed.netloc.lower() != urlparse(
                source["url"]
            ).netloc.lower():
                # Allow official subdomains of the same domain.
                source_domain = urlparse(
                    source["url"]
                ).netloc.lower()

                link_domain = parsed.netloc.lower()

                if not link_domain.endswith(
                    "." + source_domain
                ):
                    continue

            category = get_category(title)

            if category == "Latest Jobs":
                if not JOB_KEYWORDS.search(title):
                    continue

            found[link] = {
                "title": title[:250],
                "category": category,
                "link": link,
            }

        notices = []

        for item in list(found.values())[:25]:
            notices.append({
                "title": item["title"],
                "department": source["name"],
                "category": item["category"],
                "notification_url": item["link"],
                "apply_url": item["link"],
                "description": (
                    "Collected from an official source. "
                    "Verify the original notice for eligibility, "
                    "vacancies, fees, dates and application details."
                ),
                "status": "draft",
            })

        print(f"Possible notices found: {len(notices)}")

        for item in notices:
            print(
                f"  [{item['category']}] {item['title']}"
            )

        return notices

    except requests.exceptions.SSLError as error:
        print(
            f"SSL verification failed for {source['name']}: "
            f"{error}"
        )
    except requests.exceptions.RequestException as error:
        print(
            f"Source connection failed for {source['name']}: "
            f"{error}"
        )
    except Exception as error:
        print(
            f"Unexpected source error for {source['name']}: "
            f"{error}"
        )

    return []


# =========================
# DUPLICATE CHECK + SAVE
# =========================

def save_job(job):
    try:
        existing = (
            db.table("jobs")
            .select("id")
            .eq("notification_url", job["notification_url"])
            .limit(1)
            .execute()
        )

        if existing.data:
            print(f"Already exists: {job['title']}")
            return

        db.table("jobs").insert(job).execute()

        print(
            f"Saved as draft: [{job['category']}] "
            f"{job['title']}"
        )

    except Exception as error:
        print(f"Could not save {job['title']}: {error}")


# =========================
# MAIN
# =========================

def main():
    total_found = 0
    total_sources_failed = 0

    for source in SOURCES:
        notices = collect_links(source)

        if not notices:
            print(
                f"No candidate notices collected from "
                f"{source['name']}."
            )

        for job in notices:
            save_job(job)
            total_found += 1

        time.sleep(2)

    print("\n=========================")
    print("AUTOMATIC JOB CHECK FINISHED")
    print(f"Candidate notices: {total_found}")
    print("=========================")


if __name__ == "__main__":
    main()
