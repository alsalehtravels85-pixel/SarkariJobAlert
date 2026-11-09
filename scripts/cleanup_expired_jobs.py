#!/usr/bin/env python3
"""Delete only scanner-managed published Latest Jobs rows 30 days after last_date."""
import os, sys
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import requests

DB = os.getenv("SUPABASE_URL", "").strip().rstrip("/")
KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "").strip()
MARKER = "#sja-auto-scanner-managed"
HEADERS = {"apikey": KEY, "Authorization": "Bearer " + KEY, "Content-Type": "application/json", "Prefer": "return=representation"}

def main():
    if not DB.startswith("https://") or not KEY:
        print("Missing SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY GitHub secret")
        return 2
    today = datetime.now(ZoneInfo("Asia/Kolkata")).date()
    cutoff = (today - timedelta(days=30)).isoformat()
    session = requests.Session()
    params = {"select":"id,title,last_date,source_url","category":"eq.Latest Jobs","status":"eq.published","source_url":"like.*"+MARKER+"*","last_date":"lt."+cutoff,"limit":"500"}
    try:
        response=session.get(DB+"/rest/v1/jobs",headers=HEADERS,params=params,timeout=30); response.raise_for_status()
        rows=response.json()
        if not rows:
            print(f"No scanner-managed published jobs due for deletion. India date={today}; cutoff<{cutoff}.")
            return 0
        deleted=0
        for offset in range(0,len(rows),50):
            batch=rows[offset:offset+50]
            ids=[str(row["id"]) for row in batch if row.get("id") is not None]
            if not ids: continue
            delete_params={"id":"in.("+",".join(ids)+")","category":"eq.Latest Jobs","status":"eq.published","source_url":"like.*"+MARKER+"*","last_date":"lt."+cutoff}
            result=session.delete(DB+"/rest/v1/jobs",headers=HEADERS,params=delete_params,timeout=30); result.raise_for_status()
            removed=result.json() if result.content else []
            deleted += len(removed) if isinstance(removed,list) else len(ids)
            for row in batch: print("DELETED",row.get("id"),row.get("title"),"last_date=",row.get("last_date"))
        print(f"CLEANUP REPORT | India date={today} | grace cutoff<{cutoff} | deleted={deleted}")
        return 0
    except Exception as exc:
        print("CLEANUP ERROR:",exc)
        return 1
if __name__=="__main__": sys.exit(main())
