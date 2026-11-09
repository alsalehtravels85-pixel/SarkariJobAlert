#!/usr/bin/env python3
"""Conservative official-source recruitment scanner for SarkariJobAlert."""
import os, re, io, sys, time
from datetime import datetime
from zoneinfo import ZoneInfo
from urllib.parse import urljoin, urlparse, urldefrag
import requests
from bs4 import BeautifulSoup
from pypdf import PdfReader

DB=os.getenv('SUPABASE_URL','').strip().rstrip('/')
KEY=os.getenv('SUPABASE_SERVICE_ROLE_KEY','').strip()
HEAD={'User-Agent':'SarkariJobAlertOfficialScanner/2.0 (+https://github.com/alsalehtravels85-pixel/SarkariJobAlert)','Accept':'text/html,application/pdf,*/*'}
TIMEOUT=(20,45)
EXACT={'upsc.gov.in','upsconline.nic.in','ssc.gov.in','upsssc.gov.in','uppsc.up.nic.in','ibps.in','sbi.co.in','indiapost.gov.in','opportunities.rbi.org.in','drdo.gov.in','isro.gov.in','indianrailways.gov.in','rrbapply.gov.in','uppbpb.gov.in','nabard.org','sebi.gov.in','tnpsc.gov.in','keralapsc.gov.in','rpsc.rajasthan.gov.in','bpsc.bihar.gov.in','mppsc.mp.gov.in','ncs.gov.in','employmentnews.gov.in'}
SOURCES=[
('UPSSSC','https://upsssc.gov.in/'),('UPPSC','https://uppsc.up.nic.in/'),('UP Police','https://uppbpb.gov.in/'),
('UP NHM','https://upnrhm.gov.in/'),('UP Government Jobs - NCS','https://www.ncs.gov.in/pages/govt-job-vacancies.aspx'),
('UPSC','https://www.upsc.gov.in/recruitment/recruitment-advertisement'),('SSC','https://ssc.gov.in/'),
('IBPS','https://www.ibps.in/index.php/recruitment/'),
('India Post','https://www.indiapost.gov.in/vacancies'),('RBI','https://opportunities.rbi.org.in/scripts/vacancies.aspx'),
('SBI Careers','https://sbi.co.in/web/careers/current-openings'),('DRDO','https://www.drdo.gov.in/drdo/careers'),
('ISRO','https://www.isro.gov.in/Careers.html'),('Indian Railways','https://indianrailways.gov.in/railwayboard/'),
('NABARD','https://www.nabard.org/careers-notices1.aspx'),
('SEBI','https://www.sebi.gov.in/sebiweb/about/AboutAction.do?doVacancies=yes'),
('TNPSC','https://www.tnpsc.gov.in/'),('Kerala PSC','https://www.keralapsc.gov.in/'),
('RPSC','https://rpsc.rajasthan.gov.in/'),('BPSC','https://bpsc.bihar.gov.in/'),('MPPSC','https://mppsc.mp.gov.in/')]
HINT=('recruitment','vacancy','vacancies','applications invited','engagement','advertisement no','advt no','direct recruitment','posts of','post of','apprentice','probationary officer','junior associate','constable','group c','group d','staff nurse','assistant professor','non faculty','technical assistant','officer','clerk','driver')
BAD=('result','answer key','admit card','call letter','interview schedule','interview notice','interview','shortlisted candidates','shortlist','selected candidates','selection panel','selection list','date of conducting','skill test date','marks','score card','corrigendum','extension of last date','extension of time','citizen engagement','syllabus','exam calendar','tender','deputation','transfer','revised')

def txt(x): return re.sub(r'\s+',' ',x or '').strip()
def host(u): return (urlparse(u).hostname or '').lower().rstrip('.')
def official(u):
 h=host(u); return h in EXACT or h.endswith('.gov.in') or h.endswith('.nic.in') or h.endswith('.gov')
def safe(u,base):
 u=urldefrag(urljoin(base,(u or '').strip()))[0]
 return u if urlparse(u).scheme in ('http','https') and official(u) else None
def get(s,u,limit=8*1024*1024):
 try:
  r=s.get(u,timeout=TIMEOUT,allow_redirects=True,stream=True)
  if r.status_code>=400 or not official(r.url): r.close(); return None,None,None
  b=bytearray()
  for c in r.iter_content(65536):
   if c: b.extend(c)
   if len(b)>limit: r.close(); return None,None,None
  final,ct=r.url,(r.headers.get('Content-Type') or '').lower(); r.close(); return bytes(b),final,ct
 except requests.RequestException as e: print('FETCH ERROR',u,e); return None,None,None
def pdf_text(s,u):
 b,u2,ct=get(s,u,18*1024*1024)
 if not b or not ('pdf' in (ct or '') or urlparse(u2).path.lower().endswith('.pdf') or b[:4]==b'%PDF'): return '',None
 try: return txt('\n'.join(p.extract_text() or '' for p in PdfReader(io.BytesIO(b)).pages[:50])),u2
 except Exception as e: print('PDF ERROR',u,e); return '',u2
