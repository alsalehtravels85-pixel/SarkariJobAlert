import os
import datetime as dt
import requests

SUPABASE_URL = os.environ["SUPABASE_URL"].rstrip("/")
SERVICE_KEY = os.environ["SUPABASE_SERVICE_ROLE_KEY"]
TODAY = dt.datetime.now(dt.timezone.utc).date()
HEADERS = {
    "apikey": SERVICE_KEY,
    "Authorization": f"Bearer {SERVICE_KEY}",
    "Content-Type": "application/json",
    "Prefer": "return=representation",
}

GRADES = ["Class 9", "Class 10", "Class 11", "Class 12"]
SUBJECTS = ["Mathematics", "Science", "Hindi", "English", "Social Science"]
TOPICS = [
    ("Study timetable kaise banayein", "Har subject ke liye realistic weekly timetable banayein. Mushkil topics ko chhote parts mein baantein aur har study session ke baad 5–10 minute ka break rakhein.", "Roz ke 3 priority tasks likhein. School homework, revision aur practice ko alag blocks dein. Hafte ke ant mein dekhein ki kya complete hua aur agle hafte ka plan us hisaab se badlein."),
    ("Revision ko effective banane ke tareeqe", "Sirf kitab dobara padhne ke bajaye, topic band karke apni zubaan mein samjhaane ki koshish karein. Isse yaad ki hui baat samajh mein aati hai ya nahi, pata chalta hai.", "Ek short summary banayein, phir bina dekhe questions solve karein. Jo points yaad na aayein unhe mark karke agle revision mein pehle dekhein."),
    ("Practice questions se taiyari", "Practice karte waqt pehle concept samjhein, phir textbook examples aur chapter-end questions solve karein. Galat jawab ko sirf kaatne ke bajaye uski wajah likhein.", "Ek error notebook rakhein. Har galti ke saamne sahi method aur us topic ka naam likhein. Kuch din baad wahi sawal dobara solve karke progress check karein."),
    ("Exam se pehle answer writing", "Jawab saaf, seedhe aur question ke mutabiq likhein. Jahan zaroori ho headings, steps, formula ya labelled diagram ka use karein. Sirf lamba jawab likhna achhe answer ki guarantee nahi hota.", "Practice paper ko time limit mein solve karein. Aakhir mein spelling, calculation, units aur question ke sab parts ka jawab diya hai ya nahi, check karein."),
]
SUBJECT_TIPS = {
"Mathematics":"Formula ratne ke saath uska use samjhein. Har din kuch questions khud solve karein aur calculation steps saaf likhein.",
"Science":"Definitions, concepts, diagrams aur practical examples ko saath mein revise karein. Diagram banate waqt labels clear rakhein.",
"Hindi":"Gadya, padya, vyakaran aur writing practice ko alag sessions mein baantein. Answer mein sawal se judi baat aur saaf bhasha rakhein.",
"English":"Reading comprehension, grammar, vocabulary aur writing ko regular practice mein shamil karein. Answer likhne ke baad sentence structure check karein.",
"Social Science":"History, Geography, Civics aur Economics ke notes alag banayein. Dates, terms, maps aur cause-effect relations ko short points mein revise karein."
}
GRADE_TIPS = {
"Class 9":"Concepts aur textbook reading par mazboot buniyad banayein. Notes ko har hafte update karein.",
"Class 10":"Syllabus ko school/board ke current session se match karein. Sample papers sirf practice ke liye use karein, official pattern alag se verify karein.",
"Class 11":"Naye topics ko regular revise karein aur backlog jama na hone dein. Har chapter ke baad short test lein.",
"Class 12":"Long-term revision plan banayein, weak topics ko priority dein aur timed practice se answer writing behtar karein."
}

def main():
    if not SUPABASE_URL.startswith("https://") or not SERVICE_KEY:
        raise RuntimeError("Missing Supabase credentials.")
    # 80 combinations: four grades x five subjects x four learning formats.
    index = (TODAY.toordinal() - dt.date(2026, 1, 1).toordinal()) % (len(GRADES)*len(SUBJECTS)*len(TOPICS))
    grade = GRADES[index // (len(SUBJECTS)*len(TOPICS))]
    remainder = index % (len(SUBJECTS)*len(TOPICS))
    subject = SUBJECTS[remainder // len(TOPICS)]
    topic, intro, method = TOPICS[remainder % len(TOPICS)]
    title = f"{grade} {subject}: {topic}"
    slug = f"{TODAY.isoformat()}-{grade.lower().replace(' ','-')}-{subject.lower().replace(' ','-')}-{remainder%len(TOPICS)+1}"
    excerpt = f"{grade} ke students ke liye {subject} mein padhai aur revision ko behtar banane ke practical tips."
    content = (
        f"{grade} ke students ke liye {subject} study guide\n\n"
        f"{intro}\n\n"
        f"Subject tip: {SUBJECT_TIPS[subject]}\n\n"
        f"Class-wise guidance: {GRADE_TIPS[grade]}\n\n"
        f"Aaj ka action plan: {method}\n\n"
        "Important: Yeh general study guidance hai, official syllabus ya exam notification nahi. Apne school aur board ke current session ke syllabus, dates aur instructions ko official source se confirm karein."
    )
    url = f"{SUPABASE_URL}/rest/v1/school_articles"
    # Idempotency: if this date's article already exists, do not create a duplicate.
    check = requests.get(url, headers=HEADERS, params={"slug": f"eq.{slug}", "select":"id"}, timeout=25)
    check.raise_for_status()
    if check.json():
        print(f"Article already exists for {TODAY}; nothing to do.")
        return
    payload = {"slug":slug,"title":title,"excerpt":excerpt,"content":content,"grade":grade,"subject":subject,"status":"published","published_at":dt.datetime.now(dt.timezone.utc).isoformat()}
    response = requests.post(url, headers=HEADERS, json=payload, timeout=25)
    response.raise_for_status()
    print(f"Published school article: {title}")

if __name__ == "__main__":
    main()
