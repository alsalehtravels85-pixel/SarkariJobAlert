import os,json,requests
from pathlib import Path
db=os.environ["SUPABASE_URL"].rstrip("/")
key=os.environ["SUPABASE_SERVICE_ROLE_KEY"]
h={"apikey":key,"Authorization":"Bearer "+key,"Accept":"application/json"}
out=Path("repair-output"); out.mkdir(exist_ok=True)
r=requests.get(db+"/rest/v1/jobs",headers=h,params={"select":"*","limit":500},timeout=35); r.raise_for_status(); rows=r.json()
(out/"pre-draft-repair-backup.json").write_text(json.dumps(rows,ensure_ascii=False,indent=2),encoding="utf-8")
patches={
"d5777272-7ea6-45d0-953f-c4b96533aa69":{
"status":"published","notification_url":"https://nationalinsurance.nic.co.in/sites/default/files/2026-11/Advertisement%20for%20Engagement%20of%20Apprentices%20for%20the%20year%202026-27.pdf","source_url":"https://nationalinsurance.nic.co.in/","apply_url":"https://nats.education.gov.in/",
"description":"""# NICL Graduate Apprentice Recruitment 2026 – 200 पद

National Insurance Company Limited ने 2026-27 के लिए 200 Graduate Apprentice seats निकाली हैं। यह 12 महीने का apprenticeship training है, permanent job नहीं।

**महत्वपूर्ण विवरण**
- आवेदन: 04 से 18 नवंबर 2026
- कुल सीटें: 200 (14 राज्यों में)
- योग्यता: किसी भी विषय में regular full-time graduation; degree 01 अप्रैल 2026 तक पूरी होनी चाहिए
- आयु: 21–30 वर्ष, 01 अप्रैल 2026 के अनुसार
- Stipend: ₹15,000 प्रतिमाह
- अवधि: 12 महीने
- आयु छूट: SC/ST 5 वर्ष, OBC-NCL 3 वर्ष, PwBD 10 वर्ष

**आवेदन प्रक्रिया**
1. NATS portal पर student registration और profile पूरी करें।
2. National Insurance Company Limited की apprenticeship opportunity खोजकर Apply करें।
3. NATS enrolment number लेकर NICL notification में बताए गए BFSI portal पर आगे का form पूरा करें।
4. आवश्यक documents upload कर final confirmation सुरक्षित रखें।

स्थानीय भाषा का ज्ञान वांछनीय है। चयन, दस्तावेज सत्यापन, शुल्क और अन्य नियम मूल notification से जांचें। Apprenticeship से NICL में permanent employment का अधिकार स्वतः नहीं मिलता।

**Official links**
Notification PDF: https://nationalinsurance.nic.co.in/sites/default/files/2026-11/Advertisement%20for%20Engagement%20of%20Apprentices%20for%20the%20year%202026-27.pdf
NICL: https://nationalinsurance.nic.co.in/
NATS: https://nats.education.gov.in/

Last verified: 11 November 2026."""
},
"f0fd898b-f454-4ba6-8d5f-6b18255ee18c":{
"status":"published","source_url":"https://www.rrbcdg.gov.in/employment-notices.php","apply_url":"https://www.rrbapply.gov.in/",
"description":"""# RRB Isolated Categories Recruitment 2026 – CEN 09/2026, 191 पद

Railway Recruitment Boards ने CEN 09/2026 के अंतर्गत सात Isolated Category posts के लिए 191 vacancies निकाली हैं।

**Post-wise vacancies**
- Chief Law Assistant: 17
- Public Prosecutor: 21
- Senior Publicity Inspector: 8
- Junior Translator (Hindi): 79
- Staff and Welfare Inspector: 27
- Scientific Assistant (Training): 3
- Lab Assistant Grade III: 36

**महत्वपूर्ण तिथियां**
- आवेदन शुरू: 05 नवंबर 2026
- अंतिम तिथि: 04 दिसंबर 2026 (11:59 PM)
- Fee payment: 06 दिसंबर 2026 तक
- Correction window: 07–16 दिसंबर 2026
- CBT date: बाद में घोषित होगी।

**योग्यता और चयन**
हर post की qualification अलग है। Law degree और legal practice, संबंधित विषय की degree, Hindi translation qualification या Chemistry/Metallurgy qualification जैसी शर्तें post-wise लागू हैं। Age limit भी post के अनुसार 18 से 40 वर्ष तक अलग-अलग है। चयन में CBT, जहां लागू हो Translation/Skill/Performance Test, Document Verification और Medical Examination शामिल हैं।

**आवेदन**
Official RRB application portal पर CEN 09/2026 चुनें। आवेदन से पहले Annexure B में अपने चुने हुए RRB की post-wise vacancy जरूर जांचें; केवल एक RRB चुना जा सकता है। Fee, experience, age cut-off और medical standards मूल CEN notice से confirm करें।

**Links**
Notification PDF copy: https://www.adda247.com/jobs/wp-content/uploads/sites/22/2026/11/05081908/CEN_09_2026_IsolatedCategory.pdf
RRB notices: https://www.rrbcdg.gov.in/employment-notices.php
Apply: https://www.rrbapply.gov.in/

Last verified: 11 November 2026."""
},
"0854e0e3-437d-4999-8e7d-14de08a4ee0b":{
"status":"published","title":"SSC MTS Havaldar PET/PST Admit Card 2026 – Exam Date 03 November (Archive)",
"source_url":"https://ssc.gov.in/","notification_url":"https://ssccr.gov.in/admit-card","admit_card_url":"https://ssccr.gov.in/admit-card",
"description":"""# SSC MTS Havaldar PET/PST Admit Card 2026 – पुरानी सूचना

SSC MTS (Non-Technical) Examination 2025 के Havaldar पद के PET/PST चरण के लिए admit-card update जारी हुआ था। इस post में दी गई परीक्षा तिथि 03 नवंबर 2026 अब बीत चुकी है। इसलिए यह active admit-card download announcement नहीं, बल्कि उम्मीदवारों के reference के लिए archive है।

**परीक्षा विवरण**
- आयोग: Staff Selection Commission
- भर्ती: MTS (Non-Technical) Examination 2025 – Havaldar
- चरण: PET/PST
- बताई गई परीक्षा तिथि: 03 नवंबर 2026
- क्षेत्रीय वेबसाइट: SSC Central Region

परीक्षा में शामिल उम्मीदवार आगे के result और next-stage updates के लिए SSC की official website देखते रहें। पुराने admit card को किसी दूसरी परीक्षा के लिए उपयोग न करें। Login में पुरानी सूचना उपलब्ध न हो तो SSC Central Region की official help व्यवस्था देखें।

**Official links**
SSC Central Region: https://ssccr.gov.in/admit-card
SSC: https://ssc.gov.in/

Last updated: 11 November 2026."""
}}
found={str(x.get("id")):x for x in rows}
for rid,p in patches.items():
 if rid not in found: raise RuntimeError("Missing row "+rid)
 rr=requests.patch(db+"/rest/v1/jobs",headers={**h,"Content-Type":"application/json","Prefer":"return=representation"},params={"id":"eq."+rid},json=p,timeout=35); rr.raise_for_status()
 data=rr.json()
 if len(data)!=1: raise RuntimeError("Unexpected update "+rid)
 print("REPAIRED",data[0].get("title"),data[0].get("status"))
print("SUCCESS: 3 posts repaired/restored; full backup saved; no deletions")
