/* SarkariJobAlert Push Sender - separate Cloudflare Worker.
 * Allowlisted admin: alsalehtravels85@gmail.com
 * Required secrets: SUPABASE_URL, SUPABASE_ANON_KEY, SUPABASE_SERVICE_ROLE_KEY,
 * FIREBASE_SERVICE_ACCOUNT_JSON. Never expose secrets in frontend or chat.
 */
const ADMIN_EMAIL = "alsalehtravels85@gmail.com";
const ORIGIN = "https://sarkari-jobalert.com";
const enc = new TextEncoder();
const cors = {"access-control-allow-origin": ORIGIN, "access-control-allow-headers": "authorization,content-type", "access-control-allow-methods": "POST,OPTIONS", "vary": "Origin"};
const reply = (data, status=200) => new Response(JSON.stringify(data), {status, headers:{...cors,"content-type":"application/json; charset=utf-8"}});
const b64url = value => {
  let raw;
  if (typeof value === "string") raw = btoa(unescape(encodeURIComponent(value)));
  else { let bin=""; new Uint8Array(value).forEach(b=>bin+=String.fromCharCode(b)); raw=btoa(bin); }
  return raw.replace(/\+/g,"-").replace(/\//g,"_").replace(/=+$/g,"");
};
async function getGoogleToken(sa) {
  const now=Math.floor(Date.now()/1000);
  const head=b64url(JSON.stringify({alg:"RS256",typ:"JWT"}));
  const claim=b64url(JSON.stringify({iss:sa.client_email,scope:"https://www.googleapis.com/auth/firebase.messaging",aud:"https://oauth2.googleapis.com/token",iat:now,exp:now+3600}));
  const pem=sa.private_key.replace(/-----BEGIN PRIVATE KEY-----|-----END PRIVATE KEY-----|\s/g,"");
  const der=Uint8Array.from(atob(pem),c=>c.charCodeAt(0));
  const key=await crypto.subtle.importKey("pkcs8",der,{name:"RSASSA-PKCS1-v1_5",hash:"SHA-256"},false,["sign"]);
  const unsigned=head+"."+claim;
  const sig=await crypto.subtle.sign("RSASSA-PKCS1-v1_5",key,enc.encode(unsigned));
  const assertion=unsigned+"."+b64url(sig);
  const r=await fetch("https://oauth2.googleapis.com/token",{method:"POST",headers:{"content-type":"application/x-www-form-urlencoded"},body:new URLSearchParams({grant_type:"urn:ietf:params:oauth:grant-type:jwt-bearer",assertion})});
  const d=await r.json(); if(!r.ok) throw new Error("Google OAuth token failed"); return d.access_token;
}
export default { async fetch(request, env) {
  if (request.method === "OPTIONS") return new Response(null,{status:204,headers:cors});
  if (request.method !== "POST" || new URL(request.url).pathname !== "/notify") return reply({error:"Not found"},404);
  try {
    for (const k of ["SUPABASE_URL","SUPABASE_ANON_KEY","SUPABASE_SERVICE_ROLE_KEY","FIREBASE_SERVICE_ACCOUNT_JSON"]) if(!env[k]) return reply({error:"Worker secret missing: "+k},500);
    const auth=request.headers.get("authorization")||"";
    if(!auth.startsWith("Bearer ")) return reply({error:"Admin login required"},401);
    const ur=await fetch(env.SUPABASE_URL+"/auth/v1/user",{headers:{apikey:env.SUPABASE_ANON_KEY,authorization:auth}});
    if(!ur.ok) return reply({error:"Invalid login session"},401);
    const user=await ur.json();
    if(String(user.email||"").toLowerCase()!==ADMIN_EMAIL) return reply({error:"Not authorized"},403);
    const body=await request.json(); const id=String(body.jobId||"");
    if(!/^\d+$/.test(id)) return reply({error:"Invalid job ID"},400);
    const dbHeaders={apikey:env.SUPABASE_SERVICE_ROLE_KEY,authorization:"Bearer "+env.SUPABASE_SERVICE_ROLE_KEY};
    // Select only columns confirmed in the project's schema.sql.
    const jr=await fetch(env.SUPABASE_URL+"/rest/v1/jobs?id=eq."+encodeURIComponent(id)+"&status=eq.published&select=id,title,category,last_date,notification_date,apply_url,notification_url,description",{headers:dbHeaders});
    const jobs=await jr.json(); if(!jr.ok) return reply({error:"Could not read job"},500);
    if(!jobs.length) return reply({error:"Published job not found"},404);
    const job=jobs[0];
    // Check existing log first; write it only after successful sending so failures can be retried.
    const check=await fetch(env.SUPABASE_URL+"/rest/v1/push_notification_log?job_id=eq."+id+"&select=job_id",{headers:dbHeaders});
    if(!check.ok) return reply({error:"Notification log table missing or inaccessible; apply PUSH_NOTIFICATION_MIGRATION.sql"},500);
    if((await check.json()).length) return reply({ok:true,duplicate:true,sent:0});
    const sr=await fetch(env.SUPABASE_URL+"/rest/v1/push_subscriptions?enabled=eq.true&select=id,token",{headers:dbHeaders});
    const subs=await sr.json(); if(!sr.ok) return reply({error:"Could not read subscribed devices"},500);
    if(!subs.length) return reply({ok:true,sent:0,message:"No subscribed devices yet"});
    const sa=JSON.parse(env.FIREBASE_SERVICE_ACCOUNT_JSON);
    if(!sa.project_id || !sa.client_email || !sa.private_key) return reply({error:"Firebase service-account JSON is invalid"},500);
    const access=await getGoogleToken(sa);
    const category=String(job.category||"Vacancy");
    const date=category==="Vacancy" ? (job.last_date||"Check notification") : (job.notification_date||"Check details");
    const target=ORIGIN+"/?job="+encodeURIComponent(job.id);
    let sent=0, invalid=[];
    for(const sub of subs) {
      const payload={message:{token:sub.token,data:{title:job.title,body:category+" | "+date+" | Details ke liye tap karein",url:target,jobId:String(job.id),tag:"sja-"+job.id}}};
      const r=await fetch("https://fcm.googleapis.com/v1/projects/"+sa.project_id+"/messages:send",{method:"POST",headers:{authorization:"Bearer "+access,"content-type":"application/json"},body:JSON.stringify(payload)});
      if(r.ok) sent++; else {const e=await r.text(); if(e.includes("UNREGISTERED")||e.includes("registration-token-not-registered")) invalid.push(sub.id);}
    }
    if(invalid.length) await fetch(env.SUPABASE_URL+"/rest/v1/push_subscriptions?id=in.("+invalid.join(",")+")",{method:"PATCH",headers:{...dbHeaders,"content-type":"application/json"},body:JSON.stringify({enabled:false,updated_at:new Date().toISOString()})});
    if(sent>0) {
      const lr=await fetch(env.SUPABASE_URL+"/rest/v1/push_notification_log",{method:"POST",headers:{...dbHeaders,"content-type":"application/json",Prefer:"return=minimal"},body:JSON.stringify({job_id:job.id,title:job.title})});
      if(!lr.ok) return reply({ok:true,sent,warning:"Sent, but deduplication log could not be saved"},200);
    }
    return reply({ok:true,sent,failed:subs.length-sent,invalid:invalid.length});
  } catch(e) { return reply({error:e.message||"Internal error"},500); }
}};
