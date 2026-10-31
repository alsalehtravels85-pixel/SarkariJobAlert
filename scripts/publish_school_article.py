import os
import re
import datetime as dt
from zoneinfo import ZoneInfo
import requests

# SarkariJobAlert: publish exactly one educational article per scheduled run/day.
# Required GitHub secrets: SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY
# GitHub Actions variable: AUTO_PUBLISH_STUDY_GUIDES=true

SUPABASE_URL = os.environ["SUPABASE_URL"].rstrip("/")
SERVICE_KEY = os.environ["SUPABASE_SERVICE_ROLE_KEY"]
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

# The rotation deliberately covers school and college/postgraduate courses.
COURSES = [
    ("Class 9", ["Mathematics", "Science", "Hindi", "English", "Social Science"], "Build fundamentals, read the prescribed textbook and clear doubts early."),
    ("Class 10", ["Mathematics", "Science", "Hindi", "English", "Social Science"], "Match preparation to the current board syllabus and practise timed questions."),
    ("Class 11", ["Mathematics", "Physics", "Chemistry", "Biology", "English", "Accountancy", "Economics"], "Focus on concepts and weekly revision to avoid backlog."),
    ("Class 12", ["Mathematics", "Physics", "Chemistry", "Biology", "English", "Accountancy", "Economics", "Business Studies", "History", "Geography", "Political Science"], "Balance syllabus coverage, revision, answer writing and timed practice."),
    ("B.A.", ["Hindi", "English", "History", "Political Science", "Sociology", "Economics", "Geography", "Education"], "Use the university's semester syllabus and prescribed readings."),
    ("B.Sc.", ["Physics", "Chemistry", "Mathematics", "Botany", "Zoology", "Computer Science", "Statistics"], "Balance theory, problem-solving and course-prescribed practical work."),
    ("B.Com.", ["Financial Accounting", "Business Law", "Economics", "Business Studies", "Taxation", "Cost Accounting", "Auditing"], "Practise concepts, calculations, formats and case-based questions."),
    ("M.A.", ["Hindi", "English", "History", "Political Science", "Sociology", "Economics", "Education"], "Focus on critical analysis, research methods and evidence-based answers."),
    ("M.Sc.", ["Physics", "Chemistry", "Mathematics", "Botany", "Zoology", "Computer Science", "Statistics"], "Combine advanced concepts, problem-solving and prescribed practical/research work."),
    ("M.Com.", ["Advanced Accounting", "Corporate Finance", "Business Research", "Taxation", "Auditing", "Business Management"], "Practise analytical problems and follow university-prescribed readings."),
]

TOPICS = [
    ("Concepts ko asaani se samajhne ka tareeqa", "Topic ko chhote concepts mein divide karein. Har concept ke liye definition, example aur apne shabdon mein explanation likhein.", "Padhne ke baad book band karke concept samjhaayein. Jahan ruk jaayein, wahi part dobara padhein aur ek naya example solve karein."),
    ("Effective revision plan kaise banayein", "Revision ko sirf exam se pehle ke liye na chhodein. Naye topic ke baad short recap karein aur weak topics ko schedule mein dobara rakhein.", "Ek revision sheet banayein. Agle din, hafte ke andar aur phir zaroorat ke mutabiq topic test karein; timing apne workload ke hisaab se rakhein."),
    ("Practice questions se learning behtar karein", "Solved example samajhne ke baad usi concept par khud question attempt karein. Galat answer ke peeche ka reason samajhna zaroori hai.", "Mistake log mein topic, galti ka reason aur correct method likhein. Kuch din baad question dobara solve karke progress check karein."),
    ("Exam answers ko structured kaise likhein", "Answer ko question ke demand ke mutabiq rakhein. Theory mein clear points aur examples; numerical work mein formula, steps aur units dikhayein.", "Ek practice answer ko time limit mein likhein. Check karein ki question ke sab parts cover hue, explanation clear hai aur presentation readable hai."),
    ("Notes aur study material organize karein", "Notes ko textbook ki copy na banayein. Key ideas, definitions, formulas, examples, diagrams aur common mistakes ko headings ke saath summarize karein.", "Har unit ki concise revision sheet rakhein aur us par class/course, subject aur unit mark karein. Syllabus se bahar ki information ko official course material se verify karein."),
]

