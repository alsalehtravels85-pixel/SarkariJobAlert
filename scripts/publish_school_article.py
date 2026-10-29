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

def build_long_content(grade, subject, topic, intro, method):
    """Create a useful, structured long-form study article (not just a short blurb)."""
    subject_focus = {
        "Mathematics": "Formula ko samajhkar apply karein, har solution ke steps likhein, units/signs check karein aur galat sawalon ko dobara solve karein.",
        "Science": "Concept, definition, diagram, formula aur real-life example ko ek saath padhein. Diagram mein labels saaf rakhein aur numerical questions ke steps dikhayein.",
        "Hindi": " पाठ ka central idea, writer/poet ka sandesh, important शब्दार्थ, व्याकरण और लेखन अभ्यास ko alag-alag revise karein.",
        "English": "Reading comprehension, grammar, vocabulary, textbook chapters aur writing formats ki regular practice karein. Answer submit karne se pehle tense, spelling aur sentence structure check karein.",
        "Social Science": "History, Geography, Civics aur Economics ko alag notes mein rakhein. Dates, definitions, maps, examples aur cause-effect relationships ko revise karein."
    }.get(subject, "Textbook ke concepts ko samjhein, notes banayein aur practice questions solve karein.")
    grade_focus = {
        "Class 9": "Is class mein strong foundation sabse important hai. Har chapter padhne ke baad apne words mein summary banayein aur doubts ko agle din tak clear karne ki koshish karein.",
        "Class 10": "Board preparation ke liye current syllabus aur school ke instructions se apni checklist milayein. Sample paper practice karein, lekin kisi unofficial guess paper ko guaranteed question na samjhein.",
        "Class 11": "Class 11 ke concepts aage ki padhai ka base bante hain. Weekly revision rakhein aur kisi ek difficult chapter ko bahut din tak pending na chhodein.",
        "Class 12": "Long-term revision ke saath timed answer writing karein. Weak chapters ko priority dein, lekin easy/scoring topics ka revision bhi regular rakhein."
    }.get(grade, "Apne current syllabus aur teacher ke guidance ke hisaab se preparation plan banayein.")
    sections = [
        f"{grade} {subject} – Complete Study Guide\n\nIs guide ka topic: {topic}. {intro}",
        "1. Sabse pehle goal clear karein\nPadhai shuru karne se pehle chapter ya topic ko chhote targets mein baant dein. Aaj kya samajhna hai, kaun se questions solve karne hain aur end mein kya revise karna hai—ye teen baatein likh lein. Ek session mein bahut saare topics rakhne ke bajaye 1–2 clear targets rakhna zyada practical hota hai.",
        f"2. Subject-wise approach\n{subject_focus} Pehle textbook explanation aur examples padhein. Uske baad notebook band karke apni zubaan mein concept samjhaane ki koshish karein. Agar concept explain nahi ho raha, to us paragraph ya example ko dobara dekhein aur doubt ko mark karein.",
        f"3. Class ke hisaab se planning\n{grade_focus} Apne school/board ke latest syllabus se topics tick karein. Syllabus, exam dates aur marking scheme mein badlav ho sakta hai, isliye unhe official board/school source se verify karna zaroori hai.",
        f"4. Daily study routine\n{method} Ek practical routine ka example: 25–35 minute focused study, 5 minute break, phir 20–30 minute practice. Time apne school, ghar aur coaching schedule ke hisaab se adjust karein. Har din ka target poora na ho to plan ko chhota karein, poori padhai chhodna solution nahi hai.",
        "5. Notes kaise banayein\nNotes ko textbook ki copy na banayein. Important definitions, formulas, dates, diagrams, examples aur common mistakes ko short headings ke neeche likhein. Har chapter ke end par ek page ka revision sheet banayein. Notes mein page number ya chapter name likhne se exam se pehle topic jaldi milta hai.",
        "6. Practice aur answer-writing\nPehle solved example samjhein, phir bina dekhe similar question karein. Long-answer subjects mein answer ko introduction, main points aur conclusion ke order mein likhne ki practice karein. Jahan zaroori ho headings, labelled diagrams, formulas aur calculation steps dikhayein. Sirf answer yaad karne ke bajaye question ka demand samajhna seekhein.",
        "7. Galtiyon se seekhne ka tareeqa\nEk error notebook banayein. Har galat jawab ke saamne likhein: galti concept ki thi, formula yaad nahi tha, question galat padha, ya time management issue tha. 2–3 din baad wahi question dobara solve karein. Jo sawal baar-baar galat ho, use weekly revision list mein rakhein.",
        "8. Weekly revision plan\nHafte ke aakhir mein 20–30 minute nikaal kar dekhein ki kaun se topics complete hue, kaun se pending hain aur kin sawalon mein galti hui. Ek chhota self-test lein. Test ke baad marks se zyada important hai galtiyon ka analysis. Agle hafte ka timetable isi review ke basis par banayein.",
        "9. Exam se ek din pehle\nNaya bada chapter shuru karne ke bajaye apni revision sheet, formulas, definitions, maps/diagrams aur error notebook dekhein. Neend poori karein, zaroori stationery pehle rakh lein aur exam instructions padh lein. Paper mein pehle instructions samjhein, time divide karein aur aakhir mein answers check karne ke liye kuch waqt bachayein.",
        "10. Quick checklist\n• Aaj ka target likha?\n• Textbook se concept samjha?\n• Bina dekhe recall kiya?\n• Practice questions solve kiye?\n• Galtiyon ko note kiya?\n• Kal ke revision ka target banaya?\n\nAgar inmein se sab ka jawab har din ‘haan’ nahi bhi hai, to apne routine ko realistic banayein aur consistency par focus karein.",
        "Important note\nYeh general educational guidance hai. Official syllabus, exam pattern, dates, eligibility aur board instructions ke liye apne school ya sambandhit board ki official website/notice ko hi final maanein. Kisi bhi unofficial article ko official notification na samjhein."
    ]
    return "\n\n".join(sections)


