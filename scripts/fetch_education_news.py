import os, re, hashlib, datetime as dt, email.utils, html, urllib.parse, xml.etree.ElementTree as ET
from zoneinfo import ZoneInfo
import requests
from bs4 import BeautifulSoup

SUPABASE_URL=os.environ["SUPABASE_URL"].rstrip("/")
SERVICE_KEY=os.environ["SUPABASE_SERVICE_ROLE_KEY"]
GEMINI_API_KEY=os.getenv("GEMINI_API_KEY","").strip()
GEMINI_MODEL=os.getenv("GEMINI_MODEL","gemini-3.8-flash").strip()
NOW=dt.datetime.now(dt.timezone.utc)
TABLE=f"{SUPABASE_URL}/rest/v1/school_articles"
HEADERS={"apikey":SERVICE_KEY,"Authorization":f"Bearer {SERVICE_KEY}","Content-Type":"application/json"}
QUERIES=["India education school college university examination scholarship admission","Uttar Pradesh board school examination education scholarship","CBSE education examination students India","भारत शिक्षा समाचार परीक्षा छात्रवृत्ति प्रवेश विश्वविद्यालय"]
RSS="https://news.google.com/rss/search?q={}&hl={}&gl=IN&ceid=IN:{}"
UA="Mozilla/5.0 (compatible; SarkariJobAlertEducationNews/2.0; +https://sarkari-jobalert.com)"
MIN_SOURCE_CHARS=1200
MIN_WORDS=450
MAX_DAILY=1

def clean(s):
    return re.sub(r"\s+"," ",html.unescape(re.sub(r"<[^>]+>"," ",s or ""))).strip()

def pubdate(s):
    try:
        d=email.utils.parsedate_to_datetime(s)
        if d.tzinfo is None: d=d.replace(tzinfo=dt.timezone.utc)
        return d.astimezone(dt.timezone.utc).isoformat()
    except (TypeError,ValueError,OverflowError): return None

def collect():
    sess=requests.Session(); sess.headers.update({"User-Agent":UA})
    out=[]; seen=set()
    for q in QUERIES:
        hi=any("\u0900"<=ch<="\u097f" for ch in q)
        lang="hi-IN" if hi else "en-IN"; ceid="hi" if hi else "en"
        try:
            res=sess.get(RSS.format(urllib.parse.quote(q),lang,ceid),timeout=25); res.raise_for_status()
            root=ET.fromstring(res.content)
        except (requests.RequestException,ET.ParseError) as e:
            print(f"RSS query skipped: {e}"); continue
        for it in root.findall("./channel/item"):
            title=clean(it.findtext("title")); link=(it.findtext("link") or "").strip()
            src=clean(it.find("source").text if it.find("source") is not None else "Original publisher")[:120]
            if not title or not link.startswith("https://"): continue
            key=hashlib.sha256((title.lower()+"|"+src.lower()).encode()).hexdigest()
            if key in seen: continue
            seen.add(key); published=pubdate(it.findtext("pubDate"))
            if published and (NOW-dt.datetime.fromisoformat(published)).total_seconds()>72*3600: continue
            out.append({"title":title[:240],"url":link,"source":src,"published":published,"key":key})
    out.sort(key=lambda x:x.get("published") or "",reverse=True)
    return out

def extract(url):
    r=requests.get(url,headers={"User-Agent":UA},timeout=25,allow_redirects=True); r.raise_for_status()
    final=r.url
    if not final.startswith("https://"): raise ValueError("Non-HTTPS publisher URL")
    soup=BeautifulSoup(r.text,"html.parser")
    for n in soup(["script","style","noscript","svg","nav","footer","header","aside","form"]): n.decompose()
    for n in soup.select(".advertisement,.ads,.related,.social-share,[aria-hidden='true']"): n.decompose()
    nodes=soup.select("article,main,[itemprop='articleBody']")
    body=max((clean(n.get_text(" ",strip=True)) for n in nodes),key=len,default="")
    if len(body)<MIN_SOURCE_CHARS:
        body=" ".join(clean(n.get_text(" ",strip=True)) for n in soup.find_all("p") if len(clean(n.get_text(" ",strip=True)))>45)
    if len(body)<MIN_SOURCE_CHARS: raise ValueError(f"Publisher text too short ({len(body)} chars)")
    return final,body[:18000]

def write_article(item,url,source):
    if not GEMINI_API_KEY: raise RuntimeError("GEMINI_API_KEY secret missing")
    prompt=f"""
आप SarkariJobAlert के शिक्षा समाचार संपादक हैं। दिए गए मूल प्रकाशक स्रोत से एक मौलिक, उपयोगी हिंदी समाचार लेख लिखें।
नियम:
- केवल SOURCE TEXT में स्पष्ट तथ्यों का उपयोग करें। तारीख, आंकड़े, नाम, नियम, पात्रता, परिणाम, समय-सीमा या उद्धरण न गढ़ें।
- मूल लेख के वाक्य कॉपी न करें; तथ्य अपने शब्दों में समझाएँ। लंबे उद्धरण न दें।
- स्रोत में जानकारी अधूरी/विरोधाभासी हो तो सीमा स्पष्ट करें; अनुमान न लगाएँ।
- खबर का विद्यार्थियों पर व्यावहारिक असर और पाठक को अगला सही कदम बताएं, पर केवल समर्थित जानकारी के आधार पर।
- भर्ती/परीक्षा की खबर को आधिकारिक घोषणा न कहें जब तक स्रोत इसकी पुष्टि न करे।
- 550-850 हिंदी शब्द, छोटे पैराग्राफ और 4-6 उपयोगी उपशीर्षक। स्रोत अपर्याप्त हो तो केवल INSUFFICIENT_SOURCE लिखें।
- क्लिकबेट, keyword stuffing, filler, दोहराव और सामान्य सलाह नहीं। शुरुआत में संक्षिप्त सार और अंत में स्रोत/प्रकाशक लिंक दें।
- मूल प्रकाशन तारीख केवल उपलब्ध होने पर दें। केवल लेख लौटाएँ, JSON या टिप्पणी नहीं।
शीर्षक: {item["title"]}
प्रकाशक: {item["source"]}
मूल प्रकाशन तिथि: {item.get("published") or "उपलब्ध नहीं"}
मूल URL: {url}
SOURCE TEXT:
{source}
"""
    api=f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent"
    r=requests.post(api,headers={"x-goog-api-key":GEMINI_API_KEY,"Content-Type":"application/json"},json={"contents":[{"role":"user","parts":[{"text":prompt}]}],"generationConfig":{"temperature":0.35,"topP":0.85,"maxOutputTokens":7000}},timeout=100)
    r.raise_for_status(); data=r.json()
    parts=((data.get("candidates") or [{}])[0].get("content") or {}).get("parts") or []
    article="\n".join(x.get("text","") for x in parts if x.get("text")).strip()
    return "" if article=="INSUFFICIENT_SOURCE" else article

