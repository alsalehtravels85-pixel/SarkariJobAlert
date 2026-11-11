#!/usr/bin/env python3
"""Generate crawlable static detail pages for published job records.

Run only in a trusted GitHub Actions environment with Supabase secrets.
Current owner-approved published set was re-audited at 16 records on 2026-11-11.
Never exposes credentials in generated HTML. Draft and expired vacancy rows
are excluded. Generated output is intended for the Cloudflare Pages upload.
"""
import html
import os
import re
import sys
from datetime import date, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import requests

BASE = "https://sarkari-jobalert.com"
DB = os.getenv("SUPABASE_URL", "").strip().rstrip("/")
KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "").strip()
OUT = Path("jobs")
TODAY = datetime.now(ZoneInfo("Asia/Kolkata")).date()
PAGE_SIZE = 1000


def esc(value):
    return html.escape(str(value or "").strip(), quote=True)


def slugify(value):
    slug = re.sub(r"[^a-z0-9]+", "-", str(value or "").lower()).strip("-")
    return slug[:70] or "update"


def iso_date(value):
    if not value:
        return ""
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00")).date().isoformat()
    except (ValueError, TypeError):
        return ""


def date_display(value):
    parsed = iso_date(value)
    if not parsed:
        return str(value or "")
    return datetime.strptime(parsed, "%Y-%m-%d").strftime("%d %B %Y")


def is_expired_vacancy(row):
    category = str(row.get("category") or "").strip().lower()
    deadline = iso_date(row.get("last_date"))
    return category in ("vacancy", "latest jobs", "jobs") and bool(deadline) and deadline < TODAY.isoformat()


def public_rows(rows):
    return [
        row for row in rows
        if row.get("status") == "published" and row.get("id") and not is_expired_vacancy(row)
    ]


def description_for(row):
    raw = re.sub(r"\s+", " ", str(row.get("description") or "")).strip()
    if not raw:
        raw = f"{row.get('title', 'यह अपडेट')} की उपलब्ध जानकारी और आधिकारिक लिंक नीचे दिए गए हैं। आवेदन या अगला कदम उठाने से पहले विभाग की मूल अधिसूचना अवश्य पढ़ें।"
    if len(raw) > 3000:
        raw = raw[:2997].rsplit(" ", 1)[0] + "..."
    return raw


def is_generic_destination(value):
    """Identify a department homepage that is not a specific result/download destination."""
    from urllib.parse import urlparse
    try:
        parsed = urlparse(str(value or ""))
        return parsed.scheme in ("http", "https") and parsed.path in ("", "/") and not parsed.query
    except ValueError:
        return True


def detail_rows(row):
    category = str(row.get("category") or "").strip().lower()
    common = [("विभाग", row.get("department"))]
    if category in ("vacancy", "latest jobs", "jobs"):
        common += [
            ("कुल पद", row.get("vacancies")),
            ("योग्यता", row.get("qualification")),
            ("अधिसूचना की तारीख", date_display(row.get("notification_date"))),
            ("आवेदन की अंतिम तारीख", date_display(row.get("last_date"))),
            ("आवेदन शुल्क", row.get("fees")),
            ("आयु सीमा", row.get("age_limit")),
            ("चयन प्रक्रिया", row.get("selection_process")),
        ]
        links = [("आधिकारिक अधिसूचना", row.get("notification_url")), ("ऑनलाइन आवेदन", row.get("apply_url"))]
    elif category in ("admit card", "admitcard"):
        common += [
            ("परीक्षा की तारीख", date_display(row.get("exam_date"))),
            ("प्रवेश पत्र जारी होने की तारीख", date_display(row.get("admit_card_release_date"))),
        ]
        links = [("प्रवेश पत्र डाउनलोड करें", row.get("admit_card_url")), ("आधिकारिक अधिसूचना", row.get("notification_url"))]
    elif category in ("result", "results"):
        common += [
            ("परिणाम की तारीख", date_display(row.get("result_date"))),
            ("परिणाम की स्थिति", row.get("result_status")),
            ("कट-ऑफ विवरण", row.get("cutoff_details") or row.get("cutoff")),
        ]
        result_url = row.get("result_url")
        # If the action field only points to a generic homepage, prefer the
        # specific official result notice/PDF already stored in notification_url.
        if is_generic_destination(result_url) and row.get("notification_url"):
            result_url = row.get("notification_url")
        merit_url = row.get("merit_list_url")
        if is_generic_destination(merit_url):
            merit_url = None
        links = [
            ("परिणाम / नोटिस देखें", result_url),
            ("मेरिट सूची", merit_url),
            ("आधिकारिक अधिसूचना", row.get("notification_url")),
        ]
    else:
        common += [
            ("कुल पद", row.get("vacancies")),
            ("योग्यता", row.get("qualification")),
            ("महत्वपूर्ण तारीख", date_display(row.get("last_date"))),
        ]
        links = [("आधिकारिक जानकारी", row.get("notification_url")), ("आवेदन / आगे बढ़ें", row.get("apply_url"))]
    rows = [(label, value) for label, value in common if value not in (None, "")]
    return rows, [(label, url) for label, url in links if url and str(url).startswith("https://")]


