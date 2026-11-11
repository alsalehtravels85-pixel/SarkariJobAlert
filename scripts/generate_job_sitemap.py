#!/usr/bin/env python3
"""Generate a public sitemap for published SarkariJobAlert posts.

Uses the existing Supabase jobs table and service-role credentials supplied by
GitHub Actions. Drafts are never included. Expired Vacancy posts are excluded.
Current public detail URLs use crawlable /jobs/<slug>-<id>.html pages.
"""
import os
import sys
from datetime import date, datetime
from zoneinfo import ZoneInfo
from xml.etree.ElementTree import Element, SubElement, ElementTree, register_namespace
from pathlib import Path

import requests
from generate_job_pages import public_rows, slugify

BASE = "https://sarkari-jobalert.com"
DB = os.getenv("SUPABASE_URL", "").strip().rstrip("/")
KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "").strip()
OUT = Path("sitemap-jobs.xml")
PAGE_SIZE = 1000
TODAY = datetime.now(ZoneInfo("Asia/Kolkata")).date()


def iso_date(value):
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00")).date().isoformat()
    except ValueError:
        return None


def main():
    if not DB or not KEY:
        print("ERROR: SUPABASE_URL / SUPABASE_SERVICE_ROLE_KEY missing")
        return 2

    headers = {
        "apikey": KEY,
        "Authorization": f"Bearer {KEY}",
        "Accept": "application/json",
    }
    rows = []
    offset = 0
    session = requests.Session()

    while True:
        params = {
            "select": "id,title,category,last_date,updated_at,created_at,status",
            "status": "eq.published",
            "order": "updated_at.desc.nullslast,created_at.desc",
            "limit": PAGE_SIZE,
            "offset": offset,
        }
        response = session.get(
            f"{DB}/rest/v1/jobs",
            headers={**headers, "Range-Unit": "items", "Range": f"{offset}-{offset + PAGE_SIZE - 1}"},
            params=params,
            timeout=(12, 35),
        )
        response.raise_for_status()
        batch = response.json()
        if not isinstance(batch, list):
            raise RuntimeError("Supabase jobs response was not a list")
        rows.extend(batch)
        if len(batch) < PAGE_SIZE:
            break
        offset += PAGE_SIZE

    register_namespace("", "http://www.sitemaps.org/schemas/sitemap/0.9")
    root = Element("{http://www.sitemaps.org/schemas/sitemap/0.9}urlset")
    included = 0
    expired = sum(1 for row in rows if row.get("status") == "published" and (row.get("category") or "").strip().lower() in ("vacancy", "latest jobs", "jobs") and iso_date(row.get("last_date")) and iso_date(row.get("last_date")) < TODAY.isoformat())
    for row in public_rows(rows):
        node = SubElement(root, "{http://www.sitemaps.org/schemas/sitemap/0.9}url")
        SubElement(node, "{http://www.sitemaps.org/schemas/sitemap/0.9}loc").text = (
            f"{BASE}/jobs/{slugify(row["title"])}-{row['id']}.html"
        )
        lastmod = iso_date(row.get("updated_at") or row.get("created_at"))
        if lastmod:
            SubElement(node, "{http://www.sitemaps.org/schemas/sitemap/0.9}lastmod").text = lastmod
        included += 1

    ElementTree(root).write(OUT, encoding="utf-8", xml_declaration=True)
    print(f"JOB SITEMAP GENERATED | published rows fetched: {len(rows)} | URLs included: {included} | expired vacancies excluded: {expired} | file: {OUT}")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:
        print("SITEMAP GENERATION ERROR:", str(exc)[:500])
        sys.exit(1)
