// Real browser-driven audit for SHAKTHI Chrome Developer Bot's
// ui_review_engine.py. Invoked as: node browser_audit.js <url>
// Prints one JSON object to stdout -- Python parses it, doesn't scrape
// text output. Uses the Playwright already installed under
// dashboard/node_modules (proven working for this project's dashboard
// screenshots this session) -- no new dependency.
const { chromium } = require(require.resolve('playwright', { paths: [__dirname + '/../node_modules'] }));

const CTA_PATTERN = /\b(buy now|sign up|get started|contact us|book now|order now|subscribe|pay now|add to cart|start free trial|schedule a call)\b/i;

async function audit(url) {
  const browser = await chromium.launch();
  const consoleErrors = [];
  const result = { url, ok: false };

  try {
    // Desktop pass -- timing, console errors, CTA detection.
    const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
    page.on('console', (msg) => { if (msg.type() === 'error') consoleErrors.push(msg.text().slice(0, 200)); });
    page.on('pageerror', (err) => consoleErrors.push(String(err).slice(0, 200)));

    const start = Date.now();
    const response = await page.goto(url, { waitUntil: 'load', timeout: 20000 });
    const loadTimeMs = Date.now() - start;

    const timing = await page.evaluate(() => {
      const nav = performance.getEntriesByType('navigation')[0];
      return nav ? {
        domContentLoadedMs: Math.round(nav.domContentLoadedEventEnd),
        loadEventMs: Math.round(nav.loadEventEnd),
      } : { domContentLoadedMs: null, loadEventMs: null };
    });

    const hasCta = await page.evaluate((patternSource) => {
      const re = new RegExp(patternSource, 'i');
      const els = document.querySelectorAll('button, a');
      for (const el of els) { if (re.test(el.textContent || '')) return true; }
      return false;
    }, CTA_PATTERN.source);

    const title = await page.title();
    const bodyText = await page.evaluate(() => document.body ? document.body.innerText.length : 0);

    // Mobile pass -- does it actually render sanely at a phone width.
    const mobilePage = await browser.newPage({ viewport: { width: 390, height: 844 } });
    let mobileOk = true;
    try {
      await mobilePage.goto(url, { waitUntil: 'load', timeout: 15000 });
      const overflow = await mobilePage.evaluate(() => document.documentElement.scrollWidth > window.innerWidth + 10);
      mobileOk = !overflow;
    } catch { mobileOk = false; }
    await mobilePage.close();

    result.ok = true;
    result.status_code = response ? response.status() : null;
    result.load_time_ms = loadTimeMs;
    result.dom_content_loaded_ms = timing.domContentLoadedMs;
    result.title = title;
    result.body_text_length = bodyText;
    result.has_cta = hasCta;
    result.mobile_renders_without_overflow = mobileOk;
    result.console_error_count = consoleErrors.length;
    result.console_errors = consoleErrors.slice(0, 10);
    await page.close();
  } catch (e) {
    result.ok = false;
    result.error = String(e).slice(0, 500);
  } finally {
    await browser.close();
  }
  return result;
}

const url = process.argv[2];
if (!url) {
  console.log(JSON.stringify({ ok: false, error: 'no URL given' }));
  process.exit(1);
}
audit(url).then((r) => console.log(JSON.stringify(r)));
