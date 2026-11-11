#!/usr/bin/env python3
"""Rewrite one published UPESSC duplicate placeholder as a distinct exam guide.

Safety: backs up the exact row first; updates only title/description/source metadata.
Never changes status, never deletes, never drafts, never touches any other row.
"""
import json
import os
from datetime import datetime, timezone
from pathlib import Path
import requests

DB = os.environ["SUPABASE_URL"].rstrip("/")
KEY = os.environ["SUPABASE_SERVICE_ROLE_KEY"]
ROW_ID = "67a1cefb-d93e-44f8-bad5-8102e96c2c1e"
NOTICE = "https://www.upessc.up.gov.in/Notice/e51a-5123-4329-4e57-72f0.pdf"
APPLY = "https://apply.upessc.org/"
OUT = Path("repair-output")
HEADERS = {"apikey": KEY, "Authorization": f"Bearer {KEY}", "Content-Type": "application/json", "Accept": "application/json"}

TITLE = "UPESSC Principal Recruitment 2026: Exam Pattern & Selection Process"
DESCRIPTION = """# UPESSC Principal Recruitment 2026: Exam Pattern और Selection Process

उत्तर प्रदेश शिक्षा सेवा चयन आयोग (UPESSC), प्रयागराज के विज्ञापन संख्या 08/2026 के अंतर्गत अशासकीय सहायता प्राप्त माध्यमिक विद्यालयों में प्रधानाचार्य के 1,475 पदों पर चयन किया जाना है। इस लेख में भर्ती की सामान्य जानकारी दोहराने के बजाय परीक्षा के अंक-विभाजन, लिखित परीक्षा, साक्षात्कार और मेरिट तैयार होने की प्रक्रिया को आसान हिंदी में समझाया गया है।

## चयन प्रक्रिया: कुल 400 अंक

आधिकारिक विज्ञापन के अनुसार चयन लिखित परीक्षा और साक्षात्कार के संयुक्त अंकों के आधार पर होगा:
- लिखित परीक्षा: 360 अंक
- साक्षात्कार: 40 अंक
- कुल: 400 अंक

लिखित परीक्षा में 120 वस्तुनिष्ठ (Objective) प्रश्न होंगे। परीक्षा की अवधि 2 घंटे होगी। प्रश्नपत्र हिंदी और अंग्रेजी में होगा; भाषा विषयों के लिए विज्ञापन में अलग व्यवस्था दी गई है।

## अंक और Negative Marking

- प्रत्येक सही उत्तर के लिए 3 अंक मिलेंगे।
- गलत उत्तर या एक से अधिक विकल्प भरने पर 1 अंक काटा जाएगा।
- प्रश्नों के चार विकल्प होंगे और एक सबसे उपयुक्त विकल्प चुनना होगा।
- परीक्षा के बाद कट-ऑफ और प्राप्तांक आयोग द्वारा अपनी वेबसाइट पर प्रदर्शित किए जाएंगे।

इसलिए उम्मीदवारों को केवल प्रश्न हल करने की गति पर नहीं, बल्कि सटीक उत्तर देने पर भी ध्यान देना चाहिए। अनुमान से उत्तर भरने से पहले negative marking को ध्यान में रखें।

## बराबर अंक होने पर मेरिट कैसे बनेगी?

यदि दो या अधिक उम्मीदवारों के कुल अंक समान होते हैं, तो विज्ञापन में दिए गए क्रम के अनुसार पहले लिखित परीक्षा के अंक देखे जाएंगे। लिखित परीक्षा के अंक भी समान होने पर साक्षात्कार के अंक देखे जाएंगे। इसके बाद स्नातकोत्तर (Postgraduate) के अधिक प्रतिशत, फिर B.Ed. के अधिक प्रतिशत को प्राथमिकता दी जाएगी। सभी मानदंड समान रहने पर अधिक आयु वाले उम्मीदवार को ऊपर रखा जाएगा।

## जरूरी पात्रता का संक्षिप्त पुनरावलोकन

प्रधानाचार्य पद के लिए विज्ञापन में मुख्य रूप से ये शर्तें दी गई हैं:
1. मान्यता प्राप्त विश्वविद्यालय से कम से कम 50% अंकों के साथ स्नातकोत्तर डिग्री।
2. NCTE से मान्यता प्राप्त पाठ्यक्रम से B.Ed. डिग्री।
3. कक्षा 9 से 12 तक Lecturer/Assistant Teacher के रूप में कम से कम 4 वर्ष का शिक्षण अनुभव, या हाईस्कूल में प्रधानाध्यापक के रूप में कम से कम 4 वर्ष का अनुभव। अनुभव प्रमाणपत्र निर्धारित सक्षम अधिकारियों से जारी/प्रति-हस्ताक्षरित होना चाहिए।

आयु की गणना 01 जुलाई 2026 के अनुसार है: न्यूनतम आयु 30 वर्ष और अधिकतम/अधिवर्षता आयु 62 वर्ष। सभी श्रेणियों के लिए परीक्षा शुल्क ₹2,000 दिया गया है। अंतिम निर्णय के लिए मूल विज्ञापन पढ़ना जरूरी है।

## महत्वपूर्ण तारीखें

- विज्ञापन और आवेदन प्रारंभ: 23 अक्टूबर 2026
- शुल्क जमा करने की अंतिम तिथि: 22 नवंबर 2026
- आवेदन में संशोधन की अंतिम तिथि: 25 नवंबर 2026
- लिखित परीक्षा की घोषित तिथि: 07 जनवरी 2027

आयोग की ओर से संशोधित कार्यक्रम जारी होने पर उम्मीदवारों को आधिकारिक वेबसाइट पर नया नोटिस देखना चाहिए।

## उम्मीदवारों के लिए तैयारी चेकलिस्ट

- 120 प्रश्नों के लिए 2 घंटे का अभ्यास करें।
- 3 अंक सही और 1 अंक की negative marking के अनुसार mock test का विश्लेषण करें।
- अपने स्नातकोत्तर और B.Ed. के अंकपत्र सुरक्षित रखें; tie-break में इनके प्रतिशत देखे जा सकते हैं।
- अनुभव प्रमाणपत्र में पद, अवधि और जारी करने वाले सक्षम अधिकारी का विवरण जांचें।
- आवेदन में भरी गई जानकारी और दस्तावेजों का मिलान करें।

## आधिकारिक लिंक

- मूल विज्ञापन PDF: """ + NOTICE + """
- ऑनलाइन आवेदन पोर्टल: """ + APPLY + """
- UPESSC आधिकारिक वेबसाइट: https://www.upessc.up.gov.in/

यह परीक्षा-प्रक्रिया संबंधी जानकारी विज्ञापन संख्या 08/2026 पर आधारित है। किसी भी अंतिम पात्रता, दस्तावेज या तारीख के लिए आयोग का मूल विज्ञापन ही मान्य होगा।

📢 Latest Government Jobs, Admit Cards & Results के लिए SarkariJobAlert पर विजिट करें।
https://sarkari-jobalert.com/
"""

