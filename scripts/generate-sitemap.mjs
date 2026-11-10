import fs from 'node:fs/promises';

const SITE = 'https://sarkari-jobalert.com';
const SUPABASE_URL = (process.env.SUPABASE_URL || '').replace(/\/$/, '');
const SERVICE_KEY = process.env.SUPABASE_SERVICE_ROLE_KEY || '';

if (!SUPABASE_URL.startsWith('https://') || !SERVICE_KEY) {
  throw new Error('Missing SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY GitHub secret.');
}

const headers = {
  apikey: SERVICE_KEY,
  Authorization: `Bearer ${SERVICE_KEY}`,
};

async function fetchPublishedJobs() {
  const all = [];
  let offset = 0;
  const pageSize = 1000;

  while (true) {
    const url = new URL(`${SUPABASE_URL}/rest/v1/jobs`);
    url.searchParams.set('select', 'id,created_at');
    url.searchParams.set('status', 'eq.published');
    url.searchParams.set('order', 'created_at.desc');
    url.searchParams.set('limit', String(pageSize));
    url.searchParams.set('offset', String(offset));

    const response = await fetch(url, { headers });
    if (!response.ok) {
      const body = await response.text();
      throw new Error(`Supabase jobs query failed (${response.status}): ${body.slice(0, 500)}`);
    }

    const rows = await response.json();
    all.push(...rows);
    if (rows.length < pageSize) break;
    offset += pageSize;
  }

  return all;
}

function xmlEscape(value) {
  return String(value).replaceAll('&', '&amp;').replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;').replaceAll('"', '&quot;').replaceAll("'", '&apos;');
}

const staticPaths = [
  '/', '/about.html', '/contact.html', '/privacy.html',
  '/disclaimer.html', '/education.html'
];
const staticEntries = staticPaths.map(path => ({ loc: `${SITE}${path}` }));
const jobs = await fetchPublishedJobs();
const jobEntries = jobs
  .filter(job => job.id !== null && job.id !== undefined && String(job.id).length > 0)
  .map(job => ({
    loc: `${SITE}/?job=${encodeURIComponent(String(job.id))}`,
    lastmod: job.created_at ? new Date(job.created_at).toISOString() : null,
  }));

const entries = [...staticEntries, ...jobEntries];
const body = entries.map(entry => {
  const lastmod = entry.lastmod ? `\n    <lastmod>${xmlEscape(entry.lastmod)}</lastmod>` : '';
  return `  <url>\n    <loc>${xmlEscape(entry.loc)}</loc>${lastmod}\n  </url>`;
}).join('\n');

const xml = `<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n${body}\n</urlset>\n`;
await fs.writeFile('sitemap.xml', xml, 'utf8');
console.log(`Sitemap generated: ${staticEntries.length} static URLs + ${jobEntries.length} published job URLs.`);
