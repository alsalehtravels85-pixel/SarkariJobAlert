import os
import re
import json
import time
import random
import datetime as dt
from zoneinfo import ZoneInfo
import requests

# SarkariJobAlert - Daily Hindi School & College Study Guide
# GitHub Secrets required:
# SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY, GEMINI_API_KEY
# Optional GitHub Variables:
# AUTO_PUBLISH_STUDY_GUIDES=true
# GEMINI_MODEL=gemini-3.8-flash
# GEMINI_FALLBACK_MODEL=gemini-3.5-flash-lite

SUPABASE_URL = os.environ["SUPABASE_URL"].rstrip("/")
SERVICE_KEY = os.environ["SUPABASE_SERVICE_ROLE_KEY"]
GEMINI_API_KEY = os.environ["GEMINI_API_KEY"]
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.8-flash").strip()
GEMINI_FALLBACK_MODEL = os.getenv("GEMINI_FALLBACK_MODEL", "gemini-3.5-flash-lite").strip()
AUTO_PUBLISH = os.getenv("AUTO_PUBLISH_STUDY_GUIDES", "true").strip().lower() == "true"
STATUS = "published" if AUTO_PUBLISH else "draft"
TODAY = dt.datetime.now(ZoneInfo("Asia/Kolkata")).date()
TABLE_URL = f"{SUPABASE_URL}/rest/v1/school_articles"

HEADERS = {
    "apikey": SERVICE_KEY,
    "Authorization": f"Bearer {SERVICE_KEY}",
    "Content-Type": "application/json",
    "Prefer": "return=representation",
}

def gemini_post_once(model, payload, timeout=95):
    """One bounded Gemini request. Never wait indefinitely."""
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
    headers = {
        "x-goog-api-key": GEMINI_API_KEY,
        "Content-Type": "application/json",
    }
    return requests.post(url, headers=headers, json=payload, timeout=timeout)


def gemini_generate_with_fallback(payload):
    """
    Keep the complete AI phase below the GitHub Actions 10-minute limit:
    primary model: at most 2 requests; fallback model: at most 1 request.
    """
    primary = GEMINI_MODEL or "gemini-3.8-flash"
    fallback = GEMINI_FALLBACK_MODEL or "gemini-3.5-flash-lite"
    retryable = {429, 500, 502, 503, 504}

    models = [(primary, 2)]
    if fallback and fallback != primary:
        models.append((fallback, 1))

    last_response = None

    for model, attempts in models:
        print(f"Requesting Gemini model: {model}", flush=True)

        for attempt in range(1, attempts + 1):
            try:
                response = gemini_post_once(model, payload, timeout=95)
            except requests.exceptions.Timeout:
                print(
                    f"{model} request timed out (attempt {attempt}/{attempts}).",
                    flush=True
                )
                if attempt < attempts:
                    time.sleep(5)
                    continue
                last_response = None
                break
            except requests.exceptions.RequestException as error:
                print(
                    f"{model} network error (attempt {attempt}/{attempts}): {error}",
                    flush=True
                )
                if attempt < attempts:
                    time.sleep(5)
                    continue
                last_response = None
                break

            last_response = response

            if response.ok:
                return response

            if response.status_code not in retryable:
                # Model not found, invalid key, bad request, etc. Fail immediately.
                return response

            print(
                f"{model} temporarily unavailable (HTTP {response.status_code}), "
                f"attempt {attempt}/{attempts}.",
                flush=True
            )

            if attempt < attempts:
                time.sleep(5)

        if model != models[-1][0]:
            print(
                f"Switching to fallback model: {fallback}",
                flush=True
            )

    if last_response is not None:
        return last_response

    raise RuntimeError(
        "Gemini requests timed out or had network errors on all configured attempts. "
        "The script stopped early to avoid GitHub Actions timeout."
    )


