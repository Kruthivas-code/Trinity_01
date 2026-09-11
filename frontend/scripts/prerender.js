/* Build-time prerendering: after `craco build`, launch the built SPA in a
 * headless browser, snapshot the fully-rendered HTML (content + per-page meta)
 * for every docs route, and write static build/<slug>/index.html files so any
 * crawler (JS or not) gets real content. Non-fatal: on any failure the build
 * still succeeds and falls back to the normal client-rendered SPA. */
const fs = require('fs');
const path = require('path');
const http = require('http');

const BUILD_DIR = path.join(__dirname, '..', 'build');
const PORT = Number(process.env.PRERENDER_PORT || 45999);
// The headless capture happens against this internal localhost server, so any
// canonical/og:url meta the app writes using window.location.origin points here.
// Rewrite it back to the real public origin before writing the static file.
const PUBLIC_ORIGIN = (process.env.PRERENDER_PUBLIC_ORIGIN || '').trim().replace(/\/$/, '');

function backendUrl() {
  if (process.env.REACT_APP_BACKEND_URL) return process.env.REACT_APP_BACKEND_URL.trim();
  try {
    const env = fs.readFileSync(path.join(__dirname, '..', '.env'), 'utf8');
    const m = env.match(/REACT_APP_BACKEND_URL=(.*)/);
    if (m) return m[1].trim();
  } catch (_) {}
  return '';
}

const MIME = {
  '.html': 'text/html', '.js': 'application/javascript', '.css': 'text/css',
  '.json': 'application/json', '.png': 'image/png', '.jpg': 'image/jpeg',
  '.jpeg': 'image/jpeg', '.svg': 'image/svg+xml', '.ico': 'image/x-icon',
  '.woff': 'font/woff', '.woff2': 'font/woff2', '.map': 'application/json',
  '.txt': 'text/plain', '.webp': 'image/webp', '.gif': 'image/gif',
};

function startServer() {
  return http.createServer((req, res) => {
    const urlPath = decodeURIComponent(req.url.split('?')[0]);
    const filePath = path.join(BUILD_DIR, urlPath);
    if (urlPath !== '/' && fs.existsSync(filePath) && fs.statSync(filePath).isFile()) {
      const ext = path.extname(filePath);
      res.writeHead(200, { 'Content-Type': MIME[ext] || 'application/octet-stream' });
      fs.createReadStream(filePath).pipe(res);
    } else {
      // SPA fallback → serve the pristine shell so the app boots and routes client-side
      res.writeHead(200, { 'Content-Type': 'text/html' });
      fs.createReadStream(SHELL_PATH).pipe(res);
    }
  }).listen(PORT);
}

let SHELL_PATH;

async function getSlugs(base) {
  if (!base) return [];
  try {
    const r = await fetch(`${base}/api/kb/articles`);
    const d = await r.json();
    return (d.articles || []).map((x) => x.slug).filter(Boolean);
  } catch (e) {
    console.error('prerender: could not fetch slugs:', e.message);
    return [];
  }
}

(async () => {
  const indexPath = path.join(BUILD_DIR, 'index.html');
  if (!fs.existsSync(indexPath)) {
    console.log('prerender: build/index.html missing, skipping.');
    return;
  }
  // Keep an untouched copy of the SPA shell for the fallback server.
  SHELL_PATH = path.join(BUILD_DIR, 'index.shell.html');
  fs.copyFileSync(indexPath, SHELL_PATH);

  const base = backendUrl();
  const slugs = await getSlugs(base);
  if (slugs.length === 0) {
    console.log('prerender: no routes discovered, skipping.');
    fs.unlinkSync(SHELL_PATH);
    return;
  }

  let puppeteer;
  try {
    puppeteer = require('puppeteer');
  } catch (e) {
    console.log('prerender: puppeteer not available, skipping.');
    fs.unlinkSync(SHELL_PATH);
    return;
  }

  // Process slugs first ('/docs/<slug>'), then '/' last so the fallback shell stays pristine.
  const routes = slugs.map((s) => '/docs/' + s).concat(['/']);
  console.log(`prerender: ${routes.length} routes via ${base}`);
  if (!PUBLIC_ORIGIN) {
    console.warn('prerender: PRERENDER_PUBLIC_ORIGIN not set — canonical/og:url in prerendered pages will point to the internal localhost capture server. Set it to your real production origin (e.g. https://docs.example.com).');
  }

  const server = startServer();
  const launchOpts = { headless: 'new', args: ['--no-sandbox', '--disable-setuid-sandbox'] };
  if (process.env.PUPPETEER_EXECUTABLE_PATH) launchOpts.executablePath = process.env.PUPPETEER_EXECUTABLE_PATH;

  let browser, done = 0;
  try {
    browser = await puppeteer.launch(launchOpts);
    for (const route of routes) {
      let page;
      try {
        page = await browser.newPage();
        // Block analytics / heavy 3rd-party requests so the page settles quickly
        // and never keeps the network "busy" (PostHog etc. hang networkidle).
        await page.setRequestInterception(true);
        page.on('request', (req) => {
          const u = req.url();
          if (/posthog|i\.posthog\.com|google-analytics|googletagmanager|hotjar|segment|fullstory/i.test(u)) {
            req.abort().catch(() => {});
          } else {
            req.continue().catch(() => {});
          }
        });
        const work = (async () => {
          await page.goto(`http://localhost:${PORT}${route}`, { waitUntil: 'domcontentloaded', timeout: 20000 });
          await page.waitForSelector('[data-prerender-ready="true"]', { timeout: 12000 }).catch(() => {});
          await new Promise((r) => setTimeout(r, 400));
          let html = '<!doctype html>\n' + (await page.content());
          if (PUBLIC_ORIGIN) {
            html = html.split(`http://localhost:${PORT}`).join(PUBLIC_ORIGIN);
          }
          const outDir = route === '/' ? BUILD_DIR : path.join(BUILD_DIR, route);
          fs.mkdirSync(outDir, { recursive: true });
          fs.writeFileSync(path.join(outDir, 'index.html'), html);
        })();
        // Hard per-route ceiling so a single stuck page can never hang the build.
        await Promise.race([
          work,
          new Promise((_, rej) => setTimeout(() => rej(new Error('hard timeout')), 35000)),
        ]);
        done++;
      } catch (e) {
        console.error(`prerender: ${route} failed: ${e.message}`);
      } finally {
        if (page) await page.close().catch(() => {});
      }
    }
  } catch (e) {
    console.error('prerender: browser launch failed:', e.message);
  } finally {
    if (browser) await browser.close().catch(() => {});
    server.close();
    if (fs.existsSync(SHELL_PATH)) fs.unlinkSync(SHELL_PATH);
  }
  console.log(`prerender: wrote ${done}/${routes.length} static pages.`);
})();
