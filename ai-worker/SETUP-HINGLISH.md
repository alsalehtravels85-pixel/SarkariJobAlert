# SarkariJobAlert AI Worker setup (Hinglish)

Yeh alag Cloudflare Worker hai. Existing Pages frontend, push-notification Worker, Supabase schema aur job scanner ko replace ya modify nahi karta.

## Automated deployment
GitHub Actions workflow `.github/workflows/deploy-ai-worker.yml` Worker ko deploy karta hai. Repository Actions secrets:
- `CLOUDFLARE_API_TOKEN`: dedicated token with Account / Workers Scripts / Edit permission.
- `CLOUDFLARE_ACCOUNT_ID`: Cloudflare account ID.
- `GEMINI_API_KEY`: existing Gemini API key.
- `SUPABASE_URL`: Supabase project URL.
- `SUPABASE_ANON_KEY`: Supabase publishable/anon key (copy the public key from root config.js).

Do NOT configure or use the Supabase service-role key for this Worker. The Worker uses the public anon/publishable key and relies on Supabase RLS to expose published jobs only.

## Frontend
The root config.js points to `https://sarkarijobalert-ai.gulfjob.workers.dev`. Confirm that this is the exact Worker URL after deployment. Test `/health`; it should return `ok:true` and `configured:true`.

## Privacy and safeguards
- Gemini API key is stored as a Cloudflare Worker secret and never sent to the browser.
- Job Passport stays in browser localStorage; it is sent only with a chat/matching request and is not written to Supabase.
- Worker reads only published jobs; it has no insert/update/delete endpoints.
- AI may be inaccurate; verify dates, fees and eligibility against the official notification.
- CORS allows only the production custom domain and www host. If Pages preview domains are needed, add the exact trusted hostname explicitly.
- Before broad public launch, configure Cloudflare rate limiting / Turnstile and monitor Gemini API usage.

Endpoints: GET /health, POST /chat, POST /match.
Model: `gemini-3.8-flash` through Google's Gemini generateContent API.