# Rotation: Class 10 se postgraduate level tak. University syllabus institution-wise
# alag hota hai, isliye article prompt mein current syllabus verify karne ki hidayat hai.
COURSES = [
    ("Class 10", ["हिंदी", "अंग्रेज़ी", "गणित", "विज्ञान", "सामाजिक विज्ञान"]),
    ("Class 11", ["हिंदी", "अंग्रेज़ी", "गणित", "भौतिक विज्ञान", "रसायन विज्ञान", "जीव विज्ञान", "लेखाशास्त्र", "अर्थशास्त्र"]),
    ("Class 12", ["हिंदी", "अंग्रेज़ी", "गणित", "भौतिक विज्ञान", "रसायन विज्ञान", "जीव विज्ञान", "इतिहास", "भूगोल", "राजनीति विज्ञान", "लेखाशास्त्र", "व्यवसाय अध्ययन", "अर्थशास्त्र"]),
    ("B.A.", ["हिंदी", "अंग्रेज़ी", "इतिहास", "राजनीति विज्ञान", "समाजशास्त्र", "अर्थशास्त्र", "भूगोल", "शिक्षाशास्त्र"]),
    ("B.Sc.", ["भौतिक विज्ञान", "रसायन विज्ञान", "गणित", "वनस्पति विज्ञान", "प्राणी विज्ञान", "कंप्यूटर विज्ञान", "सांख्यिकी"]),
    ("B.Com.", ["वित्तीय लेखांकन", "व्यावसायिक कानून", "अर्थशास्त्र", "कराधान", "लागत लेखांकन", "लेखापरीक्षा", "व्यवसाय प्रबंधन"]),
    ("M.A.", ["हिंदी", "अंग्रेज़ी", "इतिहास", "राजनीति विज्ञान", "समाजशास्त्र", "अर्थशास्त्र", "भूगोल", "शिक्षाशास्त्र"]),
    ("M.Sc.", ["भौतिक विज्ञान", "रसायन विज्ञान", "गणित", "वनस्पति विज्ञान", "प्राणी विज्ञान", "कंप्यूटर विज्ञान", "सांख्यिकी"]),
    ("M.Com.", ["उन्नत लेखांकन", "कॉर्पोरेट वित्त", "व्यावसायिक अनुसंधान", "कराधान", "लेखापरीक्षा", "व्यवसाय प्रबंधन"]),
]

