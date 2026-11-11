const ORIGIN = "https://sarkari-jobalert.com";
const MODEL = "@cf/meta/llama-3.2-3b-instruct";
const allowedOrigin = value => { try { const u=new URL(value); return u.protocol==="https:"&&(u.hostname==="sarkari-jobalert.com"||u.hostname==="www.sarkari-jobalert.com")?u.origin:null; } catch { return null; } };
const cors = origin => ({ "Access-Control-Allow-Origin":allowedOrigin(origin)||ORIGIN,"Access-Control-Allow-Methods":"GET,POST,OPTIONS","Access-Control-Allow-Headers":"Content-Type","Vary":"Origin" });
const json = (data,status=200,origin="") => new Response(JSON.stringify(data),{status,headers:{...cors(origin),"Content-Type":"application/json; charset=utf-8","Cache-Control":"no-store"}});
const clean = (v,n=500) => String(v??"").replace(/[<>]/g,"").replace(/\s+/g," ").trim().slice(0,n);

async function loadPublishedJobs(env) {
 const base=String(env.SUPABASE_URL||"").replace(/\/$/,""),key=env.SUPABASE_ANON_KEY;
 if(!base||!key) throw new Error("Supabase Worker configuration incomplete.");
 const fields="id,title,department,category,vacancies,last_date,qualification,age_limit,fees,selection_process,notification_url,apply_url,description";
 const url=base+"/rest/v1/jobs?status=eq.published&select="+encodeURIComponent(fields)+"&order=created_at.desc&limit=60";
 const r=await fetch(url,{headers:{apikey:key,Authorization:"Bearer "+key}});
 if(!r.ok) throw new Error("Published job data abhi load nahi ho pa raha.");
 return (await r.json()).map(j=>({id:j.id,title:clean(j.title,180),department:clean(j.department,100),category:clean(j.category,40),vacancies:clean(j.vacancies,100),last_date:clean(j.last_date,30),qualification:clean(j.qualification,260),age_limit:clean(j.age_limit,160),fees:clean(j.fees,120),selection_process:clean(j.selection_process,180),notification_url:clean(j.notification_url,500),apply_url:clean(j.apply_url,500),description:clean(j.description,500)}));
}
async function loadPublishedGuides(env) {
 const base=String(env.SUPABASE_URL||"").replace(/\/$/,""),key=env.SUPABASE_ANON_KEY;
 if(!base||!key) return [];
 const fields="id,title,slug,excerpt,content,grade,subject,published_at";
 const url=base+"/rest/v1/school_articles?status=eq.published&article_type=eq.study_guide&select="+encodeURIComponent(fields)+"&order=published_at.desc&limit=60";
 const r=await fetch(url,{headers:{apikey:key,Authorization:"Bearer "+key}});
 if(!r.ok) return [];
 return (await r.json()).map(a=>({id:a.id,title:clean(a.title,180),slug:clean(a.slug,180),excerpt:clean(a.excerpt,500),content:clean(a.content,6500),grade:clean(a.grade,60),subject:clean(a.subject,80),url:ORIGIN+"/education.html#article-"+encodeURIComponent(a.id)}));
}
const makeProfile=p=>["Qualification: "+clean(p?.qualification,100),"DOB: "+clean(p?.dob,10),"Category: "+clean(p?.category,40),"State: "+clean(p?.state,80),"Preference: "+clean(p?.preference,100)].join("\n");

