import os
import re
import requests
from bs4 import BeautifulSoup
from supabase import create_client

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    raise RuntimeError(
        "GitHub Secrets mein SUPABASE_URL aur "
        "SUPABASE_SERVICE_ROLE_KEY set karein."
    )

db = create_client(SUPABASE_URL, SUPABASE_KEY)

SOURCES = [
    {
        "name": "Staff Selection Commission",
        "category": "SSC",
        "url": "https://ssc.gov.in/",
    },
    {
        "name": "Union Public Service Commission",
        "category": "UPSC",
        "url": "https://upsc.gov.in/",
    },
    {
        "name": "Institute of Banking Personnel Selection",
        "category": "Banking",
        "url": "https://www.ibps.in/",
    },
    {
        "name": "State Bank of India",
        "category": "Banking",
        "url": "https://sbi.co.in/web/careers",
    },
    {
        "name": "Railway Recruitment Boards",
        "category": "Railway",
        "url": "https://rrb.indianrailways.gov.in/",
    },
]

KEYWORDS = re.compile(
    r"recruitment|vacanc|notification|advertisement|"
    r"employment|apply online|career|job|"
    r"examination|exam notice|result",
    re.IGNORECASE,
)

HEADERS = {
    "User-Agent": "SarkariJobAlertBot/1.0 (public job notice checker)"
}


def collect_links(source):
    print(f"\nChecking: {source['name']}")

    try:
        response = requests.get(
            source["url"],
            headers=HEADERS,
            timeout=25,
        )
        response.raise_for_status()

        soup = BeautifulSoup(response.text, "html.parser")
        found = {}

        for anchor in soup.find_all("a", href=True):
            title = " ".join(anchor.get_text(" ", strip=True).split())
            href = anchor["href"].strip()

            if not title or len(title) < 8:
                continue

            if not KEYWORDS.search(title):
                continue

            if href.startswith(("javascript:", "mailto:", "#")):
                continue

            link = requests.compat.urljoin(source["url"], href)

            if not link.startswith(("https://", "http://")):
                continue

            found[link] = title[:250]

        print(f"Possible notices found: {len(found)}")

        return [
            {
                "title": title,
                "department": source["name"],
                "category": source["category"],
                "notification_url": link,
                "apply_url": link,
                "description": (
                    "Official source link collected automatically. "
                    "Verify the notice and application details before "
                    "publishing."
                ),
                "status": "draft",
            }
            for link, title in list(found.items())[:15]
        ]

    except Exception as error:
        print(f"Source check failed: {error}")
        return []


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
        print(f"Saved as draft: {job['title']}")

    except Exception as error:
        print(f"Could not save {job['title']}: {error}")


def main():
    total = 0

    for source in SOURCES:
        jobs = collect_links(source)

        for job in jobs:
            save_job(job)
            total += 1

    print(f"\nFinished. Candidate notices checked: {total}")


if __name__ == "__main__":
    main()
