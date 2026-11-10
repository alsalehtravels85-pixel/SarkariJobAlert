#!/usr/bin/env python3
"""Read-only access probe for FreeJobAlert.com. No database/API writes."""
import json
import time
from urllib.parse import urljoin, urlparse
from urllib.robotparser import RobotFileParser

import requests
from bs4 import BeautifulSoup

BASE = "https://www.freejobalert.com/"
UA = "SarkariJobAlertReadOnlyProbe/1.0 (+https://github.com/alsalehtravels85-pixel/SarkariJobAlert)"
PATHS = ["/", "/search-results/", "/sitemap.xml", "/sitemap-general.xml"]
session = requests.Session()
session.headers.update({"User-Agent": UA, "Accept": "text/html,application/xml;q=0.9,*/*;q=0.8"})
session.max_redirects = 5
report = {"site": BASE, "mode": "read-only", "robots": {}, "checks": [], "sample_job_links": []}

robots_url = urljoin(BASE, "robots.txt")
try:
    r = session.get(robots_url, timeout=(12, 25))
    report["robots"] = {"status": r.status_code, "url": r.url, "bytes": len(r.content)}
    rp = RobotFileParser()
    rp.set_url(robots_url)
    rp.parse(r.text.splitlines() if r.ok else [])
    report["robots"]["our_user_agent_allowed"] = rp.can_fetch(UA, BASE)
    report["robots"]["sitemaps"] = [line.split(":", 1)[1].strip() for line in r.text.splitlines()
                                      if line.lower().startswith("sitemap:")]
except Exception as e:
    report["robots"] = {"error": str(e)[:300]}

for path in PATHS:
    url = urljoin(BASE, path)
    item = {"path": path}
    try:
        if report["robots"].get("our_user_agent_allowed") is False:
            item["skipped"] = "robots.txt disallows this crawler"
        else:
            r = session.get(url, timeout=(12, 30), allow_redirects=True)
            item.update({"status": r.status_code, "final_url": r.url,
                         "content_type": r.headers.get("Content-Type", ""),
                         "bytes": len(r.content)})
            if r.status_code == 200 and "html" in r.headers.get("Content-Type", "").lower():
                soup = BeautifulSoup(r.text, "html.parser")
                links = []
                for a in soup.select("a[href]"):
                    href = urljoin(r.url, a.get("href", ""))
                    host = (urlparse(href).hostname or "").lower()
                    label = " ".join(a.get_text(" ", strip=True).split())
                    if host.endswith("freejobalert.com") and label and len(label) > 8:
                        low = label.lower()
                        if any(k in low for k in ("recruitment", "online form", "vacancy", "posts", "jobs")):
                            links.append({"title": label[:180], "url": href})
                if links:
                    report["sample_job_links"].extend(links[:25])
    except Exception as e:
        item["error"] = str(e)[:300]
    report["checks"].append(item)
    time.sleep(1.5)

# Deduplicate and keep a compact artifact.
seen = set()
unique = []
for link in report["sample_job_links"]:
    if link["url"] not in seen:
        seen.add(link["url"])
        unique.append(link)
report["sample_job_links"] = unique[:30]
print(json.dumps(report, ensure_ascii=False, indent=2))
