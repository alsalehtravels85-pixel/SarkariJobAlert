import fs from 'node:fs/promises';

const SITE = 'https://sarkari-jobalert.com';

// Keep the root sitemap limited to stable, independently crawlable pages.
// Job updates are listed separately in sitemap-jobs.xml.
const staticPaths = [
  '/',
  '/about.html',
  '/contact.html',
  '/privacy.html',
  '/disclaimer.html',
  '/education.html',
];

function xmlEscape(value) {
  return String(value).replaceAll('&', '&amp;').replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;').replaceAll('"', '&quot;').replaceAll("'", '&apos;');
}

const body = staticPaths.map(path =>
  `  <url>\n    <loc>${xmlEscape(SITE + path)}</loc>\n  </url>`
).join('\n');

const xml = `<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n${body}\n</urlset>\n`;
await fs.writeFile('sitemap.xml', xml, 'utf8');
console.log(`Static sitemap generated: ${staticPaths.length} stable page URLs. Job URLs remain in sitemap-jobs.xml.`);
