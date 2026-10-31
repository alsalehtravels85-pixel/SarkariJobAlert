import os
import re
import datetime as dt
from zoneinfo import ZoneInfo
import requests

# SarkariJobAlert - School & Higher Education Study Guide publisher
# AdSense-conscious defaults:
# - No fake exam dates, marks, eligibility, or official claims.
# - Adds a clear educational disclaimer and encourages official syllabus checks.
# - Uses India-local dates, unique daily slugs and duplicate checks.
# - Creates drafts by default so thin/repetitive text is not pushed live automatically.
# IMPORTANT: Code alone cannot guarantee AdSense approval; each article needs real value,
# originality, accuracy, and editorial review.

SUPABASE_URL = os.environ["SUPABASE_URL"].rstrip("/")
SERVICE_KEY = os.environ["SUPABASE_SERVICE_ROLE_KEY"]
TODAY = dt.datetime.now(ZoneInfo("Asia/Kolkata")).date()
# Safe default: prepare as draft for editorial review. Set GitHub Actions env
# AUTO_PUBLISH_STUDY_GUIDES=true only after reviewing content quality.
AUTO_PUBLISH = os.getenv("AUTO_PUBLISH_STUDY_GUIDES", "false").strip().lower() == "true"
PUBLISH_STATUS = "published" if AUTO_PUBLISH else "draft"
HEADERS = {
    "apikey": SERVICE_KEY,
    "Authorization": f"Bearer {SERVICE_KEY}",
    "Content-Type": "application/json",
    "Prefer": "return=representation",
}
TABLE_URL = f"{SUPABASE_URL}/rest/v1/school_articles"

# Keep existing school grades and add common undergraduate/postgraduate courses.
COURSES = [
    {
        "name": "Class 9",
        "subjects": ["Mathematics", "Science", "Hindi", "English", "Social Science"],
        "guidance": "Strong foundation banayein, textbook ko dhyan se padhein aur doubts ko jaldi clear karein."
    },
    {
        "name": "Class 10",
        "subjects": ["Mathematics", "Science", "Hindi", "English", "Social Science"],
        "guidance": "Current board syllabus se preparation checklist match karein aur timed practice karein."
    },
    {
        "name": "Class 11",
        "subjects": ["Mathematics", "Physics", "Chemistry", "Biology", "Hindi", "English", "Accountancy", "Economics"],
        "guidance": "Conceptual understanding par focus karein aur weekly revision se backlog kam rakhein."
    },
    {
        "name": "Class 12",
        "subjects": ["Mathematics", "Physics", "Chemistry", "Biology", "Hindi", "English", "Accountancy", "Economics", "Business Studies", "History", "Geography", "Political Science"],
        "guidance": "Syllabus ke saath regular revision, answer-writing aur timed practice ka balance rakhein."
    },
    {
        "name": "B.A.",
        "subjects": ["Hindi", "English", "History", "Political Science", "Sociology", "Economics", "Geography", "Education"],
        "guidance": "University ke semester syllabus, prescribed readings aur answer-writing expectations ko follow karein."
    },
    {
        "name": "B.Sc.",
        "subjects": ["Physics", "Chemistry", "Mathematics", "Botany", "Zoology", "Computer Science", "Statistics"],
        "guidance": "Theory ke saath numericals, practical records, lab safety aur prescribed experiments par dhyan dein."
    },
    {
        "name": "B.Com.",
        "subjects": ["Financial Accounting", "Business Law", "Economics", "Business Studies", "Taxation", "Cost Accounting", "Auditing"],
        "guidance": "Concepts ke saath formats, calculations, journal entries aur case-based questions ki practice karein."
    },
    {
        "name": "M.A.",
        "subjects": ["Hindi", "English", "History", "Political Science", "Sociology", "Economics", "Education"],
        "guidance": "Advanced readings, critical analysis, research methods aur evidence-based long answers par focus karein."
    },
    {
        "name": "M.Sc.",
        "subjects": ["Physics", "Chemistry", "Mathematics", "Botany", "Zoology", "Computer Science", "Statistics"],
        "guidance": "Advanced concepts, research papers prescribed by the university, practical work aur problem-solving ko balance karein."
    },
    {
        "name": "M.Com.",
        "subjects": ["Advanced Accounting", "Corporate Finance", "Business Research", "Taxation", "Auditing", "Business Management"],
        "guidance": "Accounting standards, analytical problems, research methodology aur university-specific readings ko priority dein."
    },
]

