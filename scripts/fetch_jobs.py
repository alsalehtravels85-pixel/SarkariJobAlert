#!/usr/bin/env python3
"""Official-source notice collector for SarkariJobAlert. Saves candidates as drafts."""
import os, re, sys, time
from datetime import datetime, timezone
from urllib.parse import urljoin, urlparse, urldefrag
import requests
from bs4 import BeautifulSoup
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from supabase import create_client
try:
    import feedparser
except ImportError:
    feedparser = None

SUPABASE_URL = os.getenv('SUPABASE_URL', '').strip()
SUPABASE_KEY = os.getenv('SUPABASE_SERVICE_ROLE_KEY', '').strip()
if not SUPABASE_URL or not SUPABASE_KEY:
    raise RuntimeError('Missing GitHub Secrets: SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY')
db = create_client(SUPABASE_URL, SUPABASE_KEY)

ALLOWED_CATEGORIES = {'Latest Jobs', 'Admit Card', 'Results', 'Answer Key', 'Admission', 'Syllabus'}
SOURCES = [
 {'name':'Staff Selection Commission','urls':['https://ssc.gov.in/'],'hosts':['ssc.gov.in']},
 {'name':'UPSC','urls':['https://upsc.gov.in/','https://www.upsc.gov.in/','https://upsc.gov.in/recruitment/recruitment-advertisement'],'hosts':['upsc.gov.in']},
 {'name':'IBPS','urls':['https://www.ibps.in/','https://www.ibps.in/index.php/recruitment/','https://www.ibps.in/index.php/crp-updates/'],'hosts':['ibps.in']},
 {'name':'Railway Recruitment Boards','urls':['https://indianrailways.gov.in/','https://www.rrbcdg.gov.in/employment-notices.php'],'hosts':['indianrailways.gov.in','rrbcdg.gov.in']},
 {'name':'State Bank of India Careers','urls':['https://sbi.co.in/web/careers','https://bank.sbi/web/careers'],'hosts':['sbi.co.in','bank.sbi']},
]
CATEGORY_RULES = [
 ('Results', re.compile(r'\b(result|results|merit list|score ?card|final result)\b', re.I)),
 ('Admit Card', re.compile(r'\b(admit card|hall ticket|call letter|e-admit card)\b', re.I)),
 ('Answer Key', re.compile(r'\b(answer key|answer keys|provisional answer key)\b', re.I)),
 ('Syllabus', re.compile(r'\b(syllabus|exam pattern)\b', re.I)),
 ('Admission', re.compile(r'\b(admission|entrance examination|entrance application)\b', re.I)),
]
JOB_PATTERN = re.compile(r'\b(recruitment|vacanc(?:y|ies)|apply online|online application|employment notice|recruitment notice|recruitment advertisement|invited applications|invites applications|notification for|selection post|combined graduate level|combined higher secondary|junior engineer|assistant loco pilot|station master|rrb ntpc|group[- ]?d|probationary officer|po/mt|crp[- ]?(rrb|spl|clerk)|apprentice|trainee|constable|sub inspector|officer recruitment)\b', re.I)
EXCLUDE = re.compile(r'\b(tender|procurement|auction|vendor registration|press release|annual report|investor relations|old notices|previous notices|archive|archives|recruitment results archive)\b', re.I)
GENERIC = {'home','careers','career','recruitment','view all','read more','click here','download','notice','notices','results','latest updates'}

def make_session():
    s = requests.Session()
    retry = Retry(total=2, connect=2, read=2, backoff_factor=.7, status_forcelist=(429,500,502,503,504), allowed_methods=frozenset(['GET']))
    adapter = HTTPAdapter(max_retries=retry)
    s.mount('https://', adapter); s.mount('http://', adapter)
    s.headers.update({'User-Agent':'Mozilla/5.0 (compatible; SarkariJobAlertNoticeChecker/2.0)','Accept':'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8','Accept-Language':'en-IN,en;q=0.8'})
    return s
SESSION = make_session()

def official(url, hosts):
    try:
        p = urlparse(url); host = (p.hostname or '').lower().rstrip('.')
        return p.scheme.lower() == 'https' and bool(host) and any(host == h or host.endswith('.'+h) for h in hosts)
    except Exception: return False

def clean(text): return ' '.join((text or '').split()).strip(' \t\r\n-–—|:·')

def classify(title):
    for cat, pattern in CATEGORY_RULES:
        if pattern.search(title): return cat
    if JOB_PATTERN.search(title) and not EXCLUDE.search(title): return 'Latest Jobs'
    return None

def add_candidate(found, title, link, source):
    title, link = clean(title), urldefrag(link)[0].strip()
    if len(title) < 8 or len(title) > 400 or title.lower() in GENERIC or EXCLUDE.search(title): return
    if not official(link, source['hosts']): return
    if re.search(r'/(archives?|archive|old-notices?)/?$', urlparse(link).path, re.I): return
    category = classify(title)
    if category not in ALLOWED_CATEGORIES: return
    found[link] = {'title':title[:250], 'department':source['name'], 'category':category,
      'notification_url':link, 'apply_url':link,
      'description':'Automatically detected candidate notice from an official source. Verify eligibility, vacancies, fees, dates and the application link in the original notice before publishing.',
      'status':'draft'}

