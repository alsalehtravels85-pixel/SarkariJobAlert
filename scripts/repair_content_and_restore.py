#!/usr/bin/env python3
"""Repair useful posts and restore two verified records; snapshot all rows first."""
import json, os
from pathlib import Path
import requests
DB=os.environ["SUPABASE_URL"].rstrip("/")
KEY=os.environ["SUPABASE_SERVICE_ROLE_KEY"]
H={"apikey":KEY,"Authorization":f"Bearer {KEY}","Accept":"application/json"}
OUT=Path("repair-output")
DSSSB_NOTICE="https://dsssb.delhi.gov.in/sites/default/files/DSSSB/circulars-orders/final_advt_06_2026_j_e_electrical_mts.pdf"
DSSSB_PAGE="https://dsssb.delhi.gov.in/dsssb/vacancy-notice-advertisement-no-062026-combined-examinations-2026-post-junior-engineer-0"
DSSSB_APPLY="https://dsssbonline.nic.in/"
DSSSB_RESULT="https://dsssb.delhi.gov.in/node/74344"
BPSC_PDF="https://bpsc.bihar.gov.in/wp-content/uploads/BPSC_content/Notices/Results-Integrated-71st-CCE-Main-Written-CCE_BPSC-20261106-wz2q4y.pdf"
SSC_JHT_PDF="https://ssc.gov.in/api/attachment/uploads/masterData/Results/ROLL_05112026.pdf"
SSC_SI_PDF="https://ssc.gov.in/api/attachment/uploads/masterData/NoticeBoards/writeup_29102026.pdf"
UPSSSC_RESULT="https://upsssc.gov.in/Online_App/Results.aspx?ID=169&Result_Type=M&Exam_Code=5&Advt_Code=564&Dept_Code=552&Post_Code=1&OnlyIntview=No"
IIBF_ADMIT="https://www.iibf.org.in/pages/notice-admit-letter-jaiib-dbf"
PATCHES={
"5aa144fd-17f2-4f10-87a5-f1adc76d9e82":{
 "status":"published","notification_url":DSSSB_NOTICE,"source_url":DSSSB_PAGE,"apply_url":DSSSB_APPLY,
 "description":"""# DSSSB Recruitment 2026 – Junior Engineer और MTS के 1,260 पद

दिल्ली अधीनस्थ सेवा चयन बोर्ड (DSSSB) ने Advertisement No. 06/2026 के तहत Junior Engineer (Electric/Electrical), Multi-Tasking Staff (MTS), MTS General Duty और MTS Aaya (Female) पदों के लिए संयुक्त भर्ती अधिसूचना जारी की है। यह अलग-अलग पदों की संयुक्त भर्ती है; हर पद की योग्यता और आयु सीमा समान नहीं है।

## भर्ती का संक्षिप्त विवरण
- भर्ती बोर्ड: Delhi Subordinate Services Selection Board
- विज्ञापन संख्या: 06/2026
- कुल पद: 1,260
- आवेदन माध्यम: ऑनलाइन
- आवेदन शुरू: 12 नवंबर 2026
- अंतिम तिथि: 11 दिसंबर 2026
- परीक्षा तिथि: अभी घोषित नहीं; DSSSB की वेबसाइट पर आगे की सूचना देखें।

## पद और योग्यता
MTS पदों के लिए 10वीं/मैट्रिक की योग्यता लागू है। Junior Engineer (Electric/Electrical) पदों के लिए संबंधित Electrical Engineering की डिग्री या डिप्लोमा और कुछ विभागों में निर्धारित अनुभव जरूरी हो सकता है। MTS Aaya (Female) पद के लिए अधिसूचना में दी गई विशेष पात्रता लागू होगी। विभाग और पद कोड के अनुसार शर्तें बदलती हैं, इसलिए किसी एक पद की योग्यता को सभी पदों पर लागू न मानें।

## आवेदन शुल्क, आयु और चयन
आवेदन शुल्क, आयु सीमा में छूट, विभागवार रिक्तियां, वेतनमान और परीक्षा योजना के लिए आधिकारिक Advertisement No. 06/2026 PDF देखें। JE और MTS की चयन परीक्षा अलग-अलग हो सकती है। इस पोस्ट में अपुष्ट पदवार विवरण को निश्चित नियम के रूप में नहीं बताया गया है।

## ऑनलाइन आवेदन कैसे करें
1. DSSSB की आधिकारिक भर्ती वेबसाइट खोलें।
2. Advertisement No. 06/2026 और अपना Post Code चुनें।
3. संबंधित पद की शैक्षणिक योग्यता, आयु, अनुभव और विभागवार रिक्तियां PDF में जांचें।
4. ऑनलाइन आवेदन पोर्टल पर पंजीकरण करके आवेदन भरें।
5. दस्तावेज अपलोड करें, लागू शुल्क जमा करें और सबमिशन रसीद सुरक्षित रखें।

## आधिकारिक लिंक
- Notification PDF: https://dsssb.delhi.gov.in/sites/default/files/DSSSB/circulars-orders/final_advt_06_2026_j_e_electrical_mts.pdf
- Apply Online: https://dsssbonline.nic.in/
- Official Notice Page: https://dsssb.delhi.gov.in/dsssb/vacancy-notice-advertisement-no-062026-combined-examinations-2026-post-junior-engineer-0

महत्वपूर्ण: अंतिम तिथि 11 दिसंबर 2026 है। पदवार पात्रता और corrigendum केवल DSSSB की आधिकारिक वेबसाइट से जांचें।

Last verified: 11 November 2026."""
},

"a505fb3b-9926-40f6-940f-36c5f0353bf0":{
 "description":"""# UPSSSC BCG Technician Result 2026 – 76 अभ्यर्थी अभिलेख परीक्षण के लिए अर्ह

उत्तर प्रदेश अधीनस्थ सेवा चयन आयोग (UPSSSC) ने विज्ञापन संख्या 10-परीक्षा/2024 के अंतर्गत BCG Technician मुख्य परीक्षा का परिणाम 06 नवंबर 2026 को जारी किया। मुख्य परीक्षा 30 जून 2026 को आयोजित हुई थी। आयोग की सूचना के अनुसार 76 अभ्यर्थियों को अर्हता/अभिलेख परीक्षण के लिए अर्ह घोषित किया गया है।

## Result Overview
- आयोग: Uttar Pradesh Subordinate Services Selection Commission
- पद: BCG Technician
- विज्ञापन संख्या: 10-परीक्षा/2024
- मुख्य परीक्षा तिथि: 30 जून 2026
- परिणाम/सूचना दिनांक: 06 नवंबर 2026
- अभिलेख परीक्षण हेतु अर्ह अभ्यर्थी: 76
- अगला चरण: शैक्षणिक, आरक्षण और अन्य पात्रता दस्तावेजों की जांच

## जरूरी बात – यह अंतिम चयन सूची नहीं है
76 अभ्यर्थियों का नाम/रोल नंबर इस सूची में होना नियुक्ति या अंतिम चयन की गारंटी नहीं है। यह केवल पात्रता और अभिलेख परीक्षण के अगले चरण के लिए अर्हता है। अंतिम चयन का निर्णय दस्तावेजों की जांच के बाद आयोग द्वारा अलग से किया जाएगा।

## अभिलेख अपलोड
प्रकाशित अपडेट के अनुसार चिन्हित अभ्यर्थियों के लिए दस्तावेज अपलोड की अवधि 06 नवंबर से 20 नवंबर 2026 बताई गई है। केवल shortlisted candidates अपने candidate login में उपलब्ध निर्देशों के अनुसार दस्तावेज अपलोड करें। अंतिम तिथि, आवश्यक दस्तावेज और upload status को अपने login तथा आयोग के notice से दोबारा मिलाएं।

## Result कैसे देखें
1. UPSSSC की official website खोलें।
2. Results section में Advertisement No. 10-परीक्षा/2024 की BCG Technician Main Examination entry चुनें।
3. मांगी गई registration/login details भरें।
4. अपना result देखें और उपलब्ध हो तो PDF/print सुरक्षित रखें।
5. यदि आप 76 अर्ह अभ्यर्थियों में हैं, तो document upload और आगे की प्रक्रिया की सूचना पढ़ें।

## Official Links
- Direct Result: https://upsssc.gov.in/Online_App/Results.aspx?ID=169&Result_Type=M&Exam_Code=5&Advt_Code=564&Dept_Code=552&Post_Code=1&OnlyIntview=No
- Official UPSSSC Website: https://upsssc.gov.in/

Last verified: 11 November 2026."""
},
"3603a99c-11cd-4000-91e0-7fc8fdeecb57":{
 "notification_url":BPSC_PDF,"result_url":BPSC_PDF,
 "description":"""# BPSC 71st CCE Mains Result 2026 – 3,392 अभ्यर्थी सफल

Bihar Public Service Commission (BPSC) ने Integrated 71st Combined Competitive Examination (CCE) Main Written Examination का परिणाम 06 नवंबर 2026 को घोषित किया। आयोग की प्रकाशित result notice के अनुसार 1,298 रिक्तियों के विरुद्ध 3,392 अभ्यर्थियों को अगले चरण के लिए सफल घोषित किया गया है।

## Result Overview
- आयोग: Bihar Public Service Commission
- परीक्षा: Integrated 71st Combined Competitive Examination
- चरण: Main Written Examination
- परिणाम दिनांक: 06 नवंबर 2026
- अधिसूचित रिक्तियां: 1,298
- सफल अभ्यर्थी: 3,392
- अगला चरण: Interview / Personality Test, आयोग की आगे की सूचना के अनुसार

## अपना परिणाम कैसे जांचें
1. नीचे दिए गए direct official result PDF को खोलें।
2. PDF में अपना roll number खोजें। मोबाइल PDF viewer में Search विकल्प और कंप्यूटर पर Ctrl+F उपयोग कर सकते हैं।
3. Roll number और उपलब्ध विवरण ध्यान से मिलाएं।
4. PDF डाउनलोड करके अपने रिकॉर्ड के लिए सुरक्षित रखें।
5. Interview schedule, document requirements और अन्य निर्देशों के लिए BPSC की अगली आधिकारिक सूचना देखते रहें।

## महत्वपूर्ण स्पष्टीकरण
Mains में सफल घोषित होना अंतिम नियुक्ति नहीं है। Interview/Personality Test और आयोग द्वारा निर्धारित आगे की प्रक्रिया पूरी होने के बाद ही अंतिम मेरिट/चयन संबंधी निर्णय होगा। Cut-off या category-wise marks के बारे में कोई संख्या तभी मानें जब वह आयोग की official notice में प्रकाशित हो।

## Official Links
- Direct Mains Result PDF: https://bpsc.bihar.gov.in/wp-content/uploads/BPSC_content/Notices/Results-Integrated-71st-CCE-Main-Written-CCE_BPSC-20261106-wz2q4y.pdf
- BPSC Official Website: https://bpsc.bihar.gov.in/

Last verified: 11 November 2026."""
},
"70f71ee7-b0d6-4abe-b759-373b8b42adea":{
 "notification_url":DSSSB_RESULT,"source_url":"https://dsssb.delhi.gov.in/results?page=1","result_url":DSSSB_RESULT,
 "description":"""# DSSSB Computer Lab / IT Assistant Result 2026 – Notice No. 384

Delhi Subordinate Services Selection Board (DSSSB) ने New Delhi Municipal Council (NDMC) के Computer Lab / IT Assistant पद, Post Code 96/23 के लिए Result Notice No. 384 दिनांक 29 अक्टूबर 2026 को प्रकाशित किया है। यह पुरानी भर्ती प्रक्रिया का परिणाम है; यह नई भर्ती या fresh application window नहीं है।

## Result Overview
- Recruiting Board: Delhi Subordinate Services Selection Board
- Department: New Delhi Municipal Council
- Post: Computer Lab / IT Assistant
- Post Code: 96/23
- Result Notice: 384
- Notice Date: 29 October 2026
- अगला चरण: notice में दिए गए provisional nomination / waiting panel और document verification निर्देशों के अनुसार।

## अपना result कैसे जांचें
1. DSSSB के official Result Notice No. 384 पेज को खोलें।
2. Download लिंक से मूल PDF प्राप्त करें।
3. PDF में अपना roll number खोजें और विवरण ध्यान से मिलाएं।
4. Notice में दिए गए provisional nomination, waiting panel और document verification संबंधी निर्देश पढ़ें।
5. Notice No. 385 भी देखें, क्योंकि उसी दिन rejection notice भी प्रकाशित हुआ था।

## महत्वपूर्ण स्पष्टीकरण
Result notice में नाम आने का अर्थ स्वतः नियुक्ति नहीं है। अंतिम नियुक्ति से पहले संबंधित विभाग द्वारा पात्रता और दस्तावेजों की जांच की जा सकती है। उम्मीदवार केवल DSSSB द्वारा जारी मूल notice को अंतिम मानें।

## Official Links
- Result Notice No. 384: https://dsssb.delhi.gov.in/node/74344
- DSSSB Results: https://dsssb.delhi.gov.in/results?page=1
- DSSSB Official Website: https://dsssb.delhi.gov.in/

Last verified: 11 November 2026."""
},
"afbf99d5-9b53-4208-a2e3-6a2554d6f69e":{
 "result_url":SSC_SI_PDF,
 "description":"""# SSC SI Delhi Police & CAPF PET/PST Result 2025

Staff Selection Commission (SSC) ने Sub-Inspector in Delhi Police and Central Armed Police Forces Examination 2025 के PET/PST चरण का परिणाम 29 अक्टूबर 2026 को प्रकाशित किया है।

## Result Overview
- आयोग: Staff Selection Commission
- परीक्षा: Sub-Inspector in Delhi Police and CAPFs Examination, 2025
- चरण: PET/PST Result
- Result Notice Date: 29 October 2026
- अगला चरण: Paper-II, SSC की आगे की परीक्षा सूचना के अनुसार
- Result status: Declared

## अपना result कैसे देखें
1. SSC की direct official result notice PDF खोलें।
2. PDF में अपना roll number खोजें। मोबाइल PDF viewer में Search और कंप्यूटर पर Ctrl+F उपयोग करें।
3. अपने roll number और notice में दिए गए निर्देशों को ध्यान से मिलाएं।
4. Paper-II की तारीख, admit card और reporting instructions के लिए SSC की अगली official notice देखें।

## ध्यान दें
PET/PST result में shortlist होना अंतिम चयन नहीं है। उम्मीदवारों को Paper-II और आगे की document/medical प्रक्रिया से संबंधित SSC की आधिकारिक सूचनाएं देखनी चाहिए। इस पोस्ट में category-wise cut-off या shortlisted संख्या तभी जोड़ी जाएगी जब वह official PDF से पुष्टि हो।

## Official Links
- Direct SSC PET/PST Notice PDF: https://ssc.gov.in/api/attachment/uploads/masterData/NoticeBoards/writeup_29102026.pdf
- SSC Official Website: https://ssc.gov.in/

Last verified: 11 November 2026."""
},
"33b3dd29-d03a-4bdb-80a5-490466c67dba":{
 "notification_url":SSC_JHT_PDF,
 "description":"""# SSC JHT / JT / Senior Translator Result 2025 – FRTA सूची

Staff Selection Commission (SSC) ने Combined Hindi Translators Examination 2025 (CHTE 2025) के लिए First Round of Tentative Allocation (FRTA) परिणाम 05 नवंबर 2026 को जारी किया। यह provisional allocation है; इसे final appointment letter न समझें।

## Result Overview
- आयोग: Staff Selection Commission
- परीक्षा: Combined Hindi Translators Examination 2025
- पद: Junior Hindi Translator, Junior Translator, Senior Translator, Junior Translation Officer और Hindi Pradhyapak सहित अधिसूचना में दिए गए पद
- Result Date: 05 November 2026
- Result Stage: First Round of Tentative Allocation (FRTA)
- Provisionally recommended candidates: 532 (published result summary के अनुसार)

## Category-wise count
- UR: 228
- SC: 82
- ST: 38
- OBC: 137
- EWS: 47
- Total: 532

## Result कैसे जांचें
1. SSC की direct official FRTA PDF खोलें।
2. PDF में अपना roll number खोजें।
3. Allocation/post preference और आगे Identity Verification (IV) से जुड़े निर्देश ध्यान से पढ़ें।
4. SSC द्वारा बताई गई document/identity verification प्रक्रिया और समय-सीमा का पालन करें।
5. आगे की allocation या corrigendum सूचना के लिए SSC की official website देखते रहें।

## जरूरी स्पष्टीकरण
FRTA का अर्थ First Round of Tentative Allocation है। Provisional recommendation अपने-आप अंतिम नियुक्ति या सभी दस्तावेजों की स्वीकृति नहीं है। Final status SSC और संबंधित user department की verification के बाद ही तय होगा।

## Official Links
- Direct FRTA Result PDF: https://ssc.gov.in/api/attachment/uploads/masterData/Results/ROLL_05112026.pdf
- SSC Official Website: https://ssc.gov.in/

Last verified: 11 November 2026."""
}
}
def main():
 OUT.mkdir(exist_ok=True)
 rows=[]; offset=0
 while True:
  r=requests.get(DB+"/rest/v1/jobs",headers=H,params={"select":"*","order":"created_at.asc","limit":500,"offset":offset},timeout=35)
  r.raise_for_status(); batch=r.json(); rows.extend(batch)
  if len(batch)<500: break
  offset+=500
 (OUT/"pre-repair-all-jobs-backup.json").write_text(json.dumps(rows,ensure_ascii=False,indent=2,default=str),encoding="utf-8")
 found={str(x.get("id")):x for x in rows}
 for rid,patch in PATCHES.items():
  if rid not in found: raise RuntimeError("Missing target row: "+rid)
  resp=requests.patch(DB+"/rest/v1/jobs",headers={**H,"Content-Type":"application/json","Prefer":"return=representation"},params={"id":f"eq.{rid}"},json=patch,timeout=35)
  resp.raise_for_status(); data=resp.json()
  if not isinstance(data,list) or len(data)!=1: raise RuntimeError("Unexpected update response for "+rid)
  print("REPAIRED",data[0].get("title"),"| status",data[0].get("status"))
 print(f"CONTENT REPAIR COMPLETE | updated={len(PATCHES)} | full backup saved | permanent deletes=0")
if __name__=="__main__": main()
