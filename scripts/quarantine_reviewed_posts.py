#!/usr/bin/env python3
"""Move a small, explicitly reviewed set of weak/duplicate/stale posts to Draft.

Backs up the current published rows first. No permanent deletes.
"""
import json, os
from pathlib import Path
import requests

DB=os.environ["SUPABASE_URL"].rstrip("/")
KEY=os.environ["SUPABASE_SERVICE_ROLE_KEY"]
REVIEW={
 "67a1cefb-d93e-44f8-bad5-8102e96c2c1e":"duplicate of UPESSC Principal Recruitment 2026 (1475 posts)",
 "5aa144fd-17f2-4f10-87a5-f1adc76d9e82":"missing official apply-online URL; description uses generic placeholder details",
 "d324cf49-f46c-4e3b-8331-38f859c0e420":"generic India Post recruitments listing; not a complete individual vacancy article",
 "da662013-5119-4845-889f-163a4ad830b1":"admit-card post links only to recruitment homepage, not a confirmed hall-ticket download page",
 "216f2542-9577-4b1c-b478-e2602931e415":"notification URL is third-party-hosted; official RRB notification not confirmed",
 "eab8de83-cdb7-4c26-8e29-ef8a6c5c8a26":"exam date has passed; verify current result availability before republishing",
 "f1cdb1ec-8598-494b-b1c3-0ba6030c426c":"official UPSC archive does not confirm the claimed result",
 "edcf441a-e85f-4737-8bfb-19ff02b21141":"admit-card availability not confirmed on official AIIMS exam portal",
 "b0ade0ff-7394-4ad7-ae2d-0e373eee71d5":"admit-card download availability not confirmed for this session",
 "48178d2a-d322-4979-9f5c-e3c5f45503e0":"exam session timing/status needs current confirmation before public display",
 "8849230e-10b7-47c9-8368-0b4e678fe191":"specific result notice not linked; generic SBI careers page only",
 "86c61c7f-77c6-4f4e-ad26-38e3967d9b7a":"specific result PDF not confirmed; generic UPSSSC homepage only",
 "34154731-48b0-4e14-b711-3520759e2eed":"application deadline has passed",
 "64e476b4-aefc-4c5d-90d8-e01bc9b2e6b5":"application deadline has passed",
 "fbc12022-f7d7-4f1d-89e0-550e1424a500":"application deadline has passed",
 "fe45b44a-677a-42a1-9636-747f3cb4696e":"application deadline has passed",
 "7ddf059b-b02e-4ad7-8913-d7e7182a4d85":"vacancy count and key recruitment facts not confirmed from official notice",
 "d5777272-7ea6-45d0-953f-c4b96533aa69":"NICL Graduate Apprentice article links only to generic NICL and NATS homepages; specific official notice/application listing not verified",
 "f0fd898b-f454-4ba6-8d5f-6b18255ee18c":"CEN 09/2026 Isolated Categories notice could not be confirmed on official RRB recruitment notices; listed PDF is hosted by a third party",
 "dedd2681-92ca-4691-bda2-7e668dfb74a4":"Bulandshahar ECCE listing does not match verified current Sewayojan records; matching records found had earlier closing dates",
 "6a543f95-0070-42fa-a777-7cd6f8e5f6e0":"UPSSSC PET 2026 exam dates ended on 1 November 2026; admit-card page is no longer a timely update",
 "0854e0e3-437d-4999-8e7d-14de08a4ee0b":"SSC MTS Havaldar PET/PST exam date 3 November 2026 has passed; archive pending next official stage",
}
def main():
 h={"apikey":KEY,"Authorization":f"Bearer {KEY}"}
 rows=[]
 start=0
 while True:
  r=requests.get(DB+"/rest/v1/jobs",headers=h,params={"select":"*","status":"eq.published","order":"id.asc","limit":500,"offset":start},timeout=30)
  r.raise_for_status(); batch=r.json(); rows.extend(batch)
  if len(batch)<500: break
  start+=len(batch)
 out=Path("audit-output");out.mkdir(exist_ok=True)
 (out/"pre-reviewed-cleanup-backup.json").write_text(json.dumps(rows,ensure_ascii=False,indent=2),encoding="utf-8")
 targets=[x for x in rows if str(x.get("id")) in REVIEW]
 ids=[str(x["id"]) for x in targets]
 if ids:
  resp=requests.patch(DB+"/rest/v1/jobs",headers={**h,"Content-Type":"application/json","Prefer":"return=representation"},params={"id":"in.("+",".join(ids)+")","status":"eq.published"},json={"status":"draft"},timeout=35)
  resp.raise_for_status()
  updated=resp.json()
  for x in updated: print("MOVED TO DRAFT",x.get("title"),"|",REVIEW.get(str(x.get("id"))))
 print("REVIEW CLEANUP", "found",len(targets),"moved",len(updated) if ids else 0,"backup saved","permanent deletes 0")
if __name__=="__main__": main()