def main():
    if not DB.startswith("https://") or not KEY:
        raise RuntimeError("Supabase secrets missing")
    session = requests.Session()
    response = session.get(f"{DB}/rest/v1/jobs", headers=HEADERS, params={"select": "*", "id": f"eq.{ROW_ID}"}, timeout=(12, 35))
    response.raise_for_status()
    rows = response.json()
    if len(rows) != 1:
        raise RuntimeError(f"Expected exactly one target row; found {len(rows)}")
    row = rows[0]
    if row.get("status") != "published":
        raise RuntimeError("Target is not currently published; refusing to change it")
    OUT.mkdir(exist_ok=True)
    backup = OUT / "upessc-principal-post-before-rewrite.json"
    backup.write_text(json.dumps(row, ensure_ascii=False, indent=2), encoding="utf-8")
    payload = {"title": TITLE, "description": DESCRIPTION, "notification_url": NOTICE, "source_url": NOTICE, "updated_at": datetime.now(timezone.utc).isoformat()}
    update = session.patch(f"{DB}/rest/v1/jobs", headers={**HEADERS, "Prefer": "return=representation"}, params={"id": f"eq.{ROW_ID}", "status": "eq.published"}, json=payload, timeout=(12, 35))
    update.raise_for_status()
    changed = update.json()
    if len(changed) != 1 or changed[0].get("status") != "published":
        raise RuntimeError("Post-update verification failed; inspect backup before retrying")
    print("UPDATED ONE PUBLISHED POST: title/description/source metadata only")
    print("STATUS PRESERVED: published")
    print(f"BACKUP: {backup}")
    print("NO OTHER ROWS TOUCHED; NO DRAFT OR DELETE OPERATIONS.")

if __name__ == "__main__":
    main()