def get_page(url, source):
    try:
        r = SESSION.get(url, timeout=(12,25), allow_redirects=True)
        if r.status_code >= 400:
            print(f'  HTTP {r.status_code}: {url}'); return None, None
        if not official(r.url, source['hosts']):
            print(f'  Skipped redirect outside official host: {r.url}'); return None, None
        return r, None
    except requests.exceptions.SSLError as e: return None, f'SSL error: {e}'
    except requests.exceptions.RequestException as e: return None, f'Connection error: {e}'

def scan_page(url, source, found, counts):
    r, error = get_page(url, source)
    if error:
        print(f'  {error}'); counts['errors'] += 1; return
    if r is None: counts['errors'] += 1; return
    if feedparser and ('xml' in r.headers.get('Content-Type','').lower() or r.text.lstrip().startswith('<?xml')):
        feed = feedparser.parse(r.content)
        if feed.entries:
            before = len(found)
            for entry in feed.entries:
                link = getattr(entry,'link','')
                if link: add_candidate(found, getattr(entry,'title',''), urljoin(r.url,link), source)
            counts['pages_ok'] += 1
            print(f'  Feed scanned: {url}; candidates: {len(found)-before}')
            return
    soup = BeautifulSoup(r.text, 'html.parser'); before = len(found)
    for a in soup.select('a[href]'):
        href = (a.get('href') or '').strip()
        if not href or href.startswith(('javascript:','mailto:','tel:')): continue
        link = urljoin(r.url, href)
        if not official(link, source['hosts']): continue
        title = clean(a.get_text(' ', strip=True))
        parent = a.find_parent(['tr','li','article'])
        nearby = clean(parent.get_text(' ', strip=True)) if parent else ''
        if len(title) < 12 and len(nearby) > len(title): title = nearby
        add_candidate(found, title, link, source)
    counts['pages_ok'] += 1
    print(f'  Page read; candidates added: {len(found)-before} ({url})')

def scan_sitemaps(source, found, counts):
    for host in source['hosts']:
        for sm in (f'https://{host}/sitemap.xml', f'https://{host}/sitemap_index.xml'):
            r, _ = get_page(sm, source)
            if r is None: continue
            if '<urlset' not in r.text[:3000] and '<sitemapindex' not in r.text[:3000]: continue
            soup = BeautifulSoup(r.text, 'xml')
            locs = [x.get_text(strip=True) for x in soup.find_all('loc')]
            if soup.find('sitemapindex'):
                locs = [u for u in locs if re.search(r'(recruit|career|notice|job|news|update)',u,re.I)][:5]
            for loc in locs[:50]:
                if official(loc,source['hosts']) and re.search(r'(recruit|career|notice|job|advertisement|vacan|result|admit|answer)',loc,re.I):
                    scan_page(loc,source,found,counts); time.sleep(.2)

def save_notice(notice, counts):
    try:
        existing = db.table('jobs').select('id').eq('notification_url',notice['notification_url']).limit(1).execute()
        if existing.data:
            counts['duplicates'] += 1; print(f"  Duplicate skipped: {notice['title']}"); return
        db.table('jobs').insert(notice).execute()
        counts['saved'] += 1; print(f"  Saved as draft [{notice['category']}]: {notice['title']}")
    except Exception as e:
        counts['save_failures'] += 1; print(f"  DATABASE SAVE FAILED [{notice['title']}]: {e}")

def main():
    counts = {'pages_ok':0,'errors':0,'duplicates':0,'saved':0,'save_failures':0}
    all_notices = {}
    print('SARKARI JOB ALERT - OFFICIAL SOURCE CHECK')
    print('Run time UTC:', datetime.now(timezone.utc).isoformat())
    print('Detected notices are saved as DRAFT, not auto-published.')
    for source in SOURCES:
        print(f"\nChecking: {source['name']}"); found = {}
        for url in source['urls']:
            scan_page(url,source,found,counts); time.sleep(.4)
        if not found: scan_sitemaps(source,found,counts)
        all_notices.update(found)
        print(f'  Total candidates for source: {len(found)}'); time.sleep(.5)
    for notice in all_notices.values(): save_notice(notice,counts)
    print('\n================================')
    print('SARKARI JOB ALERT - CHECK REPORT')
    print(f"Pages successfully read: {counts['pages_ok']}")
    print(f"Fetch errors: {counts['errors']}")
    print(f'Candidate notices: {len(all_notices)}')
    print(f"New notices saved as drafts: {counts['saved']}")
    print(f"Duplicates skipped: {counts['duplicates']}")
    print(f"Database save failures: {counts['save_failures']}")
    print('================================')
    if counts['pages_ok'] == 0 or counts['save_failures'] > 0: sys.exit(1)

if __name__ == '__main__': main()
