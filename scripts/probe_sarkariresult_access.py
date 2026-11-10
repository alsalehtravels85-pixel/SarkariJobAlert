#!/usr/bin/env python3
"""Read-only connectivity probe for SarkariResult discovery.

This experimental probe does not read or write Supabase and does not publish jobs.
It asks Bing's public RSS search for indexed SarkariResult URLs only, then checks
whether the original SarkariResult pages are directly readable from the runner.
It does not use proxies or bypass access controls.
"""
import urllib.parse
import xml.etree.ElementTree as ET
import requests

UA = "SarkariJobAlert-SourceProbe/1.0 (+https://github.com/alsalehtravels85-pixel/SarkariJobAlert)"
SEARCH_URL = "https://www.bing.com/search"
CATEGORIES = {
    "Vacancy": 'site:sarkariresult.com/latestjob/ after:2026-10-01',
    "Admit Card": 'site:sarkariresult.com/admitcard/ after:2026-10-01',
    "Result": 'site:sarkariresult.com/result/ after:2026-10-01',
}
session = requests.Session()
session.headers.update({"User-Agent": UA, "Accept": "application/rss+xml,application/xml,text/xml,*/*"})
total = 0
for category, query in CATEGORIES.items():
    print(f"\n=== {category} ===")
    url = "https://www.bing.com/search?format=rss&q=" + urllib.parse.quote(query)
    try:
        response = session.get(url, timeout=(12, 25))
        print("SEARCH_HTTP", response.status_code)
        response.raise_for_status()
        root = ET.fromstring(response.content)
        items = root.findall(".//item")
        valid = []
        for item in items:
            title = (item.findtext("title") or "").strip()
            link = (item.findtext("link") or "").strip()
            desc = (item.findtext("description") or "").strip()
            host = urllib.parse.urlparse(link).hostname or ""
            if host == "sarkariresult.com" or host.endswith(".sarkariresult.com"):
                valid.append((title, link, desc))
        print("INDEXED_SARKARIRESULT_ITEMS", len(valid))
        for title, link, desc in valid[:8]:
            print("ITEM", title[:180])
            print("URL", link)
            print("SNIPPET", desc[:500])
            total += 1
            try:
                page = session.get(link, timeout=(12, 25), allow_redirects=True)
                print("DETAIL_HTTP", page.status_code, "FINAL_HOST", urllib.parse.urlparse(page.url).hostname)
                if page.status_code == 200:
                    print("DETAIL_BYTES", len(page.content), "CONTENT_TYPE", page.headers.get("Content-Type", ""))
            except requests.RequestException as exc:
                print("DETAIL_ERROR", str(exc)[:220])
    except Exception as exc:
        print("SEARCH_ERROR", str(exc)[:300])
print("\nTOTAL_INDEXED_SARKARIRESULT_ITEMS", total)
print("SUPABASE_READS=0")
print("SUPABASE_WRITES=0")
print("AUTO_PUBLISH=0")