SUBJECT_TIPS = {
    "Mathematics": "Formula ka meaning samjhein, solution ke steps likhein aur final answer check karein.",
    "Science": "Concepts, diagrams, examples aur relevant numericals ko prescribed syllabus se match karein.",
    "Physics": "Concepts, units, derivations aur numerical problem-solving ki regular practice karein.",
    "Chemistry": "Reactions, equations, concepts aur numerical problems ko syllabus ke mutabiq organize karein.",
    "Biology": "Processes ko step-by-step samjhein, diagrams label karein aur scientific terms accurately use karein.",
    "Hindi": "Central idea, author/poet perspective, vocabulary, grammar aur writing practice par focus karein.",
    "English": "Reading comprehension, grammar, vocabulary aur structured writing ki practice karein.",
    "Social Science": "Key concepts, timelines, maps, examples aur cause-effect relations ke short notes banayein.",
    "History": "Chronology, context, causes, effects aur different interpretations compare karein.",
    "Political Science": "Core concepts, institutions, arguments aur relevant examples ko clear headings mein explain karein.",
    "Economics": "Definitions, graphs, assumptions, data interpretation aur numericals practise karein.",
    "Accountancy": "Accounting concepts, formats, journal entries, calculations aur working notes step-by-step practise karein.",
    "Financial Accounting": "Prescribed principles, formats, journal entries aur final accounts ki practice karein.",
    "Advanced Accounting": "Advanced topics aur standards ko university ke official course outline ke mutabiq padhein.",
    "Business Law": "Legal principles aur case-based applications ko prescribed textbook se verify karein.",
    "Taxation": "Applicable assessment year aur current official rules verify karein; old rates ko current advice na samjhein.",
    "Cost Accounting": "Cost concepts, formulas, working notes aur numerical solutions step-by-step practise karein.",
    "Auditing": "Audit concepts, prescribed standards, evidence aur reporting principles ke structured notes banayein.",
    "Computer Science": "Programming concepts, algorithms, code tracing aur practical exercises regularly practise karein.",
    "Statistics": "Formula selection, assumptions, calculations aur result interpretation saath practise karein.",
    "Sociology": "Key theories, thinkers, concepts aur examples ko critical comparison ke saath explain karein.",
    "Geography": "Concepts, maps, diagrams, data aur practical components syllabus ke hisaab se revise karein.",
    "Education": "Learning theories, classroom applications aur terminology ko examples ke saath connect karein.",
    "Business Studies": "Business concepts, examples, case-based questions aur structured explanations practise karein.",
    "Corporate Finance": "Financial concepts, assumptions, calculations aur interpretation step-by-step karein.",
    "Business Research": "Research question, methodology, ethics aur analysis ko university guidance ke mutabiq padhein.",
    "Business Management": "Management frameworks aur practical examples ko critical analysis ke saath padhein.",
    "Botany": "Scientific terminology, diagrams, classification aur practical observations accurately record karein.",
    "Zoology": "Processes, classification, diagrams aur practical concepts ko prescribed syllabus se match karein.",
}


def slugify(value):
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")


