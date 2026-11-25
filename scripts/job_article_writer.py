"""Gemini-backed Hindi article writer for verified SarkariJobAlert drafts."""
import os, re, time, requests
API_KEY=os.getenv("GEMINI_API_KEY","").strip()
PRIMARY=os.getenv("GEMINI_MODEL","gemini-3.8-flash").strip()
FALLBACK=os.getenv("GEMINI_FALLBACK_MODEL","gemini-3.5-flash-lite").strip()
def words(value):
    return len(re.findall(r"\S+",re.sub(r"<[^>]+>"," ",str(value or ""))))
def generate_article(title,category,department,facts,source_text,official_links):
    if not API_KEY:
        print("GEMINI SKIP: GEMINI_API_KEY missing; candidate not saved."); return None
    source=re.sub(r"\s+"," ",str(source_text or "")).strip()[:18000]
    if len(source)<160:
        print("GEMINI SKIP: official source text too short."); return None
    prompt=f"""
आप SarkariJobAlert के अनुभवी हिंदी संपादक हैं। आधिकारिक स्रोत पर आधारित मौलिक, उपयोगी
और तथ्य-सुरक्षित हिंदी लेख लिखें। कम-से-कम 550 शब्द। वर्ग: {category}
शीर्षक: {title}
विभाग: {department}
निकाले गए तथ्य: {facts}
सत्यापित आधिकारिक लिंक (इनके अलावा URL न बनाएं): {official_links}
आधिकारिक स्रोत का पाठ:
{source}
नियम: केवल स्रोत में स्पष्ट तथ्य लिखें। पद संख्या, तिथि, आयु, योग्यता, फीस, कटऑफ,
परीक्षा तिथि, चयन स्थिति या नियम अनुमान से न जोड़ें। अनुपलब्ध तथ्य के लिए
"आधिकारिक सूचना में उल्लेख नहीं" लिखें। कोई URL न गढ़ें। Vacancy में योग्यता,
पद, तिथियां, शुल्क/आयु (यदि उपलब्ध), चयन और आवेदन प्रक्रिया समझाएं। Admit Card में
डाउनलोड प्रक्रिया, परीक्षा विवरण, कार्ड पर जाँच और सामान्य डाउनलोड समस्या समाधान बताएं।
Result में परिणाम स्थिति, चेक करने के चरण, मेरिट/कटऑफ (यदि उपलब्ध) और आगे के कदम बताएं।
Latest Update में नोटिस का अर्थ, प्रभावित उम्मीदवार, कार्रवाई और समय-सीमा समझाएं।
फालतू दोहराव, keyword stuffing, काल्पनिक FAQ या filler नहीं। साफ हिंदी टेक्स्ट,
उपशीर्षक के लिए ## स्वीकार्य। अंत में आधिकारिक नोटिस से पुष्टि की सलाह दें।
केवल लेख लौटाएं।
"""
    payload={"contents":[{"parts":[{"text":prompt}]}],"generationConfig":{"temperature":0.25,"maxOutputTokens":5000}}
    models=[PRIMARY]+([FALLBACK] if FALLBACK and FALLBACK!=PRIMARY else [])
    for model in models:
        for attempt in range(2):
            try:
                r=requests.post(f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
                    headers={"x-goog-api-key":API_KEY,"Content-Type":"application/json"},json=payload,timeout=100)
                if r.ok:
                    article=r.json()["candidates"][0]["content"]["parts"][0]["text"].strip()
                    if words(article)>=500 and len(article)>=2200: return article
                    print("GEMINI REJECT:",words(article),"words; candidate skipped."); return None
                if r.status_code not in (429,500,502,503,504):
                    print("GEMINI HTTP ERROR:",r.status_code,r.text[:250]); return None
            except (requests.RequestException,KeyError,IndexError,ValueError) as e:
                print("GEMINI ERROR:",str(e)[:200])
            if attempt==0: time.sleep(4)
    print("GEMINI FAILED; candidate skipped."); return None