def render_page(row):
    title = str(row.get("title") or "सरकारी अपडेट").strip()
    category = str(row.get("category") or "Update").strip()
    description = description_for(row)
    canonical = f"{BASE}/jobs/{slugify(title)}-{esc(row['id'])}.html"
    rows, links = detail_rows(row)
    table = "\n".join(
        f"<tr><th>{esc(label)}</th><td>{esc(value)}</td></tr>" for label, value in rows
    )
    link_html = "\n".join(
        f'<a class="action" href="{esc(url)}" target="_blank" rel="noopener noreferrer">{esc(label)} ↗</a>'
        for label, url in links
    )
    return f"""<!doctype html>
<html lang="hi">
<head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="robots" content="index,follow,max-image-preview:large">
<title>{esc(title)} | Sarkari Job Alert</title>
<meta name="description" content="{esc(description[:155])}">
<link rel="canonical" href="{canonical}">
<meta property="og:type" content="article"><meta property="og:site_name" content="Sarkari Job Alert">
<meta property="og:title" content="{esc(title)} | Sarkari Job Alert">
<meta property="og:description" content="{esc(description[:200])}">
<meta property="og:url" content="{canonical}">
<meta name="twitter:card" content="summary"><meta name="twitter:title" content="{esc(title)}">
<meta name="twitter:description" content="{esc(description[:200])}">
<style>
*{{box-sizing:border-box}}body{{margin:0;background:#f4f7fb;color:#172033;font:16px/1.7 system-ui,-apple-system,Segoe UI,sans-serif}}
header{{background:linear-gradient(120deg,#063b35,#087d63);color:#fff;padding:20px 16px}}.wrap{{max-width:900px;margin:auto;padding:0 16px}}
.brand{{font-weight:800;font-size:19px}}.brand span{{color:#a7f3d0}}main{{padding:28px 0 40px}}
article{{background:#fff;border:1px solid #dce7f8;border-radius:18px;padding:clamp(18px,4vw,30px);box-shadow:0 8px 28px #173a750d}}
.tag{{display:inline-block;background:#e5f0ff;color:#0954b5;border-radius:99px;padding:4px 11px;font-size:12px;font-weight:800}}
h1{{font-size:clamp(25px,5vw,36px);line-height:1.3;margin:13px 0 6px}}.dept{{color:#64748b;margin:0 0 20px}}
table{{width:100%;border-collapse:collapse;margin:18px 0}}th,td{{padding:12px 10px;border-bottom:1px solid #e5edf7;text-align:left;vertical-align:top}}th{{width:36%;color:#40536f;font-size:14px}}td{{overflow-wrap:anywhere}}
h2{{font-size:20px;margin-top:26px}}.description{{white-space:pre-line;overflow-wrap:anywhere;color:#334155}}
.actions{{display:flex;flex-wrap:wrap;gap:10px;margin-top:20px}}.action{{display:inline-block;background:#075bd9;color:white;text-decoration:none;padding:10px 15px;border-radius:10px;font-weight:800;font-size:14px}}
.note{{background:#f1f7ff;border:1px solid #d8e8ff;border-radius:12px;padding:13px;color:#40536f;font-size:13px;margin-top:20px}}
footer{{padding:20px 16px;text-align:center;color:#64748b;font-size:13px}}footer a{{color:#075bd9;margin:0 7px}}
@media(max-width:560px){{th{{width:40%}}th,td{{padding:10px 7px;font-size:13px}}}}
</style>
</head>
<body>
<header><div class="wrap"><a class="brand" href="{BASE}/" style="color:white;text-decoration:none">Sarkari <span>Job Alert</span></a></div></header>
<main class="wrap"><article>
<span class="tag">{esc(category)}</span><h1>{esc(title)}</h1>
<p class="dept">{esc(row.get('department') or 'विभाग की जानकारी उपलब्ध नहीं')}</p>
<table><tbody>{table}</tbody></table>
<h2>पूरी जानकारी</h2><div class="description">{esc(description)}</div>
<div class="actions">{link_html}</div>
<div class="note">महत्वपूर्ण: आवेदन करने या परिणाम संबंधी अगला कदम उठाने से पहले संबंधित विभाग की आधिकारिक वेबसाइट और मूल अधिसूचना से सभी तारीखों, पात्रता, शुल्क तथा लिंक की पुष्टि करें। Sarkari Job Alert एक स्वतंत्र सूचना वेबसाइट है, सरकारी विभाग नहीं।</div>
</article></main>
<footer><a href="{BASE}/">Home</a><a href="{BASE}/about.html">About</a><a href="{BASE}/contact.html">Contact</a><a href="{BASE}/privacy.html">Privacy</a><a href="{BASE}/disclaimer.html">Disclaimer</a><p>© Sarkari Job Alert</p></footer>
</body></html>"""


