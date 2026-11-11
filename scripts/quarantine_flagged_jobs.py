#!/usr/bin/env python3
"""Safely unpublish published posts flagged by the AdSense content audit.

All rows are backed up before any change. Records are moved to Draft, never
permanently deleted. Only rows with audit flags are changed.
"""
import json
from pathlib import Path
import requests

from audit_published_jobs import DB, KEY, fetch_all, assess

OUT = Path("audit-output")


def main():
    if not DB.startswith("https://") or not KEY:
        raise RuntimeError("SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY are required")
    rows = fetch_all()
    OUT.mkdir(parents=True, exist_ok=True)
    backup = OUT / "pre-quarantine-published-jobs.json"
    backup.write_text(json.dumps(rows, ensure_ascii=False, indent=2, default=str), encoding="utf-8")

    flagged = []
    for row in rows:
        flags, _ = assess(row)
        if flags and row.get("id") and row.get("status") == "published":
            flagged.append((str(row["id"]), row.get("title", ""), flags))

    if not flagged:
        print("No flagged published records. No changes made.")
        return 0

    headers = {
        "apikey": KEY,
        "Authorization": f"Bearer {KEY}",
        "Content-Type": "application/json",
        "Prefer": "return=representation",
    }
    changed = 0
    with requests.Session() as session:
        for start in range(0, len(flagged), 50):
            batch = flagged[start:start + 50]
            ids = [item[0] for item in batch]
            response = session.patch(
                f"{DB}/rest/v1/jobs",
                headers=headers,
                params={"id": "in.(" + ",".join(ids) + ")", "status": "eq.published"},
                json={"status": "draft"},
                timeout=(12, 35),
            )
            response.raise_for_status()
            updated = response.json()
            if not isinstance(updated, list):
                raise RuntimeError("Unexpected Supabase update response")
            changed += len(updated)
            for row in updated:
                match = next((item for item in batch if item[0] == str(row.get("id"))), None)
                print("MOVED TO DRAFT:", row.get("id"), row.get("title"), "| flags:", ";".join(match[2]) if match else "review")

    print(f"QUARANTINE COMPLETE | flagged={len(flagged)} | moved_to_draft={changed} | backup={backup} | permanent_deletes=0")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
