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
  const list=await jobs(env),p=profile(body.profile);
  const context=list.map((j,i)=>[i+1,j.title,"Dept:"+j.department,"Category:"+j.category,"Vacancies:"+j.vacancies,"Last date:"+j.last_date,"Qualification:"+j.qualification,"Age:"+j.age_limit,"Fees:"+j.fees,"Selection:"+j.selection_process,"Official PDF:"+j.notification_url,"Apply:"+j.apply_url].join(" | ")).join("\n");
  const system="You are Sarkari Dost, a careful Hindi/Hinglish assistant for Indian government job seekers. Reply in simple Hindi/Hinglish, concise and practical. For current vacancies, use only the published data below. Never invent jobs, dates, fees, eligibility, URLs or results. If data is missing, say so and direct user to official notification. Never guarantee eligibility/selection; age, DOB cut-off, category relaxation and qualifications must be checked against official notification. Only give official URLs present in data. Never request Aadhaar, OTP, passwords or bank details. Profile is sent only for this request:\n"+p+"\nPublished jobs:\n"+(context||"No published jobs found.");
  const prompt=u.pathname==="/match"?"Create a cautious shortlist based on the profile. Explain match reasons and what must be verified in the official notice. If no clear matches, say so.":message;
  const history=Array.isArray(body.history)?body.history.slice(-8).map(x=>({role:x.role==="assistant"?"assistant":"user",content:clean(x.content,700)})):[];
  const answer=clean(await askGemini(env,system,history,prompt),5000);
  if(!answer)throw Error("AI returned an empty response.");
  return reply({answer,jobsChecked:list.length,disclaimer:"Dates aur eligibility official notification se verify karein."},200,origin);
 }catch(e){return reply({error:clean(e.message||"AI temporarily unavailable.",220)},502,origin)}
}};