def main():
    if not SUPABASE_URL.startswith("https://") or not SERVICE_KEY:
        raise RuntimeError("Missing Supabase credentials.")
    url = f"{SUPABASE_URL}/rest/v1/school_articles"

    # Expand existing short study-guide articles too, so older entries are not left tiny.
    existing = requests.get(url, headers=HEADERS, params={
        "select":"id,title,grade,subject,content,article_type,status,slug",
        "status":"eq.published", "article_type":"eq.study_guide", "limit":"200"
    }, timeout=30)
    existing.raise_for_status()
    expanded = 0
    for article in existing.json():
        content = article.get("content") or ""
        if len(content.strip()) >= 1800:
            continue
        grade = article.get("grade") or "Class 9"
        subject = article.get("subject") or "Education"
        title = article.get("title") or f"{grade} {subject} Study Guide"
        topic = title.split(":", 1)[-1].strip() if ":" in title else title
        intro = f"{grade} ke students ke liye {subject} ki taiyari ko systematic aur manageable banane ke liye is guide mein practical steps diye gaye hain."
        method = f"{topic} par 20–30 minute focus karein, phir apne notes se self-test lein aur jo points yaad na aayein unhe mark karein."
        patch = requests.patch(f"{url}?id=eq.{article['id']}", headers={**HEADERS, "Prefer":"return=minimal"}, json={"content":build_long_content(grade, subject, topic, intro, method)}, timeout=25)
        patch.raise_for_status()
        expanded += 1
    print(f"Expanded {expanded} existing short study-guide article(s).")

    # Publish one new, long-form guide per day (80-topic rotation).
    index = (TODAY.toordinal() - dt.date(2026, 1, 1).toordinal()) % (len(GRADES)*len(SUBJECTS)*len(TOPICS))
    grade = GRADES[index // (len(SUBJECTS)*len(TOPICS))]
    remainder = index % (len(SUBJECTS)*len(TOPICS))
    subject = SUBJECTS[remainder // len(TOPICS)]
    topic, intro, method = TOPICS[remainder % len(TOPICS)]
    title = f"{grade} {subject}: {topic}"
    slug = f"{TODAY.isoformat()}-{grade.lower().replace(' ','-')}-{subject.lower().replace(' ','-')}-{remainder%len(TOPICS)+1}"
    excerpt = f"{grade} ke students ke liye {subject} mein {topic.lower()} par detailed study guide, daily routine, practice aur revision checklist."
    check = requests.get(url, headers=HEADERS, params={"slug":f"eq.{slug}","select":"id"}, timeout=25)
    check.raise_for_status()
    if check.json():
        print(f"Article already exists for {TODAY}; no duplicate created.")
        return
    payload = {"slug":slug,"title":title,"excerpt":excerpt,"content":build_long_content(grade,subject,topic,intro,method),"grade":grade,"subject":subject,"article_type":"study_guide","status":"published","published_at":dt.datetime.now(dt.timezone.utc).isoformat()}
    response = requests.post(url, headers=HEADERS, json=payload, timeout=25)
    response.raise_for_status()
    print(f"Published long-form study article: {title}")

if __name__ == "__main__":
    main()
