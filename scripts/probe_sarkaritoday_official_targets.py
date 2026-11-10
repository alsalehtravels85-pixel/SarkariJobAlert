#!/usr/bin/env python3
"""Read-only test of government URLs discovered on SarkariToday articles."""
import io, json, time
from urllib.parse import urlparse
import requests
from bs4 import BeautifulSoup
from pypdf import PdfReader

URLS=[
 "https://join.afms.gov.in/",
 "https://cdnbbsr.s3waas.gov.in/s3ec0490f1f4972d133619a60c30f3559e/uploads/2026/10/2026101325.pdf",
 "https://www.sci.gov.in/recruitments/",
 "https://vidhansabha.bihar.gov.in/pdf/recruitment/2026/Advertisment/Advertisemnt%20No-02-2026%20(Office%20Attendent).pdf",
 "https://dsssb.delhi.gov.in/sites/default/files/DSSSB/circulars-orders/final_advt_06_2026_j_e_electrical_mts.pdf",
 "https://upsssc.gov.in/AllNotifications.aspx",
 "https://uppsc.up.nic.in/Default.aspx",
 "https://rrb.indianrailways.gov.in/-/image/1791999622770Final_CEN_07-2026_14.10.2026_English.pdf/examsDocuments",
 "https://www.rrbapply.gov.in/#/auth/landing",
]
UA="SarkariJobAlertReadOnlyProbe/1.0 (+https://github.com/alsalehtravels85-pixel/SarkariJobAlert)"
s=requests.Session(); s.headers.update({"User-Agent":UA,"Accept":"text/html,application/pdf,*/*;q=0.8"})
report={"mode":"read-only","checks":[]}
for url in URLS:
 item={"url":url}
 try:
  r=s.get(url,timeout=(12,35),allow_redirects=True)
  item.update({"status":r.status_code,"final_url":r.url,"content_type":r.headers.get("Content-Type",""),"bytes":len(r.content)})
  if r.ok and (r.content[:4]==b"%PDF" or "pdf" in r.headers.get("Content-Type","").lower()):
   try:
    reader=PdfReader(io.BytesIO(r.content))
    text=" ".join(p.extract_text() or "" for p in reader.pages[:8])
    item.update({"pdf_pages":len(reader.pages),"extractable_text_chars":len(text),"text_sample": " ".join(text.split())[:500]})
   except Exception as e: item["pdf_parse_error"]=str(e)[:250]
  elif r.ok and "html" in r.headers.get("Content-Type","").lower():
   soup=BeautifulSoup(r.content,"html.parser")
   item["page_title"]=soup.title.get_text(" ",strip=True)[:180] if soup.title else ""
 except Exception as e: item["error"]=str(e)[:250]
 report["checks"].append(item); time.sleep(1)
print(json.dumps(report,ensure_ascii=False,indent=2))
