import os,json,requests
from pathlib import Path
db=os.environ["SUPABASE_URL"].rstrip("/")
key=os.environ["SUPABASE_SERVICE_ROLE_KEY"]
h={"apikey":key,"Authorization":"Bearer "+key,"Accept":"application/json"}
out=Path("repair-output"); out.mkdir(exist_ok=True)
r=requests.get(db+"/rest/v1/jobs",headers=h,params={"select":"*","limit":500},timeout=35); r.raise_for_status(); rows=r.json()
(out/"pre-editorial-repair-backup.json").write_text(json.dumps(rows,ensure_ascii=False,indent=2),encoding="utf-8")
byid={str(x.get("id")):x for x in rows}
canonical="6245be5f-4f99-4852-972a-17e17cd018f2"
duplicate="67a1cefb-d93e-44f8-bad5-8102e96c2c1e"
ecce="dedd2681-92ca-4691-bda2-7e668dfb74a4"
for rid in (canonical,duplicate,ecce):
 if rid not in byid: raise RuntimeError("Missing expected row "+rid)
main=byid[canonical]
desc=main.get("description") or ""
addition="""

## आवेदन से पहले जरूरी जांच

- इस भर्ती का विज्ञापन क्रमांक 08/2026 है। आवेदन से पहले इसी विज्ञापन का मूल PDF पढ़ें; किसी अन्य Principal/Headmaster भर्ती की योग्यता लागू न मानें।
- उम्मीदवार को पहले One Time Registration (OTR) पूरा करना है, फिर इसी विज्ञापन के लिए आवेदन करना है।
- आवेदन शुल्क जमा करने और फॉर्म में सुधार की अंतिम तिथि अलग-अलग हैं: शुल्क 22 नवंबर 2026 तक और correction 25 नवंबर 2026 तक बताई गई है।
- Girls' schools के Principal पदों के लिए notification में दी गई gender eligibility condition अलग से जांचें।
- Postgraduate degree, B.Ed. और निर्धारित teaching/headmaster experience तीनों शर्तें पूरी होने पर ही आवेदन करें।
- परीक्षा तिथि 07 जनवरी 2027 बताई गई है; किसी संशोधित कार्यक्रम के लिए UPESSC की आधिकारिक वेबसाइट देखते रहें।

**Official verification:** Notification PDF: https://www.upessc.up.gov.in/Notice/e51a-5123-4329-4e57-72f0.pdf | Apply portal: https://apply.upessc.org/ | Commission: https://www.upessc.up.gov.in/
"""
if "## आवेदन से पहले जरूरी जांच" not in desc:
 desc=desc.replace("📢 Latest Government Jobs",addition+"\n📢 Latest Government Jobs")
patches=[
 (canonical,{"description":desc,"source_url":"https://www.upessc.up.gov.in/"}),
 (duplicate,{"status":"draft","title":"UPESSC Principal Recruitment 2026 – Duplicate Draft (Merged into Main Post)","source_url":"https://www.upessc.up.gov.in/","description":"""यह अलग draft article, UPESSC Advertisement No. 08/2026 के 1,475 Principal पदों वाली मुख्य published post में merge कर दिया गया है।

एक ही भर्ती के लिए दो अलग-अलग public pages न बनें, इसलिए यह record Draft में सुरक्षित रखा गया है। कोई जानकारी या record delete नहीं किया गया।

मुख्य और अपडेटेड पोस्ट: https://sarkari-jobalert.com/

Official notification: https://www.upessc.up.gov.in/Notice/e51a-5123-4329-4e57-72f0.pdf
Apply portal: https://apply.upessc.org/

Editorial status: Duplicate consolidated; do not publish this draft separately."""}),
 (ecce,{"status":"draft","department":"Uttar Pradesh Basic Education Department (reported; district-specific outsourcing listing)","source_url":"https://sewayojan.up.nic.in/","notification_url":"https://sewayojan.up.nic.in/","apply_url":"https://sewayojan.up.nic.in/","description":"""# Bulandshahar ECCE Educator Recruitment 2026 – 160 Posts (Verification Pending)

Bulandshahar district में ECCE Educator के 160 outsourcing posts और 02 से 18 नवंबर 2026 तक आवेदन की जानकारी कुछ employment-information portals पर प्रकाशित हुई है। UP Rojgar Sangam (Sewayojan) उत्तर प्रदेश सरकार का आधिकारिक employment portal है, लेकिन इस audit में इस specific 160-post vacancy का matching official vacancy notice/PDF independently locate नहीं हो पाया।

## उपलब्ध reported details – अभी final न मानें
- पद: ECCE Educator
- जिला: Bulandshahar, Uttar Pradesh
- reported vacancies: 160
- reported application dates: 02–18 November 2026
- reported remuneration: ₹10,313 प्रति माह
- reported engagement: Outsourcing/contract
- reported eligibility: Home Science graduation with 50% marks OR qualifying NTT / CT (Nursery) / DPSE diploma
- reported age details में sources के बीच अंतर है; exact age cut-off और relaxation confirm नहीं हैं।

## आवेदन से पहले क्या verify करें
1. Sewayojan portal पर Bulandshahar district और ECCE Educator job listing को सीधे खोजें।
2. Employer/outsourcing agency का नाम, vacancy count, last date, salary और eligibility listing में मिलाएं।
3. यदि portal पर specific job listing उपलब्ध न हो, तो केवल इस summary के आधार पर आवेदन या payment न करें।
4. किसी भी एजेंट को नौकरी दिलाने के नाम पर पैसे न दें।

Official portal: https://sewayojan.up.nic.in/
District Bulandshahr official website: https://bulandshahar.nic.in/

**Editorial status:** Draft रखा गया है क्योंकि specific official vacancy notice अभी independently verify नहीं हुआ। Verification के बाद ही इसे Published किया जाएगा."""})
]
for rid,p in patches:
 rr=requests.patch(db+"/rest/v1/jobs",headers={**h,"Content-Type":"application/json","Prefer":"return=representation"},params={"id":"eq."+rid},json=p,timeout=35); rr.raise_for_status()
 data=rr.json()
 if len(data)!=1: raise RuntimeError("Unexpected update "+rid)
 print("UPDATED",data[0].get("title"),data[0].get("status"))
print("EDITORIAL REPAIR COMPLETE | 3 rows updated | backup saved | permanent deletes=0")