# Subject ke hisaab se topic pool. AI in topics mein se ek par ek focused lesson banata hai.
TOPICS = {
    "हिंदी": ["भाषा और व्याकरण की मूल अवधारणाएँ", "संज्ञा और उसके भेद", "सर्वनाम और विशेषण", "क्रिया, काल और वाच्य", "समास और संधि", "मुहावरे और लोकोक्तियाँ", "अपठित गद्यांश का विश्लेषण", "काव्य में रस, छंद और अलंकार", "निबंध लेखन की संरचना", "पत्र और अनुच्छेद लेखन"],
    "अंग्रेज़ी": ["Reading comprehension की रणनीति", "Parts of speech", "Tenses और उनका प्रयोग", "Active और passive voice", "Direct और indirect speech", "Vocabulary in context", "Paragraph writing", "Formal letter writing", "Grammar error correction", "Literary devices और उनके उदाहरण"],
    "गणित": ["वास्तविक संख्याएँ और उनके गुण", "बहुपद और शून्यक", "दो चर वाले रैखिक समीकरण", "द्विघात समीकरण", "समांतर श्रेणी", "त्रिभुजों की समानता", "निर्देशांक ज्यामिति", "त्रिकोणमिति की मूल बातें", "वृत्त और स्पर्श रेखाएँ", "प्रायिकता और सांख्यिकी"],
    "विज्ञान": ["रासायनिक अभिक्रियाएँ और समीकरण", "अम्ल, क्षार और लवण", "धातु और अधातु", "कार्बन और उसके यौगिक", "जीवन प्रक्रियाएँ", "नियंत्रण और समन्वय", "प्रकाश का परावर्तन और अपवर्तन", "विद्युत धारा और परिपथ", "चुंबकीय प्रभाव", "पर्यावरण और पारितंत्र"],
    "सामाजिक विज्ञान": ["लोकतंत्र की मूल अवधारणा", "संघवाद और सत्ता का विकेंद्रीकरण", "राजनीतिक दल और चुनाव", "विकास के मानक", "भारतीय अर्थव्यवस्था के क्षेत्र", "भूमि और संसाधन", "कृषि और उद्योग", "राष्ट्रवाद और आधुनिक इतिहास", "वैश्वीकरण", "मानचित्र कौशल"],
    "भौतिक विज्ञान": ["मापन, मात्रक और विमीय विश्लेषण", "सरल रेखीय गति", "न्यूटन के गति नियम", "कार्य, ऊर्जा और शक्ति", "गुरुत्वाकर्षण", "द्रव्य के गुण", "ऊष्मागतिकी की आधारभूत बातें", "विद्युत क्षेत्र और विभव", "धारा विद्युत", "तरंगें और प्रकाशिकी"],
    "रसायन विज्ञान": ["परमाणु की संरचना", "रासायनिक बंधन", "मोल संकल्पना और स्टॉइकियोमेट्री", "ऊष्मागतिकी", "रासायनिक साम्य", "अम्ल-क्षार साम्य", "कार्बनिक रसायन की मूल बातें", "हाइड्रोकार्बन", "विद्युत रसायन", "अभिक्रिया की दर"],
    "जीव विज्ञान": ["कोशिका की संरचना और कार्य", "जैव अणु", "कोशिका विभाजन", "पादप ऊतक", "मानव पाचन तंत्र", "श्वसन और गैसों का परिवहन", "आनुवंशिकी के मूल सिद्धांत", "विकासवाद", "पारिस्थितिकी", "जैव विविधता और संरक्षण"],
    "इतिहास": ["इतिहास के स्रोत और उनका मूल्यांकन", "प्राचीन भारतीय सभ्यताएँ", "मौर्य और गुप्त काल", "मध्यकालीन समाज और संस्कृति", "औपनिवेशिक शासन", "1857 का विद्रोह", "राष्ट्रीय आंदोलन", "संविधान निर्माण की ऐतिहासिक पृष्ठभूमि", "विश्व युद्धों के प्रभाव", "इतिहास लेखन की पद्धतियाँ"],
    "भूगोल": ["भूगोल की प्रकृति और क्षेत्र", "पृथ्वी की आंतरिक संरचना", "भू-आकृतिक प्रक्रियाएँ", "जलवायु और मौसम", "भारत की नदियाँ", "जनसंख्या वितरण", "संसाधन और सतत विकास", "कृषि भूगोल", "मानचित्र और स्थानिक आँकड़े", "पर्यावरणीय चुनौतियाँ"],
    "राजनीति विज्ञान": ["राज्य, राष्ट्र और संप्रभुता", "संविधानवाद और मौलिक अधिकार", "विधायिका, कार्यपालिका और न्यायपालिका", "संघीय व्यवस्था", "लोकतांत्रिक प्रतिनिधित्व", "राजनीतिक विचारधाराएँ", "न्याय, स्वतंत्रता और समानता", "अंतरराष्ट्रीय संबंधों की मूल बातें", "लोक नीति विश्लेषण", "तुलनात्मक राजनीति"],
    "अर्थशास्त्र": ["मांग और आपूर्ति", "उपभोक्ता व्यवहार", "उत्पादन और लागत", "बाजार के प्रकार", "राष्ट्रीय आय की अवधारणा", "मुद्रास्फीति और बेरोजगारी", "बैंकिंग और मुद्रा", "राजकोषीय नीति", "अंतरराष्ट्रीय व्यापार", "विकास और असमानता"],
    "लेखाशास्त्र": ["लेखांकन के सिद्धांत", "जर्नल और लेजर", "ट्रायल बैलेंस", "बैंक मिलान विवरण", "अवमूल्यन", "वित्तीय विवरण", "साझेदारी लेखांकन", "कंपनी खातों की मूल बातें", "नकद प्रवाह विवरण", "वित्तीय विवरणों का विश्लेषण"],
    "व्यवसाय अध्ययन": ["व्यवसाय की प्रकृति और उद्देश्य", "प्रबंधन के सिद्धांत", "योजना और संगठन", "मानव संसाधन प्रबंधन", "विपणन के सिद्धांत", "वित्तीय प्रबंधन", "उद्यमिता", "व्यावसायिक नैतिकता", "उपभोक्ता संरक्षण", "व्यावसायिक वातावरण"],
    "वनस्पति विज्ञान": ["पादप कोशिका और ऊतक", "पादप वर्गिकी के सिद्धांत", "शैवाल और कवक", "पादप शरीर क्रिया विज्ञान", "प्रकाश संश्लेषण", "पादप प्रजनन", "आनुवंशिकी और पादप प्रजनन", "पारिस्थितिकी", "पादप जैव प्रौद्योगिकी", "पादप रोग विज्ञान"],
    "प्राणी विज्ञान": ["प्राणी जगत का वर्गीकरण", "ऊतक और अंग तंत्र", "कोशिका जीवविज्ञान", "मानव शरीर क्रिया विज्ञान", "आनुवंशिकी", "विकास और प्राकृतिक चयन", "प्राणी व्यवहार", "पारिस्थितिकी और जनसंख्या", "प्रतिरक्षा विज्ञान की मूल बातें", "जैव विविधता और संरक्षण"],
    "कंप्यूटर विज्ञान": ["कंप्यूटर प्रणाली की संरचना", "एल्गोरिदम और फ्लोचार्ट", "प्रोग्रामिंग की मूल अवधारणाएँ", "डेटा प्रकार और नियंत्रण संरचनाएँ", "फंक्शन और मॉड्यूल", "डेटा संरचनाएँ", "डेटाबेस की मूल बातें", "नेटवर्क और इंटरनेट", "ऑपरेटिंग सिस्टम", "साइबर सुरक्षा के सिद्धांत"],
    "सांख्यिकी": ["वर्णनात्मक सांख्यिकी", "केन्द्रीय प्रवृत्ति के माप", "प्रसरण और मानक विचलन", "प्रायिकता के सिद्धांत", "यादृच्छिक चर", "प्रतिचयन और वितरण", "सहसंबंध और प्रतिगमन", "परिकल्पना परीक्षण", "विश्वास अंतराल", "सांख्यिकीय निष्कर्षों की व्याख्या"],
    "वित्तीय लेखांकन": ["लेखांकन समीकरण", "जर्नल प्रविष्टियाँ", "लेजर और ट्रायल बैलेंस", "वित्तीय विवरण", "अवमूल्यन पद्धतियाँ", "इन्वेंटरी मूल्यांकन", "कंपनी वित्तीय विवरण", "नकद प्रवाह विवरण", "लेखांकन मानक", "वित्तीय अनुपात"],
    "व्यावसायिक कानून": ["भारतीय संविदा की मूल अवधारणाएँ", "प्रस्ताव और स्वीकृति", "प्रतिफल और संविदा की वैधता", "क्षतिपूर्ति और गारंटी", "एजेंसी", "विक्रय के सिद्धांत", "कंपनी की कानूनी पहचान", "उपभोक्ता अधिकार", "व्यापारिक दायित्व", "कानूनी केस विश्लेषण"],
    "कराधान": ["कराधान की मूल अवधारणाएँ", "प्रत्यक्ष और अप्रत्यक्ष कर", "आय के शीर्ष", "कटौतियों की अवधारणा", "GST की संरचना", "इनपुट टैक्स क्रेडिट", "कर अनुपालन", "कर नियोजन और कर चोरी में अंतर", "कर गणना के उदाहरण", "वर्तमान नियमों की आधिकारिक जाँच"],
    "लागत लेखांकन": ["लागत की अवधारणा और वर्गीकरण", "लागत पत्रक", "सामग्री लागत", "श्रम लागत", "ओवरहेड का आवंटन", "जॉब और बैच costing", "प्रक्रिया costing", "मानक लागत", "सीमांत लागत", "लागत नियंत्रण"],
    "लेखापरीक्षा": ["लेखापरीक्षा का उद्देश्य", "ऑडिट साक्ष्य", "आंतरिक नियंत्रण", "ऑडिट योजना", "जोखिम मूल्यांकन", "वाउचिंग और सत्यापन", "ऑडिट रिपोर्ट", "नैतिकता और स्वतंत्रता", "आंतरिक लेखापरीक्षा", "ऑडिट केस अध्ययन"],
    "शिक्षाशास्त्र": ["शिक्षा की अवधारणा और उद्देश्य", "सीखने के सिद्धांत", "बाल विकास", "शिक्षण-अधिगम प्रक्रिया", "पाठ्यचर्या और मूल्यांकन", "समावेशी शिक्षा", "शैक्षिक मनोविज्ञान", "शोध की मूल बातें", "शिक्षा में तकनीक", "शिक्षा नीति का विश्लेषण"],
    "समाजशास्त्र": ["समाजशास्त्र का परिचय", "समाज और समुदाय", "संस्कृति और समाजीकरण", "सामाजिक स्तरीकरण", "जाति और वर्ग", "परिवार और विवाह", "सामाजिक परिवर्तन", "प्रमुख समाजशास्त्रीय विचारक", "अनुसंधान पद्धति", "समकालीन सामाजिक मुद्दे"],
    "वित्तीय लेखांकन": ["लेखांकन समीकरण", "जर्नल प्रविष्टियाँ", "लेजर और ट्रायल बैलेंस", "वित्तीय विवरण", "अवमूल्यन पद्धतियाँ", "इन्वेंटरी मूल्यांकन", "कंपनी वित्तीय विवरण", "नकद प्रवाह विवरण", "लेखांकन मानक", "वित्तीय अनुपात"],
    "उन्नत लेखांकन": ["कंपनी विलय का लेखांकन", "समेकित वित्तीय विवरण", "शाखा लेखांकन", "लीज लेखांकन की अवधारणा", "वित्तीय साधनों का परिचय", "लेखांकन मानकों का अनुप्रयोग", "नकद प्रवाह विश्लेषण", "वित्तीय विवरणों का तुलनात्मक अध्ययन", "लेखांकन अनुमान और निर्णय", "उन्नत केस अध्ययन"],
    "कॉर्पोरेट वित्त": ["वित्तीय प्रबंधन के उद्देश्य", "समय मूल्य और नकदी प्रवाह", "पूँजी बजटिंग", "पूँजी की लागत", "पूँजी संरचना", "लाभांश नीति", "कार्यशील पूँजी प्रबंधन", "जोखिम और प्रतिफल", "वित्तीय अनुपात विश्लेषण", "कॉर्पोरेट मूल्यांकन"],
    "व्यावसायिक अनुसंधान": ["अनुसंधान समस्या की पहचान", "साहित्य समीक्षा", "अनुसंधान डिजाइन", "नमूना चयन", "प्रश्नावली निर्माण", "डेटा की विश्वसनीयता", "मात्रात्मक और गुणात्मक विधियाँ", "परिकल्पना परीक्षण", "शोध नैतिकता", "रिपोर्ट लेखन"],
    "व्यवसाय प्रबंधन": ["प्रबंधन विचारधारा का विकास", "रणनीतिक प्रबंधन", "संगठनात्मक व्यवहार", "नेतृत्व और प्रेरणा", "निर्णय निर्माण", "मानव संसाधन रणनीति", "परिवर्तन प्रबंधन", "संचालन प्रबंधन", "व्यवसाय नैतिकता", "प्रबंधन केस विश्लेषण"],
    "उन्नत लेखांकन": ["कंपनी विलय का लेखांकन", "समेकित वित्तीय विवरण", "शाखा लेखांकन", "लीज लेखांकन की अवधारणा", "वित्तीय साधनों का परिचय", "लेखांकन मानकों का अनुप्रयोग", "नकद प्रवाह विश्लेषण", "वित्तीय विवरणों का तुलनात्मक अध्ययन", "लेखांकन अनुमान और निर्णय", "उन्नत केस अध्ययन"],
}

