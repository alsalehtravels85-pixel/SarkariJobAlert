const ORIGIN="https://sarkari-jobalert.com";
const MODEL="gemini-3.8-flash";
const allowed=o=>{try{const u=new URL(o);return u.protocol==="https:"&&(u.hostname==="sarkari-jobalert.com"||u.hostname==="www.sarkari-jobalert.com")?u.origin:null}catch{return null}};
const headers=o=>({"Access-Control-Allow-Origin":allowed(o)||ORIGIN,"Access-Control-Allow-Methods":"GET,POST,OPTIONS","Access-Control-Allow-Headers":"Content-Type","Vary":"Origin"});
const reply=(d,s=200,o="")=>new Response(JSON.stringify(d),{status:s,headers:{...headers(o),"Content-Type":"application/json; charset=utf-8","Cache-Control":"no-store"}});
const clean=(v,n=500)=>String(v??"").replace(/[<>]/g,"").replace(/\s+/g," ").trim().slice(0,n);
async function jobs(env){
 const base=String(env.SUPABASE_URL||"").replace(/\/$/,""),key=env.SUPABASE_ANON_KEY;
 if(!base||!key)throw Error("Supabase Worker configuration incomplete.");
 const cols="id,title,department,category,vacancies,last_date,qualification,age_limit,fees,selection_process,notification_url,apply_url,description";
 const r=await fetch(base+"/rest/v1/jobs?status=eq.published&select="+encodeURIComponent(cols)+"&order=created_at.desc&limit=40",{headers:{apikey:key,Authorization:"Bearer "+key}});
 if(!r.ok)throw Error("Published jobs could not be loaded.");
 return(await r.json()).map(j=>({id:j.id,title:clean(j.title,180),department:clean(j.department,100),category:clean(j.category,40),vacancies:clean(j.vacancies,100),last_date:j.last_date||"",qualification:clean(j.qualification,260),age_limit:clean(j.age_limit,160),fees:clean(j.fees,120),selection_process:clean(j.selection_process,180),notification_url:j.notification_url||"",apply_url:j.apply_url||"",description:clean(j.description,350)}));
}
async function guides(env){
 const base=String(env.SUPABASE_URL||"").replace(/\/$/,""),key=env.SUPABASE_ANON_KEY;
 if(!base||!key)return [];
 const cols="id,title,slug,excerpt,grade,subject,published_at";
 const url=base+"/rest/v1/school_articles?status=eq.published&article_type=eq.study_guide&select="+encodeURIComponent(cols)+"&order=published_at.desc&limit=35";
 const r=await fetch(url,{headers:{apikey:key,Authorization:"Bearer "+key}});
 if(!r.ok)return [];
 return(await r.json()).map(a=>({id:a.id,title:clean(a.title,180),slug:clean(a.slug,160),excerpt:clean(a.excerpt,260),grade:clean(a.grade,60),subject:clean(a.subject,80),url:ORIGIN+"/education.html#article-"+encodeURIComponent(a.id)}));
}
const profile=p=>["Qualification: "+clean(p?.qualification,100),"DOB: "+clean(p?.dob,10),"Category: "+clean(p?.category,40),"State: "+clean(p?.state,80),"Preference: "+clean(p?.preference,100)].join("\n");
async function askGemini(env,system,history,prompt){
 if(!env.GEMINI_API_KEY)throw Error("Gemini API key is not configured.");
 const contents=[...history.map(x=>({role:x.role==="assistant"?"model":"user",parts:[{text:x.content}]})),{role:"user",parts:[{text:prompt}]}];
 const r=await fetch("https://generativelanguage.googleapis.com/v1beta/models/"+MODEL+":generateContent",{method:"POST",headers:{"Content-Type":"application/json","x-goog-api-key":env.GEMINI_API_KEY},body:JSON.stringify({systemInstruction:{parts:[{text:system}]},contents,generationConfig:{temperature:0.2,maxOutputTokens:650}})});
 const data=await r.json().catch(()=>({}));
 if(!r.ok)throw Error(clean(data?.error?.message||"Gemini service temporarily unavailable.",220));
 return (data?.candidates?.[0]?.content?.parts||[]).map(p=>p.text||"").join("\n").trim();
}
export default{async fetch(req,env){
 const origin=req.headers.get("Origin")||"";
 if(req.method==="OPTIONS")return allowed(origin)?new Response(null,{status:204,headers:headers(origin)}):new Response(null,{status:403});
 if(!allowed(origin))return reply({error:"Origin not allowed."},403,origin);
 const u=new URL(req.url);
 if(req.method==="GET"&&u.pathname==="/health")return reply({ok:true,service:"SarkariJobAlert AI",provider:"Gemini",model:MODEL,configured:!!env.GEMINI_API_KEY&&!!env.SUPABASE_URL&&!!env.SUPABASE_ANON_KEY},200,origin);
 if(req.method!=="POST"||!["/chat","/match"].includes(u.pathname))return reply({error:"Not found."},404,origin);
 let body;try{body=await req.json()}catch{return reply({error:"Invalid request."},400,origin)}
 if(JSON.stringify(body).length>12000)return reply({error:"Request too large."},413,origin);
 const message=clean(body.message,1200);
 if(u.pathname==="/chat"&&!message)return reply({error:"Apna sawal type karein."},400,origin);
 try{
  const list=await jobs(env),guideList=await guides(env),p=profile(body.profile);
  const context=list.map((j,i)=>[i+1,j.title,"Dept:"+j.department,"Category:"+j.category,"Vacancies:"+j.vacancies,"Last date:"+j.last_date,"Qualification:"+j.qualification,"Age:"+j.age_limit,"Fees:"+j.fees,"Selection:"+j.selection_process,"Official PDF:"+j.notification_url,"Apply:"+j.apply_url].join(" | ")).join("\n");
  const guideContext=guideList.map((g,i)=>[i+1,g.title,"Class/Course:"+g.grade,"Subject:"+g.subject,"Summary:"+g.excerpt,"Read URL:"+g.url].join(" | ")).join("\\n");\n  const system="You are Sarkari Dost, a helpful study mentor and government-job counsellor for Indian students. For academic/student questions (school subjects, board exams, college study, revision, study plans, scholarships/admissions or learning skills), FIRST answer the actual question clearly and usefully. THEN, when a published School & Exam Guide article is relevant, naturally recommend the best matching article: explain in one sentence why it will benefit the student, invite them to read it once, and provide its exact Read Article URL on its own line. Do not force an unrelated article; if none matches, mention the School & Exam Guide page only when genuinely useful. Never invent an article or URL. Keep the answer helpful, not like an advertisement. For career/job questions, prioritize relevant published vacancies and official application links.  Always answer in clear, natural Hinglish/Hindi with complete sentences. Never output broken fragments, unfinished sentences, raw ### headings, or vague filler. Understand the full conversation history: if the user says apply for it/isme apply karna hai, identify the exact vacancy mentioned earlier and explain its application process. Use ONLY the Published jobs dataset below for live vacancy claims. For every relevant vacancy, clearly say 'Ye vacancy aapke liye relevant ho sakti hai' only when the user profile/asked qualification reasonably matches; otherwise say eligibility needs checking. Give exact post title, department, vacancies, last date, qualification, age/age relaxation if supplied, fees if supplied, and selection process if supplied. Then give the exact Apply Online URL and Official Notification URL from the dataset on separate lines, labelled 'Apply Online:' and 'Official Notification:'. Never invent or modify URLs. If a URL is absent, clearly say 'Apply link database mein available nahi hai' rather than guessing. If user asks to apply, give numbered step-by-step instructions and remind them to verify details in official notice before payment/submission. If several jobs match, list up to 5 best matches, each with its own links; do not dump unrelated vacancies. If no job matches or the named job is not in the dataset, say so plainly and ask one focused question or guide them to the relevant job page. Distinguish verified dataset facts from advice. Never guarantee selection or eligibility; DOB cut-off, category relaxation and qualification equivalence must be checked in official notice. Never request Aadhaar, OTP, passwords or bank details. Keep answer structured and easy to read. User profile for this request:\n"+p+"\nPublished jobs dataset (URLs must be copied exactly):\n"+(context||"No published jobs found.");
  const prompt=u.pathname==="/match"?"Create a cautious shortlist based on the profile. Explain match reasons and what must be verified in the official notice. If no clear matches, say so.":message;
  const history=Array.isArray(body.history)?body.history.slice(-8).map(x=>({role:x.role==="assistant"?"assistant":"user",content:clean(x.content,700)})):[];
  const answer=clean(await askGemini(env,system,history,prompt),5000);
  if(!answer)throw Error("AI returned an empty response.");
  return reply({answer,jobsChecked:list.length,disclaimer:"Dates aur eligibility official notification se verify karein."},200,origin);
 }catch(e){return reply({error:clean(e.message||"AI temporarily unavailable.",220)},502,origin)}
}};