async function callFreeCloudflareAI(env,system,history,prompt) {
 if(!env.AI) throw new Error("Cloudflare Workers AI binding configure nahi hai.");
 const messages=[
  {role:"system",content:system},
  ...history.map(x=>({role:x.role==="assistant"?"assistant":"user",content:x.content})),
  {role:"user",content:prompt}
 ];
 try {
  const result=await env.AI.run(MODEL,{messages,max_tokens:900,temperature:0.35});
  const answer=String(result?.response||"").trim();
  if(!answer) throw new Error("AI ne khaali jawab diya. Sawal ko chhota karke dobara poochhein.");
  return answer;
 } catch(error) {
  const message=String(error?.message||"");
  if(/limit|quota|neurons|429|exceed/i.test(message)) throw new Error("Aaj ki free AI limit poori ho gayi hai. Cloudflare ki daily limit reset hone par dobara try karein.");
  throw new Error(clean(message||"Free AI service abhi busy hai. Thodi der baad try karein.",240));
 }
}
export default { async fetch(request,env) {
 const origin=request.headers.get("Origin")||"";
 if(request.method==="OPTIONS")return allowedOrigin(origin)?new Response(null,{status:204,headers:cors(origin)}):new Response(null,{status:403});
 if(!allowedOrigin(origin))return json({error:"Origin not allowed."},403,origin);
 const url=new URL(request.url);
 if(request.method==="GET"&&url.pathname==="/health")return json({ok:true,service:"Sarkari Dost",provider:"Cloudflare Workers AI",model:MODEL,configured:!!env.AI&&!!env.SUPABASE_URL&&!!env.SUPABASE_ANON_KEY},200,origin);
 if(request.method!=="POST"||!["/chat","/match"].includes(url.pathname))return json({error:"Not found."},404,origin);
 let body;try{body=await request.json();}catch{return json({error:"Request format sahi nahi hai."},400,origin);}
 if(JSON.stringify(body).length>14000)return json({error:"Message bahut lamba hai. Chhota karke bhejein."},413,origin);
 const message=clean(body.message,1200);if(url.pathname==="/chat"&&!message)return json({error:"Apna sawal type karein."},400,origin);
 try {
  const [jobs,guides]=await Promise.all([loadPublishedJobs(env),loadPublishedGuides(env)]);
  const profile=makeProfile(body.profile);
  const jobContext=jobs.map((j,i)=>[i+1,j.title,"Department: "+j.department,"Category: "+j.category,"Vacancies: "+j.vacancies,"Last date: "+j.last_date,"Qualification: "+j.qualification,"Age: "+j.age_limit,"Fees: "+j.fees,"Selection: "+j.selection_process,"Notification URL: "+j.notification_url,"Apply URL: "+j.apply_url,"Description: "+j.description].join(" | ")).join("\n");
  const queryText=[message,...(Array.isArray(body.history)?body.history.slice(-4).map(x=>clean(x.content,300)):[])].join(" ").toLowerCase();
  const terms=queryText.split(/[^\p{L}\p{N}]+/u).filter(x=>x.length>2);
  const relevantGuides=guides.map(g=>({g,score:terms.reduce((n,t)=>n+((g.title+" "+g.excerpt+" "+g.grade+" "+g.subject+" "+g.content).toLowerCase().includes(t)?1:0),0)})).sort((a,b)=>b.score-a.score).slice(0,5);
  const guideContext=relevantGuides.map(({g},i)=>[i+1,g.title,"Class/course: "+g.grade,"Subject: "+g.subject,"Summary: "+g.excerpt,"Full guide content: "+g.content.slice(0,4200),"Article URL: "+g.url].join(" | ")).join("\n");
  const system=[
   "You are Sarkari Dost, a capable, warm, patient Hindi/Hinglish AI study and career assistant for Indian students.",
   "Be conversational and context-aware. Answer the student's actual question first, clearly and completely. Ask only one useful follow-up when essential. Never end mid-sentence.",
   "For job questions, use only the published jobs dataset for current vacancy facts. Resolve follow-ups like isme, us vacancy, apply karna hai using conversation history. Give exact title, department, vacancy count, last date, qualification, age, fee and selection process when available. Explain application steps. Never claim eligibility unless verified. Put exact Apply Online and Official Notification URLs on separate lines. Never invent or alter links.",
   "For academic questions, use the supplied full guide content as a source when relevant. Explain the requested topic/solution first in student-friendly Hindi/Hinglish, with steps and examples where useful. If a published School & Exam Guide article genuinely matches, recommend it naturally and provide its exact Article URL on a separate line. If no guide matches, answer from general educational knowledge and do not invent article URLs. Never claim an article says something absent from its supplied content.",
   "Never request Aadhaar, OTP, passwords or bank details. Never guarantee job selection or exam results. Clearly distinguish general guidance from verified official facts.",
   "Optional Job Passport:\n"+profile,
   "Published jobs:\n"+(jobContext||"No published jobs are currently available."),
   "Published School & Exam Guide articles:\n"+(guideContext||"No published School & Exam Guide articles were returned.")
  ].join("\n\n");
  const history=Array.isArray(body.history)?body.history.slice(-10).map(x=>({role:x.role==="assistant"?"assistant":"user",content:clean(x.content,900)})):[];
  const prompt=url.pathname==="/match"?"Mere Job Passport ke hisaab se matching published jobs ka shortlist banao. Match ka reason, missing eligibility checks aur official links do.":message;
  const answer=await callFreeCloudflareAI(env,system,history,prompt);
  return json({answer,jobsChecked:jobs.length,guidesChecked:guides.length,disclaimer:"Vacancy ki final eligibility, dates aur fees official notification se verify karein."},200,origin);
 } catch(e){return json({error:clean(e.message||"AI service abhi available nahi hai.",320)},502,origin);}
}};
