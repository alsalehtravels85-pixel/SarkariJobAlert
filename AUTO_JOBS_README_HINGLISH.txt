SARKARIJOBALERT AUTO-JOBS UPDATE (Hinglish)

Is update mein:
- Official source discovery list mein SSC, UPSC, IBPS, Indian Railways, SBI ke saath UPSSSC, UPPSC, National Career Service aur India Post add kiye gaye hain.
- GitHub Actions schedule har 6 ghante ka hai; Actions tab se manual run bhi kar sakte hain.
- Naye notices Supabase jobs table mein DRAFT ke roop mein save hote hain.
- Duplicate URL aur title checks rakhe gaye hain.
- apply_url ko galat tareeke se notice URL se fill nahi kiya jata; human verification ke liye blank rehta hai.
- source_url traceability ke liye record hota hai.

ZAROORI LIMITATIONS:
1. Yeh notice-link discovery hai, full notification PDF parsing nahi. Vacancy, dates, age, qualification, fees, selection process abhi automatic reliably extract nahi hote.
2. Har official site scraping allow ya technically accessible nahi hoti. 403/SSL errors ko bypass nahi kiya gaya; logs mein errors dekhein.
3. Sare records Draft rehte hain. Details official notification se verify karke hi Publish karein.
4. GitHub repository mein Secrets set hon:
   SUPABASE_URL
   SUPABASE_SERVICE_ROLE_KEY
   Service role key sirf GitHub Actions Secrets mein rakhein, config.js ya public frontend mein kabhi nahi.
5. Agar Supabase column/table names different hon, workflow error log check karein.
6. Workflow GitHub Actions ke schedule par chalega; GitHub scheduled workflows kabhi-kabhi delay ho sakte hain.

Deploy:
- ZIP extract karein.
- GitHub repository mein files upload/replace karein (existing app.js, index.html, styles.css ko bhi saath rakhein).
- Commit changes.
- GitHub > Actions > Auto Fetch Government Jobs > Run workflow se pehla test run karein.
- Run log check karein; phir Supabase jobs table mein Draft records verify karein.
