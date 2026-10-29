import os
import re
import hashlib
import datetime as dt
import email.utils
import html
import urllib.parse
import xml.etree.ElementTree as ET
import requests

SUPABASE_URL = os.environ["SUPABASE_URL"].rstrip("/")
SERVICE_KEY = os.environ["SUPABASE_SERVICE_ROLE_KEY"]
NOW = dt.datetime.now(dt.timezone.utc)
HEADERS = {
    "apikey": SERVICE_KEY,
    "Authorization": f"Bearer {SERVICE_KEY}",
    "Content-Type": "application/json",
    "Prefer": "resolution=ignore-duplicates,return=minimal",
}
# Google News RSS returns headlines and source links; this workflow does not scrape full articles.
QUERIES = [
    'education India school college university exam scholarship',
    'UP Board education exam school university',
    'CBSE board exam education India',
    'scholarship admission entrance exam India',
    'शिक्षा समाचार बोर्ड परीक्षा छात्रवृत्ति भारत',
]
BASE = "https://news.google.com/rss/search?q={}&hl={}&gl=IN&ceid=IN:{}"


def clean_text(value):
    value = html.unescape(re.sub(r"<[^>]+>", " ", value or ""))
    return re.sub(r"\s+", " ", value).strip()


def parse_date(value):
    if not value:
        return None
    try:
        parsed = email.utils.parsedate_to_datetime(value)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=dt.timezone.utc)
        return parsed.astimezone(dt.timezone.utc).isoformat()
    except (TypeError, ValueError, OverflowError):
        return None


def source_from_item(item):
    source = item.find("source")
    return clean_text(source.text if source is not None else "News source")[:120]


def item_url(item):
    link = (item.findtext("link") or "").strip()
    # Google News RSS links are HTTPS and lead to the publisher story/Google News redirect.
    if link.startswith("https://"):
        return link
    return ""


def collect_items():
    session = requests.Session()
    session.headers.update({"User-Agent": "SarkariJobAlert-EducationNews/1.0 (RSS headline reader)"})
    seen = set()
    collected = []
    for query in QUERIES:
        lang = "hi-IN" if any('\u0900' <= ch <= '\u097f' for ch in query) else "en-IN"
        ceid = "IN:hi" if lang == "hi-IN" else "IN:en"
        url = BASE.format(urllib.parse.quote(query), lang, ceid.split(":")[1])
        try:
            response = session.get(url, timeout=25)
            response.raise_for_status()
            root = ET.fromstring(response.content)
        except (requests.RequestException, ET.ParseError) as exc:
            print(f"RSS source query failed (continuing): {exc}")
            continue
        for item in root.findall("./channel/item"):
            title = clean_text(item.findtext("title"))
            link = item_url(item)
            if not title or not link:
                continue
            # Skip obviously unrelated sports/entertainment items unless education/exam keywords occur.
            searchable = title.lower()
            keywords = ("education", "school", "college", "university", "exam", "board", "scholarship", "admission", "student", "शिक्षा", "परीक्षा", "छात्रवृत्ति", "प्रवेश", "बोर्ड", "विश्वविद्यालय", "स्कूल", "कॉलेज")
            if not any(word in searchable for word in keywords):
                continue
            canonical_key = hashlib.sha256((title.lower().strip() + "|" + source_from_item(item).lower()).encode("utf-8")).hexdigest()
            if canonical_key in seen:
                continue
            seen.add(canonical_key)
            published = parse_date(item.findtext("pubDate"))
            description = clean_text(item.findtext("description"))
            # Keep only a short feed excerpt; never copy a complete article.
            excerpt = description[:260].rstrip()
            if len(description) > 260:
                excerpt = excerpt.rsplit(" ", 1)[0] + "…"
            if not excerpt:
                excerpt = "Education update. Original report aur poori details ke liye source par jaayein."
            slug = "news-" + hashlib.sha256((title.lower().strip() + "|" + source_from_item(item).lower()).encode("utf-8")).hexdigest()[:32]
            collected.append({
                "slug": slug,
                "title": title[:240],
                "excerpt": excerpt,
                "content": excerpt + "\n\nYeh short feed summary hai, full article nahi. Details, context aur latest correction ke liye original publisher ki report padhein.",
                "grade": "All Students",
                "subject": "Education News",
                "article_type": "news",
                "source_url": link,
                "source_name": source_from_item(item),
                "original_published_at": published,
                "status": "published",
                "published_at": NOW.isoformat(),
                "updated_at": NOW.isoformat(),
            })
    # Sort by original publication date, newest first; unknown dates last.
    collected.sort(key=lambda x: x.get("original_published_at") or "", reverse=True)
    return collected[:30]


def main():
    if not SUPABASE_URL.startswith("https://") or not SERVICE_KEY:
        raise RuntimeError("Missing Supabase credentials. Configure GitHub Actions secrets.")
    items = collect_items()
    if not items:
        raise RuntimeError("No RSS items were collected; leaving existing feed untouched.")
    endpoint = f"{SUPABASE_URL}/rest/v1/school_articles"
    # Supabase unique slug + ignore-duplicates makes repeated daily runs idempotent.
    inserted = 0
    for item in items:
        response = requests.post(endpoint, headers=HEADERS, params={"on_conflict": "slug"}, json=item, timeout=25)
        if not response.ok:
            raise RuntimeError(f"Supabase insert failed ({response.status_code}): {response.text[:500]}")
        inserted += 1
    # Keep feed compact: retain the latest 120 news rows; no existing study-guide rows are touched.
    cutoff = (NOW - dt.timedelta(days=60)).isoformat()
    cleanup_headers = dict(HEADERS)
    cleanup_headers["Prefer"] = "return=minimal"
    cleanup = requests.delete(endpoint, headers=cleanup_headers, params={"article_type":"eq.news", "created_at":f"lt.{cutoff}"}, timeout=25)
    if not cleanup.ok:
        print(f"Old news cleanup skipped: {cleanup.status_code}")
    print(f"RSS feed processed: {inserted} current headlines; duplicates ignored by unique slug.")

if __name__ == "__main__":
    main()
