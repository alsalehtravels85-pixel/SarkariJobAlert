# SarkariJobAlert AI Worker setup — Free mode

Sarkari Dost uses Cloudflare Workers AI. No Gemini/OpenAI API key, paid AI API, or separate AI provider billing is configured.

## Free usage
- Cloudflare Workers AI Free allocation: 10,000 Neurons per day.
- The daily allowance resets at 00:00 UTC.
- After the free allowance is exhausted, AI requests may fail until reset. It is not unlimited free usage.
- Monitor usage in Cloudflare Dashboard → Workers & Pages → AI → Usage.

## Automated deployment
GitHub Actions deploys the separate AI Worker. Required repository Actions secrets:
- CLOUDFLARE_API_TOKEN — Account Workers Scripts Edit permission.
- CLOUDFLARE_ACCOUNT_ID — Cloudflare account ID.
- SUPABASE_URL — existing Supabase project URL.
- SUPABASE_ANON_KEY — public publishable/anon key.

No GEMINI_API_KEY is needed. Do not use the Supabase service-role key.

## Worker binding
The Worker uses the Cloudflare Workers AI binding named AI, declared in wrangler.toml. Model: @cf/meta/llama-3.2-3b-instruct.

## Existing systems
The existing Pages frontend, push-notification Worker, Supabase schema and job scanner are not replaced. Worker reads published jobs and published study guides only. For academic questions it supplies the matching guide's article content (not just title/summary) to the model, so answers can explain the actual published material and link back to the article.

## Test
GET /health should return ok:true and configured:true after deployment.
POST /chat and POST /match are the AI endpoints.

Job Passport stays in browser localStorage and is sent only when a user asks for matching. Never submit Aadhaar, OTP or passwords.