def slugify(value):
    # ASCII slug keeps URL safe; date prefix guarantees daily uniqueness.
    value = value.lower()
    value = re.sub(r"[^a-z0-9]+", "-", value).strip("-")
    return value or "study-guide"

def word_count(text):
    return len(re.findall(r"\S+", text))

def choose_lesson():
    """Har 9 din mein har course ki baari; us course ke subjects bhi rotate hon."""
    day_number = (TODAY - dt.date(2026, 11, 6)).days

    # Course rotation: Class 10, 11, 12, B.A., B.Sc., B.Com., M.A., M.Sc., M.Com.
    course_index = day_number % len(COURSES)
    course, subjects = COURSES[course_index]

    # Jab wahi course 9 din baad aaye, agla subject choose ho.
    course_cycle = day_number // len(COURSES)
    subject_index = (course_cycle + course_index) % len(subjects)
    subject = subjects[subject_index]

    # Ek subject ke topics us course-subject ki agli baari par aage badhen.
    subject_cycle = course_cycle // len(subjects)
    topic_list = TOPICS.get(subject, [
        "विषय की मूल अवधारणाएँ", "प्रमुख सिद्धांत और उनके अनुप्रयोग",
        "उदाहरणों द्वारा विषय की समझ", "विश्लेषण और अभ्यास"
    ])
    topic = topic_list[subject_cycle % len(topic_list)]
    return course, subject, topic, day_number

