#!/usr/bin/env python3
"""Read-only SarkariResult indexed-discovery experiment.

Searches Bing's public RSS index with broad category terms constrained to
SarkariResult's own domain and subdomains. Then tests direct access to returned
SarkariResult pages. No Supabase access, writes, publishing, proxies or bypasses.
"""
import urllib.parse
import xml.etree.ElementTree as ET
import requests

UA = "SarkariJobAlert-SourceProbe/1.1 (+https://github.com/alsalehtravels85-pixel/SarkariJobAlert)"
CATEGORIES = {
    "Vacancy": 'site:sarkariresult.com (recruitment OR vacancy OR "online form") 2026',
    "Admit Card": 'site:sarkariresult.com ("admit card" OR "hall ticket") 2026',
    "Result": 'site:sarkariresult.com (result OR "merit list" OR "score card") 2026',
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
        print("SEARCH_INDEX_ITEMS", len(items))
        valid = []
        for item in items:
            title = (item.findtext("title") or "").strip()
            link = (item.findtext("link") or "").strip()
            desc = (item.findtext("description") or "").strip()
            host = (urllib.parse.urlparse(link).hostname or "").lower().rstrip(".")
            if host == "sarkariresult.com" or host.endswith(".sarkariresult.com"):
                valid.append((title, link, desc))
        print("INDEXED_SARKARIRESULT_ITEMS", len(valid))
        for title, link, desc in valid[:10]:
            print("ITEM", title[:180])
            print("URL", link)
            print("SNIPPET", desc[:500])
            total += 1
            try:
                page = session.get(link, timeout=(12, 25), allow_redirects=True)
                final_host = (urllib.parse.urlparse(page.url).hostname or "").lower()
                print("DETAIL_HTTP", page.status_code, "FINAL_HOST", final_host, "BYTES", len(page.content))
            except requests.RequestException as exc:
                print("DETAIL_ERROR", str(exc)[:220])
    except Exception as exc:
        print("SEARCH_ERROR", str(exc)[:300])
print("\nTOTAL_INDEXED_SARKARIRESULT_ITEMS", total)
print("SUPABASE_READS=0")
print("SUPABASE_WRITES=0")
print("AUTO_PUBLISH=0")
