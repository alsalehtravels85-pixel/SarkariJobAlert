import fs from 'node:fs/promises';

const SITE = 'https://sarkari-jobalert.com';

// Keep stable pages separate from the automatically maintained job sitemap.
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

const pagesXml = `<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n${body}\n</urlset>\n`;
await fs.writeFile('sitemap-pages.xml', pagesXml, 'utf8');

const indexXml = `<?xml version="1.0" encoding="UTF-8"?>\n<sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n  <sitemap>\n    <loc>${SITE}/sitemap-pages.xml</loc>\n  </sitemap>\n  <sitemap>\n    <loc>${SITE}/sitemap-jobs.xml</loc>\n  </sitemap>\n</sitemapindex>\n`;
await fs.writeFile('sitemap.xml', indexXml, 'utf8');

console.log(`Sitemap index generated with ${staticPaths.length} static pages and sitemap-jobs.xml.`);