def generate_article(course, subject, topic):
    prompt = f"""
आप SarkariJobAlert वेबसाइट के School & Exam Guide अनुभाग के लिए अनुभवी हिंदी शिक्षक और शैक्षिक लेखक हैं।

आज का निर्धारित पाठ:
स्तर/कक्षा: {course}
विषय: {subject}
मुख्य विषय: {topic}
तिथि: {TODAY.isoformat()}

बहुत महत्वपूर्ण निर्देश:
- यहाँ "हिंदी" लेख की भाषा/माध्यम है, जरूरी नहीं कि विषय हिंदी हो। निर्धारित विषय {subject} ही पढ़ाएँ।
- गणित का पाठ गणित पर, विज्ञान का पाठ विज्ञान पर, इतिहास का पाठ इतिहास पर और इसी तरह दिए गए विषय पर ही केंद्रित हो।
- केवल तभी हिंदी व्याकरण, साहित्य या हिंदी भाषा पढ़ाएँ जब निर्धारित विषय स्वयं "हिंदी" हो।
- अंग्रेज़ी विषय होने पर भी पूरी व्याख्या सरल हिंदी में दें; अंग्रेज़ी के उदाहरण/वाक्य जहाँ जरूरी हों, उनके हिंदी अर्थ और समझ भी दें।
- सूत्र, समीकरण, तकनीकी शब्द और आवश्यक अंग्रेज़ी शब्द रख सकते हैं, लेकिन उनका अर्थ सरल हिंदी में समझाएँ।

लक्ष्य:
- पूरा लेख स्वाभाविक, सरल और स्पष्ट हिंदी में लिखें। अंग्रेज़ी शब्द केवल जहाँ आवश्यक हों, वहाँ हिंदी अर्थ के साथ दें।
- लगभग 1,000 से 1,500 हिंदी शब्द लिखें। अनावश्यक दोहराव या शब्द बढ़ाने के लिए खाली बातें न जोड़ें।
- विषय को शिक्षक की तरह चरणबद्ध समझाएँ। परिभाषा, पृष्ठभूमि, मुख्य अवधारणाएँ, उपशीर्षक, उदाहरण/हल किए हुए उदाहरण और वास्तविक जीवन/परीक्षा में उपयोग शामिल करें।
- इस स्तर के अनुरूप कठिनाई रखें। Class 10 के लिए सरल, B.A./B.Sc./B.Com. के लिए स्नातक स्तर, M.A./M.Sc./M.Com. के लिए परास्नातक स्तर की व्याख्या दें।
- पाठ्यक्रम, बोर्ड, विश्वविद्यालय, परीक्षा तिथि, नियम, आँकड़े या पाठ्यपुस्तक का ऐसा दावा न करें जिसकी पुष्टि उपलब्ध न हो। अलग-अलग बोर्ड/विश्वविद्यालयों के पाठ्यक्रम भिन्न हो सकते हैं; पाठ को सामान्य अध्ययन सामग्री के रूप में प्रस्तुत करें और पाठक को अपने वर्तमान आधिकारिक पाठ्यक्रम से मिलाने की सलाह दें।
- किसी किताब/वेबसाइट का पाठ ज्यों का त्यों न लें। सामग्री मौलिक ढंग से समझाएँ।
- अंत में 10 महत्वपूर्ण प्रश्न-उत्तर और 10 MCQ दें। हर MCQ के चार विकल्प (क, ख, ग, घ) हों और अंत में उत्तरमाला तथा संक्षिप्त कारण दें।
- लेख में वास्तविक शैक्षिक मूल्य हो; केवल पढ़ाई की सामान्य सलाह न लिखें।
- यदि किसी विषय में सटीक तथ्य पर अनिश्चितता हो, तो अनुमान लगाने के बजाय सावधानी से समझाएँ।

लेख का प्रारूप:
शीर्षक
भूमिका
अध्ययन के उद्देश्य
विषय की विस्तृत व्याख्या (कम से कम 5 स्पष्ट उपशीर्षक)
उदाहरण / हल किया हुआ उदाहरण
महत्वपूर्ण बिंदु
10 महत्वपूर्ण प्रश्न-उत्तर
10 बहुविकल्पीय प्रश्न
उत्तरमाला व संक्षिप्त व्याख्या
निष्कर्ष
अस्वीकरण: यह सामान्य शैक्षिक सामग्री है; अपने बोर्ड/विश्वविद्यालय के नवीनतम आधिकारिक पाठ्यक्रम और निर्देश अवश्य जाँचें।

केवल लेख का पाठ लौटाएँ। Markdown headings और numbered lists इस्तेमाल कर सकते हैं। JSON, code fence या अतिरिक्त टिप्पणी न दें।
"""
    response = gemini_generate_with_fallback(
        {
            "contents": [{"role": "user", "parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": 0.65,
                "topP": 0.9,
                "maxOutputTokens": 8500
            }
        }
    )
    try:
        payload = response.json()
    except ValueError:
        raise RuntimeError(f"Gemini ne non-JSON response diya (HTTP {response.status_code}).")
    if not response.ok:
        message = payload.get("error", {}).get("message", "Unknown Gemini API error")
        raise RuntimeError(f"Gemini API HTTP {response.status_code}: {message[:900]}")
    candidates = payload.get("candidates") or []
    parts = (candidates[0].get("content", {}).get("parts", []) if candidates else [])
    article = "\n".join(p.get("text", "") for p in parts if p.get("text")).strip()
    if not article:
        reason = candidates[0].get("finishReason", "No candidate") if candidates else "No candidate"
        raise RuntimeError(f"Gemini ne article text nahi diya. Finish reason: {reason}")
    return article

def main():
    if not SUPABASE_URL.startswith("https://") or not SERVICE_KEY:
        raise RuntimeError("Missing Supabase credentials or invalid SUPABASE_URL.")
    if not GEMINI_API_KEY:
        raise RuntimeError("GEMINI_API_KEY GitHub Secret missing hai.")

    course, subject, topic, day_number = choose_lesson()
    title = f"{course} {subject}: {topic}"
    slug = f"{TODAY.isoformat()}-{slugify(course)}-{slugify(subject)}-{day_number}"
    print(f"Generating Hindi lesson: {title}", flush=True)

    # Prevent duplicate publishing if workflow is manually re-run on the same date.
    check = requests.get(
        TABLE_URL,
        headers=HEADERS,
        params={"slug": f"eq.{slug}", "select": "id,status"},
        timeout=30
    )
    check.raise_for_status()
    existing = check.json()
    if existing:
        row = existing[0]
        if STATUS == "published" and row.get("status") != "published":
            update = requests.patch(
                TABLE_URL,
                headers=HEADERS,
                params={"slug": f"eq.{slug}"},
                json={
                    "status": "published",
                    "published_at": dt.datetime.now(dt.timezone.utc).isoformat()
                },
                timeout=30
            )
            update.raise_for_status()
            print(f"Existing article promoted to published: {title}")
        else:
            print(f"Today's article already exists; no duplicate created: {title}")
        return

    article = generate_article(course, subject, topic)
    count = word_count(article)

    # Do not launch a second full article generation: that can exceed the
    # GitHub Actions time limit. Keep the article unpublished if too short.
    if count < 700:
        raise RuntimeError(
            f"Generated article is too short ({count} words). "
            "Not published; retry the workflow later."
        )

    # Build a short excerpt locally from the article to avoid a second Gemini
    # API request, which previously caused long waits and extra 503 errors.
    plain_excerpt = re.sub(r"[*_#>`\\-]+", " ", article)
    excerpt_words = re.findall(r"\S+", plain_excerpt)
    excerpt = " ".join(excerpt_words[:45]).strip()
    if len(excerpt_words) < 20:
        excerpt = (
            f"{course} के विद्यार्थियों के लिए {subject} में {topic} की "
            "व्याख्या, उदाहरण, महत्वपूर्ण प्रश्न और अभ्यास MCQ।"
        )

    payload = {
        "slug": slug,
        "title": title,
        "excerpt": excerpt[:1000],
        "content": article,
        "grade": course,
        "subject": subject,
        "article_type": "study_guide",
        "status": STATUS
    }
    if STATUS == "published":
        payload["published_at"] = dt.datetime.now(dt.timezone.utc).isoformat()

    result = requests.post(TABLE_URL, headers=HEADERS, json=payload, timeout=45)
    if not result.ok:
        raise RuntimeError(f"Supabase insert failed HTTP {result.status_code}: {result.text[:1000]}")

    print(f"Created {STATUS} Hindi study guide: {title} ({count} words)", flush=True)

if __name__ == "__main__":
    main()