TOPICS = [
    (
        "Study timetable kaise banayein",
        "Apne available time aur syllabus ko dekh kar realistic weekly timetable banayein. Mushkil topics ko chhote parts mein baantein aur study sessions ke beech short breaks rakhein.",
        "Roz ke 3 priority tasks likhein. Reading, notes, practice aur revision ko alag blocks dein. Hafte ke aakhir mein plan review karke agle hafte ko adjust karein."
    ),
    (
        "Active recall aur revision ke tareeqe",
        "Sirf notes dobara padhne ke bajaye topic band karke apni zubaan mein samjhaane ya key points likhne ki koshish karein. Isse pata chalega ki kaun se concepts abhi clear nahi hain.",
        "Short summary banayein, phir bina dekhe questions solve karein. Jo points yaad na aayein unhe mark karein aur 1 din, 1 hafte aur phir zaroorat ke mutabiq revise karein."
    ),
    (
        "Practice questions se taiyari",
        "Pehle concept aur solved examples samjhein, phir khud questions solve karein. Galat answer ko sirf correct na karein; galti ki wajah bhi likhein.",
        "Error notebook banayein. Har galti ke saamne topic, galti ka reason aur sahi method note karein. Kuch din baad wahi question dobara solve karein."
    ),
    (
        "Exam answer writing ko behtar banana",
        "Answer ko question ke mutabiq rakhein. Jahan zaroori ho headings, examples, formulae, labelled diagrams ya relevant evidence ka use karein. Sirf lamba answer likhna achhe answer ki guarantee nahi.",
        "Practice paper ko time limit mein solve karein. Baad mein dekhein ki answer ne question ke sab parts cover kiye hain, reasoning clear hai aur presentation readable hai."
    ),
    (
        "Notes aur study material organize karna",
        "Notes ko textbook ki copy banane ke bajaye definitions, core ideas, examples, formulae aur common mistakes ke short summaries mein badlein.",
        "Har unit ke liye ek revision sheet rakhein. File ya notebook par course, semester/class, subject aur unit ka naam likhein taaki exam se pehle material jaldi mil sake."
    ),
]

