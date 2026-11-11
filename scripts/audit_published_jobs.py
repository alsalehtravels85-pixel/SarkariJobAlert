#!/usr/bin/env python3
"""Read-only AdSense content audit for published SarkariJobAlert records.

Exports a review CSV. It NEVER updates or deletes Supabase rows.
Rows are classified for human review; an automated heuristic is not an AdSense verdict.
"""
import csv
import os
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse
from zoneinfo import ZoneInfo

import requests

DB = os.getenv("SUPABASE_URL", "").strip().rstrip("/")
KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "").strip()
OUT = Path("audit-output")
TODAY = datetime.now(ZoneInfo("Asia/Kolkata")).date()


def is_url(value):
    try:
        p = urlparse(str(value or "").strip())
        return p.scheme in ("http", "https") and bool(p.hostname)
    except ValueError:
        return False


def category(row):
    return str(row.get("category") or "").strip().lower()


def assess(row):
    """Return conservative flags; never label a genuine post as definitely bad."""
    flags = []
    title = str(row.get("title") or "").strip()
    department = str(row.get("department") or "").strip()
    description = str(row.get("description") or "").strip()
    cat = category(row)
    vacancy = cat in ("vacancy", "latest jobs", "jobs")
    notification = row.get("notification_url")
    source = row.get("source_url")
    action_url = (
        row.get("apply_url") if vacancy else
        row.get("admit_card_url") if cat in ("admit card", "admitcard") else
        row.get("result_url") if cat in ("result", "results") else None
    )

    if not title:
        flags.append("missing_title")
    if not department:
        flags.append("missing_department")
    if len(description) < 350:
        flags.append("thin_description_under_350_chars")
    if not is_url(notification) and not is_url(source):
        flags.append("missing_source_or_notification_url")
    if vacancy:
        if not str(row.get("qualification") or "").strip():
            flags.append("missing_qualification")
        if not str(row.get("last_date") or "").strip():
            flags.append("missing_last_date")
        if not is_url(notification):
            flags.append("missing_notification_url")
        if not is_url(action_url):
            flags.append("missing_apply_url")
        last_date = str(row.get("last_date") or "")[:10]
        try:
            if last_date and datetime.strptime(last_date, "%Y-%m-%d").date() < TODAY:
                flags.append("expired_vacancy")
        except ValueError:
            flags.append("invalid_last_date")
    elif cat in ("admit card", "admitcard"):
        if not is_url(action_url):
            flags.append("missing_admit_card_link")
    elif cat in ("result", "results"):
        if not is_url(action_url):
            flags.append("missing_result_link")
    else:
        flags.append("unknown_category_review")

    # Any flag means human review is needed; no row is auto-deleted.
    return flags, ("REVIEW_BEFORE_PUBLISH" if flags else "PASSES_BASIC_CHECKS")


def fetch_all():
    headers = {"apikey": KEY, "Authorization": f"Bearer {KEY}", "Accept": "application/json"}
    rows, offset = [], 0
    with requests.Session() as session:
        while True:
            params = {
                "select": "*", "status": "eq.published",
                "order": "created_at.desc", "limit": 500, "offset": offset,
            }
            response = session.get(f"{DB}/rest/v1/jobs", headers=headers, params=params, timeout=(12, 35))
            response.raise_for_status()
            batch = response.json()
            if not isinstance(batch, list):
                raise RuntimeError("Unexpected Supabase response")
            rows.extend(batch)
            if len(batch) < 500:
                return rows
            offset += 500


def write_report(rows, output=OUT):
    output.mkdir(parents=True, exist_ok=True)
    path = output / "published-jobs-adsense-audit.csv"
    fields = [
        "id", "title", "department", "category", "status", "last_date",
        "description_length", "notification_url", "source_url", "apply_url",
        "admit_card_url", "result_url", "recommended_action", "review_flags",
    ]
    with path.open("w", newline="", encoding="utf-8-sig") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            flags, action = assess(row)
            writer.writerow({
                "id": row.get("id", ""),
                "title": row.get("title", ""),
                "department": row.get("department", ""),
                "category": row.get("category", ""),
                "status": row.get("status", ""),
                "last_date": row.get("last_date", ""),
                "description_length": len(str(row.get("description") or "").strip()),
                "notification_url": row.get("notification_url", ""),
                "source_url": row.get("source_url", ""),
                "apply_url": row.get("apply_url", ""),
                "admit_card_url": row.get("admit_card_url", ""),
                "result_url": row.get("result_url", ""),
                "recommended_action": action,
                "review_flags": ";".join(flags),
            })
    flagged = sum(bool(assess(row)[0]) for row in rows)
    print(f"READ-ONLY AUDIT | published={len(rows)} | needs_review={flagged} | passes_basic_checks={len(rows)-flagged} | report={path}")
    print("NO DATABASE ROWS WERE UPDATED OR DELETED.")
    return path


def main():
    if not DB.startswith("https://") or not KEY:
        raise RuntimeError("SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY secrets are required")
    rows = fetch_all()
    write_report(rows)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
