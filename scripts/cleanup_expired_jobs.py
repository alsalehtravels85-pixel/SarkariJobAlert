#!/usr/bin/env python3
"""Delete expired Vacancy rows only. Never delete other categories or undated rows."""
import os
import sys
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import requests

def main():
    url = os.getenv("SUPABASE_URL", "").strip().rstrip("/")
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "").strip()
    if not url.startswith("https://") or not key:
        return 2
    today = datetime.now(ZoneInfo("Asia/Kolkata")).date()
    cutoff = (today - timedelta(days=15)).isoformat()
    headers = {"apikey": key, "Authorization": "Bearer " + key,
               "Prefer": "return=representation"}
    params = {"select": "id,title,last_date", "category": "eq.Vacancy", "status": "eq.published",
              "last_date": "lte." + cutoff}
    try:
        session = requests.Session()
        count = 0
        while True:
            r = session.get(url + "/rest/v1/jobs", headers=headers,
                            params={**params, "limit": "100"}, timeout=30)
            r.raise_for_status()
            rows = r.json()
            if not rows:
                break
            ids = [str(row["id"]) for row in rows]
            if not ids:
                raise RuntimeError("Missing IDs")
            r = session.delete(url + "/rest/v1/jobs", headers=headers,
                params={**params, "id": "in.(" + ",".join(ids) + ")"}, timeout=30)
            r.raise_for_status()
            deleted = r.json()
            if not deleted:
                raise RuntimeError("No rows deleted; stopping")
            count += len(deleted)
        print(f"Expired Vacancy cleanup: {count} deleted; India date={today}")
        return 0
    except Exception as exc:
        print("Cleanup failed:", str(exc)[:500])
        return 1

if __name__ == "__main__":
    sys.exit(main())