def dateval(v):
 v=txt(v).replace('st','').replace('nd','').replace('rd','').replace('th','')
 for f in ('%d/%m/%Y','%d-%m-%Y','%d.%m.%Y','%d/%m/%y','%d-%m-%y','%d.%m.%y','%d %B %Y','%d %b %Y','%B %d, %Y'):
  try:return datetime.strptime(v,f).date().isoformat()
  except ValueError:pass
 return None
def field_date(t,patterns):
 for p in patterns:
  m=re.search(p,t,re.I)
  if m:
   d=dateval(m.group(1))
   if d:return d
 return None
def fields(t):
 v=None
 for p in (r'(?:total\s+(?:number\s+of\s+)?vacanc(?:y|ies)|total\s+posts?|number\s+of\s+vacanc(?:y|ies)|no\.\s*of\s*vacanc(?:y|ies))\s*[:\-]?\s*(\d[\d,]*)',r'(\d[\d,]*)\s+(?:vacancies|vacant posts|posts)\b'):
  m=re.search(p,t,re.I)
  if m and 0<int(m.group(1).replace(',',''))<1000000:v=m.group(1).replace(',','');break
 last=field_date(t,[r'(?:last date(?:\s+for|\s+of)?\s+(?:submission|receipt|apply|application)?|closing date|apply online up to|applications? may be submitted up to|on or before)\s*[:\-]?\s*(\d{1,2}[./-]\d{1,2}[./-]\d{2,4}|\d{1,2}\s+[A-Za-z]{3,9}\s+\d{4})'])
 nd=field_date(t,[r'(?:date of notification|notification date|dated|date of advertisement|advertisement date|published on)\s*[:\-]?\s*(\d{1,2}[./-]\d{1,2}[./-]\d{2,4}|\d{1,2}\s+[A-Za-z]{3,9}\s+\d{4})'])
 q=re.search(r'(?:educational|essential|minimum|prescribed)\s+qualification(?:s)?\s*[:\-]?\s*(.{20,240}?)(?:\n|\b(?:age limit|pay scale|salary|application fee|selection process|how to apply)\b)',t,re.I)
 fee=re.search(r'(?:application fee|examination fee|exam fee|registration fee)\s*[:\-]?\s*([^\n]{3,120})',t,re.I)
 age=re.search(r'(?:age limit|age criteria)\s*[:\-]?\s*([^\n]{3,100})',t,re.I)
 sel=re.search(r'(?:selection process|mode of selection|selection procedure)\s*[:\-]?\s*([^\n]{3,140})',t,re.I)
 return {'vacancies':v,'last_date':last,'notification_date':nd,'qualification':txt(q.group(1))[:240] if q else None,'fees':txt(fee.group(1))[:120] if fee else None,'age_limit':txt(age.group(1))[:100] if age else None,'selection_process':txt(sel.group(1))[:140] if sel else None}
def links(html,page):
 soup=BeautifulSoup(html,'html.parser'); out=[]; seen=set()
 for a in soup.select('a[href]'):
  label=txt(a.get_text(' ',strip=True)); row=a.find_parent(['tr','li']); context=txt(row.get_text(' ',strip=True)) if row else label
  title=context if len(context)>len(label)+8 else label; low=(title+' '+label).lower()
  if len(title)<12 or len(title)>350 or any(x in low for x in BAD) or not any(x in low for x in HINT):continue
  u=safe(a.get('href'),page)
  if u and u not in seen and u.rstrip('/')!=page.rstrip('/'):seen.add(u);out.append((title[:220],u))
 return out
def apply_link(s,html,page,pdftxt):
 candidates=[]
 if html:
  soup=BeautifulSoup(html,'html.parser')
  for a in soup.select('a[href]'):
   label=txt(a.get_text(' ',strip=True)).lower(); u=safe(a.get('href'),page)
   if u and any(k in label for k in ('apply online','online application','registration','apply now','application portal')):candidates.append(u)
 for raw in re.findall(r'https?://[A-Za-z0-9._~:/?#\[\]@!$&\'()*+,;=%-]+',pdftxt):
  u=safe(raw.rstrip('.,;)'),page)
  if u and any(k in u.lower() for k in ('apply','registration','online','ora','recruit')):candidates.append(u)
 for u in dict.fromkeys(candidates):
  b,final,_=get(s,u,1024*1024)
  if b is not None:return final
 return None