SUBJECT_TIPS = {
    "Mathematics": "Formula ka meaning samjhein, solution ke steps likhein aur answer ko dobara check karein.",
    "Science": "Theory, diagrams, practical examples aur numericals ko relevant syllabus ke hisaab se saath revise karein.",
    "Physics": "Concepts, units, derivations aur numerical problem-solving ki regular practice karein.",
    "Chemistry": "Reactions, equations, concepts aur numerical problems ko syllabus ke mutabiq organize karein.",
    "Biology": "Processes ko step-by-step samjhein, diagrams ko label karein aur scientific terms accurately use karein.",
    "Hindi": "Text ka central idea, author/poet ka perspective, vocabulary, grammar aur writing practice karein.",
    "English": "Reading, grammar, vocabulary aur structured writing ki regular practice karein.",
    "Social Science": "Key concepts, timelines, maps, examples aur cause-effect relations ko short notes mein rakhein.",
    "History": "Events ke context, chronology, causes, effects aur different interpretations ko compare karein.",
    "Political Science": "Core concepts, institutions, arguments aur relevant examples ko clear headings mein explain karein.",
    "Economics": "Definitions, graphs, assumptions, data interpretation aur numerical practice ko syllabus ke mutabiq karein.",
    "Accountancy": "Accounting concepts, formats, journal entries, calculations aur working notes ko step-by-step practice karein.",
    "Financial Accounting": "Prescribed accounting principles, formats, journal entries aur final accounts ki practice karein.",
    "Advanced Accounting": "University-prescribed standards, consolidation or other advanced topics ko official course outline ke mutabiq padhein.",
    "Business Law": "Relevant legal principles, definitions aur case-based application ko prescribed textbook se verify karein.",
    "Taxation": "Applicable assessment year aur current official rules verify karein; old rates ya outdated examples ko current advice na samjhein.",
    "Cost Accounting": "Cost concepts, formulas, working notes aur numerical solutions ko step-by-step practice karein.",
    "Auditing": "Audit concepts, standards prescribed by the course, evidence and reporting principles ko structured notes mein rakhein.",
    "Computer Science": "Programming concepts, algorithms, code tracing and practical exercises ko regularly practice karein.",
    "Statistics": "Formula selection, assumptions, calculations and interpretation of results ko saath practice karein.",
    "Sociology": "Key theories, thinkers, concepts and examples ko critical comparison ke saath explain karein.",
    "Geography": "Concepts, maps, diagrams, data and field/practical components ko syllabus ke hisaab se revise karein.",
    "Education": "Learning theories, classroom applications, terminology and critical reflection ko connect karein.",
    "Business Studies": "Business concepts, examples, case-based questions and structured explanations ki practice karein.",
    "Corporate Finance": "Financial concepts, assumptions, calculations and interpretation ko step-by-step explain karein.",
    "Business Research": "Research question, methodology, ethical considerations and analysis ko university guidance ke mutabiq padhein.",
    "Business Management": "Management concepts, frameworks and practical examples ko critical analysis ke saath padhein.",
    "Botany": "Scientific terminology, diagrams, classification and practical observations ko accurately record karein.",
    "Zoology": "Processes, classification, diagrams and practical concepts ko prescribed syllabus se match karein.",
}

def slugify(value):
    value = value.lower().strip()
    value = re.sub(r"[^a-z0-9]+", "-", value)
    return value.strip("-")

