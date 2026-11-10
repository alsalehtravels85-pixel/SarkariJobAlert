# SarkariJobAlert AI Worker setup (Hinglish)

Yeh alag Worker hai; existing Pages, push-notification Worker, Supabase schema aur scanner ko replace nahi karta.

## Cloudflare setup
1. Cloudflare Dashboard → Workers & Pages → Create → Worker. Name: sarkarijobalert-ai.
2. Is folder ki index.js paste karke Deploy karein.
3. Settings → Bindings → Add → Workers AI. Binding variable exactly AI.
4. Settings → Variables and Secrets mein SUPABASE_URL aur SUPABASE_ANON_KEY add karein (existing public project URL/publishable key). Service-role key kabhi na daalein.
5. Worker URL note karein, e.g. https://sarkarijobalert-ai.<account-subdomain>.workers.dev.

## Frontend connect
Root config.js mein AI_WORKER_URL ko actual Worker URL se set karein. Commit ke baad Pages deployment check karein. Worker URL + /health open karke ok:true aur aiConfigured:true verify karein.

## Privacy / limits
- Workers AI free allocation limited hai, unlimited free nahi. Current usage/pricing Cloudflare docs mein verify karein.
- Job Passport v1 localStorage mein save hota hai. Profile sirf chat/matching request ke waqt Worker ko bheja jata hai; Supabase mein save nahi hota.
- AI Worker sirf published jobs read karta hai. Drafts, admin accounts, push subscriptions ya job rows modify nahi karta.
- AI responses galat/incomplete ho sakte hain; official notice se dates/fees/eligibility verify karein.
- CORS origin check alone complete abuse protection nahi. Public launch se pehle Cloudflare rate limiting/Turnstile aur usage monitoring configure karein.
- Worker unconfigured ho to AI feature error show karega; normal website chalti rahegi.

Endpoints: GET /health, POST /chat, POST /match.
Model: @cf/meta/llama-3.1-8b-instruct via Workers AI binding.