def words(s):
    return len(re.findall(r"[\w\u0900-\u097F]+",s,flags=re.UNICODE))

def exists(slug):
    r=requests.get(TABLE,headers=HEADERS,params={"slug":f"eq.{slug}","select":"id,status"},timeout=20)
    r.raise_for_status(); return bool(r.json())

def cleanup_old_news():
    # Delete only Education News rows older than 30 days; never touch study guides or job posts.
    cutoff=(NOW-dt.timedelta(days=30)).isoformat()
    params={"article_type":"eq.news","created_at":f"lt.{cutoff}","select":"id"}
    h={**HEADERS,"Prefer":"return=representation"}
    r=requests.delete(TABLE,headers=h,params=params,timeout=30)
    r.raise_for_status()
    deleted=r.json() if r.content else []
    print(f"30-day Education News cleanup: deleted {len(deleted)} old news rows.",flush=True)

def published_news_today():
    local_today=dt.datetime.now(ZoneInfo("Asia/Kolkata")).date()
    midnight=dt.datetime.combine(local_today,dt.time.min,tzinfo=ZoneInfo("Asia/Kolkata")).astimezone(dt.timezone.utc)
    params={"article_type":"eq.news","status":"eq.published","published_at":f"gte.{midnight.isoformat()}","select":"id","limit":"2"}
    r=requests.get(TABLE,headers=HEADERS,params=params,timeout=25)
    r.raise_for_status()
    return len(r.json())

def qualifies_news_article(title, article, url, source):
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme != "https" or not parsed.netloc or parsed.hostname == "news.google.com":
        return False, "Original publisher URL not resolved"
    if not title.strip() or not source.strip():
        return False, "Missing title or source"
    if not MIN_WORDS <= words(article) <= 1100:
        return False, "Article word count outside quality limits"
    if len(re.findall(r"(?m)^#{1,3}\s+\S", article)) < 4:
        return False, "Insufficient article structure"
    if url not in article:
        return False, "Publisher source link missing"
    if "INSUFFICIENT_SOURCE" in article:
        return False, "Insufficient source"
    return True, "qualified"

def main():
    if not SUPABASE_URL.startswith("https://") or not SERVICE_KEY: raise RuntimeError("Missing Supabase credentials")
    if not GEMINI_API_KEY: raise RuntimeError("GEMINI_API_KEY GitHub Secret missing")
    # Preserve published articles; no automatic deletion.

    already_published=published_news_today()
    if already_published >= MAX_DAILY:
        print(f"Daily limit reached: {already_published} Education News article(s) already published today. No more will be created.",flush=True)
        return
    created=skipped=0
    for item in collect():
        if created>=MAX_DAILY: break
        slug="edu-news-"+item["key"][:32]
        if exists(slug): continue
        try:
            url,source=extract(item["url"])
            article=write_article(item,url,source); count=words(article)
            ok, reason = qualifies_news_article(item['title'], article, url, item['source'])
            if not ok:
                print(f"Skipped article failing quality gate: {item['title']} — {reason} ({count} words)"); skipped+=1; continue
            excerpt=re.sub(r"[#*_>]+","",article)
            excerpt=re.sub(r"\s+"," ",excerpt).strip()[:420]
            payload={"slug":slug,"title":item["title"],"excerpt":excerpt,"content":article,"grade":"All Students","subject":"Education News","article_type":"news","source_url":url,"source_name":item["source"],"original_published_at":item.get("published"),"status":"published","published_at":NOW.isoformat(),"updated_at":NOW.isoformat()}
            h={**HEADERS,"Prefer":"resolution=ignore-duplicates,return=representation"}
            r=requests.post(TABLE,headers=h,params={"on_conflict":"slug"},json=payload,timeout=35)
            if not r.ok: raise RuntimeError(f"Supabase HTTP {r.status_code}: {r.text[:400]}")
            inserted=r.json() if r.content else []
            if not inserted or inserted[0].get("status") != "published":
                raise RuntimeError("Supabase did not confirm a published row; refusing to count this as published.")
            created+=1; print(f"Published original education article: {item['title']} ({count} words)")
        except (requests.RequestException,ValueError,RuntimeError) as e:
            skipped+=1; print(f"Skipped safely: {item['title']} — {e}")
    print(f"Education News complete: {created} published; {skipped} skipped. Existing records untouched.")
    if created == 0:
        raise RuntimeError("No verified education article was published; inspect source resolution and quality gates.")
if __name__=="__main__": main()
