// Usage: node scrape.js home            -> JSON list of listing cards on the source home page
//        node scrape.js detail <slug>   -> JSON {lines, images} for one listing page
const { chromium } = require('playwright');

const SOURCE = 'https://www.thequickcloseteam.com/';
const SITE_CHROME = ['bd92bf78', 'a8868a4b', '978933aa', '78bf59f8', '41b53abf', 'c39d80db', 'f4e3e7f5', '72bfc1ef'];

async function scrollThrough(page) {
  for (let y = 0; y < 12000; y += 600) {
    await page.mouse.wheel(0, 600);
    await page.waitForTimeout(200);
  }
  await page.waitForTimeout(1500);
}

async function home(page) {
  await page.goto(SOURCE, { waitUntil: 'networkidle', timeout: 90000 }).catch(() => {});
  await scrollThrough(page);
  return page.$$eval('a', (anchors) => {
    const out = [];
    for (const a of anchors) {
      if (!/VIEW NOW/i.test(a.textContent || '')) continue;
      let box = a.parentElement;
      for (let i = 0; i < 8 && box; i++) {
        if (/\$[\d,]+/.test(box.innerText || '') && /sqft/i.test(box.innerText || '')) break;
        box = box.parentElement;
      }
      if (!box) continue;
      const lines = box.innerText.split('\n').map((l) => l.trim()).filter(Boolean);
      const statusIdx = lines.findIndex((l) => /^(Active|Assigned|Closed|Pending|Under Contract|Sold)$/i.test(l));
      if (statusIdx < 1) continue;
      const href = a.getAttribute('href') || '';
      out.push({
        slug: href.replace(/^https?:\/\/[^/]+\/?/, '').replace(/[#?].*$/, ''),
        address: lines[statusIdx - 1],
        status: lines[statusIdx],
        price: Number((lines[statusIdx + 1] || '').replace(/[^\d]/g, '')) || null,
        beds: lines[statusIdx + 2] || '',
        baths: lines[statusIdx + 3] || '',
        sqft: lines[statusIdx + 4] || '',
      });
    }
    return out;
  });
}

async function detail(page, slug) {
  const seen = new Set();
  page.on('response', (r) => {
    const m = r.url().match(/wixstatic\.com\/media\/([^/]+~mv2\.(?:jpe?g|png|webp))/i);
    if (m) seen.add(m[1]);
  });
  await page.goto(SOURCE + slug, { waitUntil: 'networkidle', timeout: 90000 }).catch(() => {});
  await scrollThrough(page);
  const srcs = await page.$$eval('img', (imgs) => imgs.map((i) => i.currentSrc || i.src));
  for (const s of srcs) {
    const m = s.match(/media\/([^/]+~mv2\.(?:jpe?g|png|webp))/i);
    if (m) seen.add(m[1]);
  }
  const text = await page.evaluate(() => document.body.innerText);
  const lines = text.split('\n').map((l) => l.replace(/[​ ]/g, ' ').trim()).filter(Boolean);
  const images = [...seen].filter((x) => !SITE_CHROME.some((c) => x.includes(c)));
  return { slug, lines, images };
}

(async () => {
  const [mode, slug] = process.argv.slice(2);
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 1400, height: 1000 } });
  const result = mode === 'home' ? await home(page) : await detail(page, slug);
  process.stdout.write(JSON.stringify(result));
  await browser.close();
})();
