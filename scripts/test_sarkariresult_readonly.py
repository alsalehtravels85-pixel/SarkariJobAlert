import re
import sys
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

BASE = "https://www.sarkariresult.com"
PAGES = {
    "Latest Jobs": f"{BASE}/latestjob/",
    "Admit Card": f"{BASE}/admitcard/",
    "Result": f"{BASE}/result/",
}
HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; SarkariJobAlertReadOnlyTest/1.0)",
    "Accept": "text/html,application/xhtml+xml",
}

session = requests.Session()
session.headers.update(HEADERS)
failed = False

def fetch(label, url):
    global failed
    print(f"\n=== {label} ===")
    try:
        response = session.get(url, timeout=25)
        print("URL:", url)
        print("HTTP:", response.status_code)
        print("Final URL:", response.url)
        print("Content-Type:", response.headers.get("content-type", ""))
        if response.status_code != 200:
            print("RESULT: page could not be read")
            failed = True
            return None
        soup = BeautifulSoup(response.text, "html.parser")
        print("Page title:", soup.title.get_text(" ", strip=True) if soup.title else "(missing)")
        anchors = []
        seen = set()
        for a in soup.find_all("a", href=True):
            href = urljoin(response.url, a["href"].strip())
            text = re.sub(r"\s+", " ", a.get_text(" ", strip=True))
            if href.startswith(("http://", "https://")) and href not in seen and text:
                seen.add(href)
                anchors.append((text, href))
        print("Text links found:", len(anchors))
        for text, href in anchors[:12]:
            print("-", text[:110], "=>", href)
        return soup, anchors
    except Exception as exc:
        print("ERROR:", type(exc).__name__, str(exc)[:300])
        failed = True
        return None

listing = fetch("Latest Jobs listing", PAGES["Latest Jobs"])
for label in ("Admit Card", "Result"):
    fetch(label + " listing", PAGES[label])

if listing:
    _, links = listing
    candidates = [
        (text, href) for text, href in links
        if "upessc" in text.lower() and ("primary teacher" in text.lower() or "super tet" in text.lower())
    ]
    if not candidates:
        candidates = [(text, href) for text, href in links if "online form" in text.lower()]
    if candidates:
        title, detail_url = candidates[0]
        print("\nSelected detail link:", title, "=>", detail_url)
        detail = fetch("Selected job detail page", detail_url)
        if detail:
            soup, anchors = detail
            print("Detail page tables:", len(soup.find_all("table")))
            print("Relevant detail links:")
            keywords = ("notification", "apply", "admit", "result", "syllabus", "vacancy", "download", "registration", "login")
            count = 0
            for text, href in anchors:
                if any(k in text.lower() for k in keywords):
                    print("-", text[:100], "=>", href)
                    count += 1
                    if count >= 30:
                        break
            if count == 0:
                print("(No keyword-matching anchor labels; raw page may still contain the information.)")
    else:
        print("\nNo matching detail link found on Latest Jobs page.")
        failed = True

print("\n=== READ-ONLY TEST SUMMARY ===")
print("Database writes: NONE")
print("Supabase secrets used: NO")
print("Overall:", "CHECK FAILED / ACCESS INCOMPLETE" if failed else "HTTP/PAGE READ TEST PASSED")
sys.exit(1 if failed else 0)