def norm(t):return re.sub(r'[^a-z0-9]+',' ',txt(t).lower()).strip()
def dbheaders():return {'apikey':KEY,'Authorization':'Bearer '+KEY,'Content-Type':'application/json','Prefer':'return=representation'}
def main():
 if not DB.startswith('https://') or not KEY: print('Missing SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY GitHub secret');return 2
 s=requests.Session();s.headers.update(HEAD); urls=set(); titles=set(); start=0
 try:
  while True:
   r=s.get(DB+'/rest/v1/jobs',headers=dbheaders(),params={'select':'id,title,department,notification_url,source_url','limit':1000,'offset':start},timeout=30);r.raise_for_status();rows=r.json()
   for x in rows:
    for k in ('notification_url','source_url'):
     if x.get(k):urls.add(x[k].rstrip('/'))
    titles.add((norm(x.get('title')),norm(x.get('department'))))
   if len(rows)<1000:break
   start+=1000
 except Exception as e:print('Supabase read error:',e);return 2
 candidates=[]; seen=set()
 for name,u in SOURCES:
  print('CHECK',name,u); b,final,ct=get(s,u)
  if not b or 'pdf' in (ct or ''):continue
  for title,link in links(b,final):
   if link.rstrip('/') not in urls and link not in seen:seen.add(link);candidates.append((name,title,link))
  time.sleep(.3)
 pub=drafts=dupes=errors=0
 today=datetime.now(ZoneInfo('Asia/Kolkata')).date().isoformat()
 for source,title,link in candidates:
  try:
   if any(x in title.lower() for x in BAD) or not any(x in title.lower() for x in HINT):continue
   html,detail,ct=get(s,link); pdftxt='';pdfurl=None
   if html and ('pdf' in (ct or '') or html[:4]==b'%PDF'):pdftxt,pdfurl=pdf_text(s,detail)
   elif html:
    soup=BeautifulSoup(html,'html.parser')
    page_text=txt(soup.get_text(' ',strip=True))
    pdftxt=page_text
    purls=[]
    for a in soup.select('a[href]'):
     label=txt(a.get_text(' ',strip=True)).lower();u=safe(a.get('href'),detail)
     if u and ('.pdf' in urlparse(u).path.lower() or 'notification' in label or 'advertisement' in label or 'download' in label):purls.append(u)
    for pu in purls[:8]:
     t,fu=pdf_text(s,pu)
     if len(t)>len(pdftxt):pdftxt,pdfurl=t,fu
   if len(pdftxt)<180:continue
   # PDF is optional: a genuine, current recruitment detail page on an official government site is also acceptable.
   notice_url=pdfurl or detail
   f=fields(pdftxt);apply=apply_link(s,html,detail,pdftxt)
   
   # Publish only when essential proof and a valid future deadline are present.
   # Missing optional details must never create Draft clutter in the admin panel.
   missing=[]
   if not official(detail): missing.append('official government source')
   if not f['last_date']: missing.append('last date')
   elif f['last_date']<today: missing.append('deadline expired')
   if len(txt(title))<12: missing.append('clear job title')
   if missing:
    print('SKIP - essential detail missing:', ', '.join(missing), '|', title)
    continue
   # Optional fields: vacancy count, qualification, fees, age, selection process, separate apply URL.
   status='published'
   dept=source
   if ' | ' in title:dept=txt(title.split(' | ')[0])[:120] or source
   record={'title':txt(title)[:180],'department':dept,'category':'Latest Jobs','vacancies':f['vacancies'] or '',
    'notification_date':f['notification_date'],'last_date':f['last_date'],'qualification':f['qualification'] or '',
    'fees':f['fees'] or '', 'age_limit':f['age_limit'] or '', 'selection_process':f['selection_process'] or '',
    'notification_url':notice_url,'apply_url':apply or '', 'source_url':detail+'#sja-auto-scanner-managed',
    'description':'Official recruitment notice detected on an official government website. PDF may not be available; open the official notice/source link for complete terms, category-wise vacancies, age relaxation and application instructions.','status':status}
   tk=(norm(record['title']),norm(record['department']))
   if notice_url.rstrip('/') in urls or detail.rstrip('/') in urls or tk in titles:dupes+=1;continue
   chk=s.get(DB+'/rest/v1/jobs',headers=dbheaders(),params={'select':'id','notification_url':'eq.'+notice_url,'limit':1},timeout=25);chk.raise_for_status()
   if chk.json():dupes+=1;continue
   r=s.post(DB+'/rest/v1/jobs',headers=dbheaders(),json=record,timeout=30);r.raise_for_status()
   urls.update((notice_url.rstrip('/'),detail.rstrip('/')));titles.add(tk)
   if status=='published':pub+=1;print('AUTO-PUBLISHED',record['title'],'| optional details missing:',', '.join(missing) if missing else 'none')
   else:drafts+=1;print('DRAFT - deadline missing/expired or official PDF not verified',record['title'],'| missing:',', '.join(missing) if missing else 'deadline/PDF verification')
  except Exception as e:errors+=1;print('PROCESS ERROR',title,e)
  time.sleep(.25)
 print('\nSCAN REPORT | official source pages:',len(SOURCES),'| candidate links:',len(candidates),'| published:',pub,'| drafts:',drafts,'| duplicates:',dupes,'| errors:',errors)
 return 1 if errors else 0
if __name__=='__main__':sys.exit(main())
