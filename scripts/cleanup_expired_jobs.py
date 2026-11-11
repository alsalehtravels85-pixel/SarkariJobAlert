#!/usr/bin/env python3
"""Unpublish expired vacancy posts while preserving their records.

Only Latest Jobs, Vacancy and Jobs categories are eligible. Admit Cards,
Results and other categories are excluded. Missing or invalid last_date is
never changed. Expired rows are moved from published to draft, not deleted,
so administrators can review or restore them when appropriate.
"""
import os
import sys
from datetime import datetime
from zoneinfo import ZoneInfo

import requests

DB = os.getenv("SUPABASE_URL", "").strip().rstrip("/")
KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "").strip()
HEADERS = {
    "apikey": KEY,
    "Authorization": "Bearer " + KEY,
    "Content-Type": "application/json",
    "Prefer": "return=representation",
}


def main():
    if not DB.startswith("https://") or not KEY:
        print("Missing SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY GitHub secret")
        return 2

    today = datetime.now(ZoneInfo("Asia/Kolkata")).date().isoformat()
    session = requests.Session()
    unpublished = 0

    try:
        while True:
            params = {
                "select": "id,title,last_date,status",
                "status": "eq.published",
                "category": 'in.("Latest Jobs",Vacancy,Jobs)',
                "last_date": "lt." + today,
                "order": "last_date.asc",
                "limit": "100",
            }
            response = session.get(
                DB + "/rest/v1/jobs", headers=HEADERS, params=params, timeout=30
            )
            response.raise_for_status()
            rows = response.json()
            if not isinstance(rows, list):
                raise ValueError("Unexpected Supabase response (expected list)")
            if not rows:
                break

            ids = [str(row["id"]) for row in rows if row.get("id") is not None]
            if not ids:
                raise ValueError("Eligible rows returned without IDs")

            update_params = {
                "id": "in.(" + ",".join(ids) + ")",
                "status": "eq.published",
                "last_date": "lt." + today,
            }
            result = session.patch(
                DB + "/rest/v1/jobs",
                headers=HEADERS,
                params=update_params,
                json={"status": "draft"},
                timeout=30,
            )
            result.raise_for_status()
            changed = result.json() if result.content else []
            if not isinstance(changed, list):
                raise ValueError("Unexpected update response (expected list)")
            if not changed:
                raise RuntimeError("No rows updated; stopping to avoid an infinite loop")

            unpublished += len(changed)
            for row in changed:
                print("UNPUBLISHED", row.get("id"), row.get("title"),
                      "last_date=", row.get("last_date"))

        print(f"EXPIRY REVIEW | India date={today} | expired published vacancies moved to draft={unpublished} | records preserved")
        return 0
    except Exception as exc:
        print("EXPIRY CLEANUP ERROR:", str(exc)[:500])
        return 1


if __name__ == "__main__":
    sys.exit(main())
