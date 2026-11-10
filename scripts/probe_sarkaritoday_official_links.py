#!/usr/bin/env python3
"""Read-only test: discover official government notice links from SarkariToday articles."""
import json, time
from urllib.parse import urljoin, urlparse
from urllib.robotparser import RobotFileParser
import requests
from bs4 import BeautifulSoup

BASE="https://sarkaritoday.com/"
UA="SarkariJobAlertReadOnlyProbe/1.0 (+https://github.com/alsalehtravels85-pixel/SarkariJobAlert)"
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
def is_official(url):
 h=(urlparse(url).hostname or "").lower().rstrip(".")
 return h.endswith(".gov.in") or h.endswith(".nic.in") or h.endswith(".gov") or h in {
  "upsc.gov.in","ssc.gov.in","ibps.in","indiapost.gov.in","drdo.gov.in","isro.gov.in",
  "sci.gov.in","barc.gov.in","esic.gov.in","aiimsexams.ac.in","rrbapply.gov.in"
 }
s=requests.Session(); s.headers.update({"User-Agent":UA,"Accept":"text/html,application/pdf,*/*;q=0.8"})
report={"mode":"read-only","robots":{},"articles":[]}
try:
 r=s.get(urljoin(BASE,"robots.txt"),timeout=(12,25))
 rp=RobotFileParser(); rp.set_url(urljoin(BASE,"robots.txt")); rp.parse(r.text.splitlines() if r.ok else [])
 report["robots"]={"status":r.status_code,"allowed":rp.can_fetch(UA,BASE)}
except Exception as e:
 report["robots"]={"error":str(e)[:200]}
if report["robots"].get("allowed"):
 for url in ARTICLES:
  item={"article":url,"status":None,"official_links":[]}
  try:
   r=s.get(url,timeout=(12,30),allow_redirects=True); item["status"]=r.status_code
   if r.ok and (urlparse(r.url).hostname or "").endswith("sarkaritoday.com"):
    soup=BeautifulSoup(r.content,"html.parser")
    item["page_title"]=soup.title.get_text(" ",strip=True)[:200] if soup.title else ""
    seen=set()
    for a in soup.select("a[href]"):
     href=urljoin(r.url,a.get("href","")); label=" ".join(a.get_text(" ",strip=True).split())
     if is_official(href) and href not in seen:
      seen.add(href); item["official_links"].append({"label":label[:120],"url":href,"looks_pdf":".pdf" in urlparse(href).path.lower()})
    item["official_links"]=item["official_links"][:30]
  except Exception as e: item["error"]=str(e)[:250]
  report["articles"].append(item); time.sleep(1)
else:
 report["skipped"]="robots.txt did not permit this crawler or could not be verified"
print(json.dumps(report,ensure_ascii=False,indent=2))
