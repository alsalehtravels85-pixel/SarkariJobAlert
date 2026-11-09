#!/usr/bin/env python3
"""Delete expired vacancies (manual or scanner-created) 30 days after last_date.

Only category=Latest Jobs is eligible. Admit Cards, Results and other
categories are excluded. Missing or invalid last_date is not deleted.
"""
import os
import sys
from datetime import datetime, timedelta
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

    today = datetime.now(ZoneInfo("Asia/Kolkata")).date()
    cutoff = (today - timedelta(days=30)).isoformat()
    session = requests.Session()
    deleted = 0

    # Re-query from the beginning after each batch so there is no offset
    # pagination gap when the selected records are deleted.
    try:
        while True:
            params = {
                "select": "id,title,last_date",
                "category": 'in.("Latest Jobs",Vacancy,Jobs)',
                "last_date": "lte." + cutoff,
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

            delete_params = {
                "id": "in.(" + ",".join(ids) + ")",
                "category": "eq.Latest Jobs",
                "last_date": "lte." + cutoff,
            }
            result = session.delete(
                DB + "/rest/v1/jobs",
                headers=HEADERS,
                params=delete_params,
                timeout=30,
            )
            result.raise_for_status()
            removed = result.json() if result.content else []
            if not isinstance(removed, list):
                raise ValueError("Unexpected delete response (expected list)")
            if not removed:
                raise RuntimeError("No rows deleted; stopping to avoid infinite loop")
            deleted += len(removed)
            for row in removed:
                print(
                    "DELETED",
                    row.get("id"),
                    row.get("title"),
                    "last_date=",
                    row.get("last_date"),
                )

        print(
            f"CLEANUP REPORT | India date={today} | vacancy last_date<={cutoff}"
            f" | deleted={deleted} | manual+automatic | all statuses"
        )
        return 0
    except Exception as exc:
        print("CLEANUP ERROR:", exc)
        return 1


if __name__ == "__main__":
    sys.exit(main())