def fetch_rows(session):
    headers = {"apikey": KEY, "Authorization": f"Bearer {KEY}", "Accept": "application/json"}
    result, offset = [], 0
    while True:
        params = {
            "select": "*", "status": "eq.published",
            "order": "updated_at.desc.nullslast,created_at.desc",
            "limit": PAGE_SIZE, "offset": offset,
        }
        response = session.get(f"{DB}/rest/v1/jobs", headers=headers, params=params, timeout=(12, 35))
        response.raise_for_status()
        batch = response.json()
        if not isinstance(batch, list):
            raise RuntimeError("Unexpected Supabase jobs response")
        result.extend(batch)
        if len(batch) < PAGE_SIZE:
            return result
        offset += PAGE_SIZE


def generate(rows, output=OUT):
    selected = public_rows(rows)
    output.mkdir(parents=True, exist_ok=True)
    expected = set()
    for row in selected:
        filename = f"{slugify(row.get('title'))}-{row['id']}.html"
        expected.add(filename)
        (output / filename).write_text(render_page(row), encoding="utf-8")
    # Remove stale generated HTML only; do not touch non-HTML assets or other files.
    for path in output.glob("*.html"):
        if path.name not in expected:
            path.unlink()
    print(f"JOB PAGES GENERATED | published eligible records: {len(selected)} | output: {output}")
    return selected


def main():
    if not DB.startswith("https://") or not KEY:
        print("ERROR: SUPABASE_URL / SUPABASE_SERVICE_ROLE_KEY missing")
        return 2
    rows = fetch_rows(requests.Session())
    generate(rows)
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:
        print("JOB PAGE GENERATION ERROR:", str(exc)[:500])
        sys.exit(1)