def build_content(course, subject, topic, intro, method, guidance):
    subject_tip = SUBJECT_TIPS.get(subject, "Core concepts samjhein, prescribed readings use karein aur course ke mutabiq practice karein.")
    parts = [
        f"{course} {subject}: {topic}\n\nYeh guide {course} ke learners ke liye {subject} ki padhai ko practical tareeqe se organize karne mein madad karti hai. {intro}",
        f"1. Learning goal set karein\nStudy session se pehle ek specific target likhein: concept samajhna, chapter ka section complete karna ya practice questions solve karna. Session ke end mein target check karein.",
        f"2. Subject-specific approach\n{subject_tip} Prescribed textbook, course outline aur teacher/university ke recommended material ko primary reference banayein.",
        f"3. Course ke mutabiq planning\n{guidance} Board ya university ke current academic session, syllabus aur assessment instructions ko official source se verify karein.",
        f"4. Is topic par kaam kaise karein\n{method} Apne available time aur topic ki difficulty ke mutabiq focused reading, short break, practice aur recap ka routine banayein.",
        "5. Practice aur self-check\nTopic ke baad bina notes dekhe apni understanding explain karein. Numerical subjects mein working steps rakhein; theory subjects mein argument, examples aur clear structure par focus karein.",
        "6. Common mistakes se seekhein\nJo concept samajh na aaye ya question galat ho, uska reason note karein. Galti concept gap, calculation, unclear wording ya time management ki ho sakti hai. Baad mein us topic ko dobara test karein.",
        "7. Quick checklist\n• Aaj ka learning target clear tha?\n• Prescribed material se topic padha?\n• Bina dekhe recall ya practice ki?\n• Doubts aur mistakes note ki?\n• Agli revision ka target set kiya?",
        "Important note\nYeh general educational guidance hai, official syllabus, exam notice ya guaranteed result nahi. Course structures aur assessment rules institution ke hisaab se alag ho sakte hain. Current syllabus, exam dates aur rules ke liye apne board, university ya department ki official website/notice check karein.",
    ]
    return "\n\n".join(parts)


def main():
    if not SUPABASE_URL.startswith("https://") or not SERVICE_KEY:
        raise RuntimeError("Missing Supabase credentials or invalid SUPABASE_URL.")

    pairs = [(course, subject) for course, subjects, _ in COURSES for subject in subjects]
    topic_count = len(TOPICS)
    cycle_size = len(pairs) * topic_count
    day_number = (TODAY - dt.date(2026, 1, 1)).days
    index = day_number % cycle_size
    course_name, subject = pairs[index // topic_count]
    guidance = next(item[2] for item in COURSES if item[0] == course_name)
    topic, intro, method = TOPICS[index % topic_count]
    title = f"{course_name} {subject}: {topic}"
    slug = f"{TODAY.isoformat()}-{slugify(course_name)}-{slugify(subject)}-{index % topic_count + 1}"
    excerpt = f"{course_name} ke {subject} students ke liye {topic.lower()} par practical study guidance, practice aur revision tips."
    content = build_content(course_name, subject, topic, intro, method, guidance)

    # One row per date/slug. If today's row exists as draft, promote it when auto-publish is enabled.
    check = requests.get(TABLE_URL, headers=HEADERS, params={"slug": f"eq.{slug}", "select": "id,status"}, timeout=25)
    check.raise_for_status()
    existing = check.json()
    if existing:
        row = existing[0]
        if STATUS == "published" and row.get("status") != "published":
            update = requests.patch(TABLE_URL, headers=HEADERS, params={"slug": f"eq.{slug}"}, json={"status": "published", "published_at": dt.datetime.now(dt.timezone.utc).isoformat()}, timeout=25)
            update.raise_for_status()
            print(f"Existing article promoted to published: {title}")
        else:
            print(f"Today's article already exists; no duplicate created: {title}")
        return

    payload = {"slug": slug, "title": title, "excerpt": excerpt, "content": content, "grade": course_name, "subject": subject, "article_type": "study_guide", "status": STATUS}
    if STATUS == "published":
        payload["published_at"] = dt.datetime.now(dt.timezone.utc).isoformat()
    response = requests.post(TABLE_URL, headers=HEADERS, json=payload, timeout=25)
    response.raise_for_status()
    print(f"Created {STATUS} study guide: {title}")


if __name__ == "__main__":
    main()
