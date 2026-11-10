#!/usr/bin/env python3
"""Read-only GitHub Actions access probe for SarkariToday.com."""
import json, time
from urllib.parse import urljoin, urlparse
from urllib.robotparser import RobotFileParser
import requests
from bs4 import BeautifulSoup

BASE="https://sarkaritoday.com/"
UA="SarkariJobAlertReadOnlyProbe/1.0 (+https://github.com/alsalehtravels85-pixel/SarkariJobAlert)"
s=requests.Session()
s.headers.update({"User-Agent":UA,"Accept":"text/html,application/xml;q=0.9,*/*;q=0.8"})
report={"site":BASE,"mode":"read-only","robots":{},"checks":[],"discovered_listing_links":[]}
try:
 r=s.get(urljoin(BASE,"robots.txt"),timeout=(12,25))
 txt=r.text if r.ok else ""
 rp=RobotFileParser(); rp.set_url(urljoin(BASE,"robots.txt")); rp.parse(txt.splitlines())
 report["robots"]={"status":r.status_code,"final_url":r.url,"bytes":len(r.content),
 "our_user_agent_allowed":rp.can_fetch(UA,BASE),
 "sitemaps":[x.split(":",1)[1].strip() for x in txt.splitlines() if x.lower().startswith("sitemap:")]}
except Exception as e: report["robots"]={"error":str(e)[:250]}
targets=[BASE,"https://sarkaritoday.com/latest-job/","https://sarkaritoday.com/latestjob/","https://sarkaritoday.com/sitemap.xml"]
if report["robots"].get("our_user_agent_allowed") is False:
 report["checks"].append({"skipped":"robots.txt disallows this crawler"})
else:
 for url in targets:
  item={"url":url}
  try:
   r=s.get(url,timeout=(12,30),allow_redirects=True)
   item.update({"status":r.status_code,"final_url":r.url,"content_type":r.headers.get("Content-Type",""),"bytes":len(r.content)})
   if r.ok and "html" in r.headers.get("Content-Type","").lower():
    soup=BeautifulSoup(r.text,"html.parser")
    for a in soup.select("a[href]"):
     href=urljoin(r.url,a.get("href","")); label=" ".join(a.get_text(" ",strip=True).split())
     host=(urlparse(href).hostname or "").lower()
     if host.endswith("sarkaritoday.com") and label and any(k in label.lower() for k in ("latest job","vacancy","recruitment","online form","government job","sarkari naukri")):
      report["discovered_listing_links"].append({"title":label[:150],"url":href})
  except Exception as e: item["error"]=str(e)[:250]
  report["checks"].append(item); time.sleep(1)
seen=set(); links=[]
for x in report["discovered_listing_links"]:
 if x["url"] not in seen: seen.add(x["url"]); links.append(x)
report["discovered_listing_links"]=links[:30]
print(json.dumps(report,ensure_ascii=False,indent=2))
