#!/usr/bin/env python3
"""Read-only SarkariToday article-detail extraction test. No database access."""
import json, re, time
from urllib.parse import urljoin, urlparse
import requests
from bs4 import BeautifulSoup

ARTICLES=[
 "https://sarkaritoday.com/armed-forces-afms-ssc-medical-officer-2026/",
 "https://sarkaritoday.com/supreme-court-spa-2026/",
 "https://sarkaritoday.com/bihar-vidhan-sabha-office-attendant-2026/",
 "https://sarkaritoday.com/railway-rrc-nr-apprentice-2026/",
 "https://sarkaritoday.com/dsssb-mts-je-2026/",
 "https://sarkaritoday.com/upsssc-junior-engineer-je-mechanical-2026/",
 "https://sarkaritoday.com/uppsc-ro-aro-oct26/",
 "https://sarkaritoday.com/rrb-ntpc-inter-level-07-2026/",
]
UA="SarkariJobAlertReadOnlyProbe/1.0 (+https://github.com/alsalehtravels85-pixel/SarkariJobAlert)"
def official(url):
 h=(urlparse(url).hostname or "").lower().rstrip(".")
 return h.endswith((".gov.in",".nic.in",".gov")) or h in {"upsc.gov.in","ssc.gov.in","ibps.in","indiapost.gov.in","drdo.gov.in","isro.gov.in","sci.gov.in","rrbapply.gov.in"}
def tidy(s): return re.sub(r"\s+"," ",s or "").strip()
def pick(text, patterns, limit=300):
 for p in patterns:
  m=re.search(p,text,re.I)
  if m:
   v=tidy(m.group(1))
   if 2 <= len(v) <= limit: return v
 return None
session=requests.Session()
session.headers.update({"User-Agent":UA,"Accept":"text/html,application/xhtml+xml"})
report={"mode":"read-only","policy":"SarkariToday facts are draft-only unless independently confirmed on an official source","articles":[]}
for url in ARTICLES:
 item={"article_url":url}
 try:
  r=session.get(url,timeout=(12,30),allow_redirects=True)
  item["http_status"]=r.status_code
  if not r.ok or (urlparse(r.url).hostname or "").lower() not in {"sarkaritoday.com","www.sarkaritoday.com"}:
   item["error"]="article unavailable or redirected outside SarkariToday"
   report["articles"].append(item); continue
  soup=BeautifulSoup(r.content,"html.parser")
  for node in soup.select("script,style,nav,footer,header,aside,.advertisement,.ads,.breadcrumb"): node.decompose()
  root=soup.select_one("article") or soup.select_one("main") or soup.body or soup
  title=(soup.select_one("h1") or soup.title)
  item["title"]=tidy(title.get_text(" ",strip=True))[:240] if title else ""
  rows=[]
  for tr in root.select("tr"):
   cells=[tidy(x.get_text(" ",strip=True)) for x in tr.select("th,td")]
   if len(cells)>=2 and any(cells): rows.append({"label":cells[0][:100],"value":" | ".join(cells[1:])[:400]})
  text=tidy(root.get_text(" ",strip=True))
  item["content_chars"]=len(text)
  item["table_rows"]=rows[:60]
  # Extract only explicit labelled statements; do not infer values from nearby numbers.
  item["candidate_fields"]={
   "vacancies":pick(text,[r"(?:total\s+)?vacanc(?:y|ies|y\s+of\s+posts)\s*[:：-]\s*([^.;]{1,80})",r"(?:total\s+)?posts?\s*[:：-]\s*([0-9,]+)"]),
   "last_date":pick(text,[r"(?:last date(?: to apply)?|closing date|application last date)\s*[:：-]\s*([^.;]{3,80})"]),
   "notification_date":pick(text,[r"(?:notification date|date of notification|published on)\s*[:：-]\s*([^.;]{3,80})"]),
   "qualification":pick(text,[r"(?:qualification|educational qualification|eligibility)\s*[:：-]\s*(.{12,260}?)(?=\s+(?:age limit|application fee|selection process|important dates)\b|$)",r"(?:education qualification)\s*[:：-]\s*(.{12,260})"]),
   "age_limit":pick(text,[r"(?:age limit|age criteria)\s*[:：-]\s*([^.;]{3,120})"]),
   "fees":pick(text,[r"(?:application fee|exam fee|registration fee)\s*[:：-]\s*([^.;]{3,120})"]),
   "selection_process":pick(text,[r"(?:selection process|mode of selection)\s*[:：-]\s*([^.;]{3,160})"]),
  }
  links=[]; seen=set()
  for a in root.select("a[href]"):
   u=urljoin(r.url,a.get("href",""))
   if official(u) and u not in seen:
    seen.add(u); links.append({"label":tidy(a.get_text(" ",strip=True))[:100],"url":u})
  item["official_links"]=links[:25]
  item["text_sample"]=text[:1800]
 except Exception as e: item["error"]=str(e)[:240]
 report["articles"].append(item); time.sleep(1)
print(json.dumps(report,ensure_ascii=False,indent=2))