def build_long_content(course, subject, topic, intro, method):
    subject_focus = SUBJECT_TIPS.get(
        subject,
        "Subject ke core concepts ko samjhein, prescribed readings use karein aur practice ko course requirements ke mutabiq rakhein."
    )
    course_focus = course["guidance"]
    sections = [
        f"{course['name']} {subject}: {topic}\n\n"
        f"Yeh study guide {course['name']} ke learners ke liye {subject} ki padhai ko organize karne par focused hai. {intro}",
        "1. Learning goal set karein\n"
        "Study session se pehle ek clear goal likhein: kaunsa concept samajhna hai, kaunsa section padhna hai ya kaun se questions practice karne hain. Goal ko manageable rakhein aur session ke end mein apni progress check karein.",
        f"2. Subject-specific approach\n{subject_focus} "
        "Prescribed textbook, course outline aur teacher/university ke recommended material ko primary reference banayein. Online notes ko samajhne mein madad ke liye use karein, lekin unhe official syllabus ka replacement na samjhein.",
        f"3. Course ke hisaab se planning\n{course_focus} "
        "School board ya university ke current academic session, semester scheme, syllabus aur assessment instructions ko official website ya department notice se verify karein.",
        f"4. Practical study routine\n{method} "
        "Ek possible routine hai: focused reading, short break, practice/recall aur end mein summary. Total time apne schedule, subject difficulty aur upcoming assessment ke mutabiq adjust karein.",
        "5. Useful notes banayein\n"
        "Notes mein main concepts, definitions, examples, formulae, diagrams, important questions aur apni common mistakes ko alag headings mein rakhein. Sirf copied paragraphs se bachkar apni understanding ke short summaries likhein.",
        "6. Practice aur self-check\n"
        "Topic ke baad khud ko explain karein ya relevant practice questions solve karein. Numerical subjects mein working steps rakhein; theory subjects mein argument, examples aur clear structure par focus karein. Course-specific assessment pattern ko official guidance se check karein.",
        "7. Mistake log aur revision\n"
        "Jo concept samajh na aaye ya question galat ho, uska reason note karein. Mistakes ko concept gap, careless error, unclear question ya time management jaise categories mein baantna helpful ho sakta hai. Baad mein un topics ko dobara test karein.",
        "8. Weekly progress review\n"
        "Hafte mein ek baar completed topics, pending work aur weak areas ka review karein. Agle hafte ke targets isi review se banayein. Agar plan consistently complete nahi ho raha, to targets ko realistic banayein.",
        "9. Study material ko verify karein\n"
        "Course aur syllabus university/board ke hisaab se alag ho sakte hain. Kisi blog, social media post ya old PDF ko final official information na maanein. Syllabus, exam dates, paper pattern aur rules ko relevant institution ke official source se confirm karein.",
        "10. Quick checklist\n"
        "• Aaj ka learning target clear tha?\n"
        "• Prescribed material se topic padha?\n"
        "• Bina dekhe recall ya practice ki?\n"
        "• Galtiyon aur doubts ko note kiya?\n"
        "• Next revision ka target set kiya?",
        "About this guide\n"
        "Yeh general educational guidance hai, official syllabus, university notice, exam paper, professional advice ya guaranteed result nahi. Course structure aur assessment rules institution ke mutabiq badal sakte hain; current information ke liye apne board, university ya department ki official website/notice check karein."
    ]
    return "\n\n".join(sections)

def main():
    if not SUPABASE_URL.startswith("https://") or not SERVICE_KEY:
        raise RuntimeError("Missing Supabase credentials.")

    # Keep existing articles unchanged. Create one new guide per India-local day.
    # Draft is the safe default; AUTO_PUBLISH_STUDY_GUIDES=true opts into auto-publishing.
    course_subject_pairs = [
        (course, subject)
        for course in COURSES
        for subject in course["subjects"]
    ]
    cycle_size = len(course_subject_pairs) * len(TOPICS)
    index = (TODAY - dt.date(2026, 1, 1)).days % cycle_size
    course, subject = course_subject_pairs[index // len(TOPICS)]
    topic, intro, method = TOPICS[index % len(TOPICS)]

    course_name = course["name"]
    title = f"{course_name} {subject}: {topic}"
    slug = f"{TODAY.isoformat()}-{slugify(course_name)}-{slugify(subject)}-{index % len(TOPICS) + 1}"
    excerpt = (
        f"{course_name} ke {subject} learners ke liye {topic.lower()} par "
        "practical study planning, revision aur self-check guidance."
    )
    content = build_long_content(course, subject, topic, intro, method)

    # Check slug to avoid creating duplicate rows on reruns.
    check = requests.get(
        TABLE_URL,
        headers=HEADERS,
        params={"slug": f"eq.{slug}", "select": "id"},
        timeout=25,
    )
    check.raise_for_status()
    if check.json():
        print(f"Article already exists for {TODAY}; no duplicate created.")
        return

    payload = {
        "slug": slug,
        "title": title,
        "excerpt": excerpt,
        "content": content,
        "grade": course_name,
        "subject": subject,
        "article_type": "study_guide",
        "status": PUBLISH_STATUS,
    }
    if PUBLISH_STATUS == "published":
        payload["published_at"] = dt.datetime.now(dt.timezone.utc).isoformat()
    response = requests.post(TABLE_URL, headers=HEADERS, json=payload, timeout=25)
    response.raise_for_status()
    print(f"Created {PUBLISH_STATUS} study guide: {title}")

if __name__ == "__main__":
    main()
