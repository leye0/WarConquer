#!/usr/bin/env node
// Zero-dependency, full-page HTML screenshots using Chrome DevTools Protocol.
import { spawn } from 'node:child_process';
import { existsSync, mkdirSync, mkdtempSync, readFileSync, realpathSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { dirname, isAbsolute, join, relative, resolve, sep } from 'node:path';
import { pathToFileURL } from 'node:url';
import { performance } from 'node:perf_hooks';

const started = performance.now();
const workspace = realpathSync(process.env.GITHUB_WORKSPACE || process.cwd());
const batch = process.argv[2] === '--nul-list';
const sources = batch
  ? readFileSync(process.argv[3]).toString('utf8').split('\0').filter(Boolean)
  : [process.argv[2] || 'patate.html'];
if (!sources.length) throw new Error('No HTML files to render');
const destination = resolve(process.argv[batch ? 4 : 3] || (batch ? 'renders' : 'render.png'));
const pages = [...new Set(sources)].map(source => {
  const html = realpathSync(resolve(workspace, source));
  const rel = relative(workspace, html);
  if (rel === '..' || rel.startsWith('..' + sep) || isAbsolute(rel) || !/\.html?$/i.test(html)) {
    throw new Error('HTML path must be a .html file inside the repository: ' + source);
  }
  return { html, rel };
});
const chrome = process.env.CHROME_BIN || '/usr/bin/google-chrome';
if (!existsSync(chrome)) throw new Error('Chrome is unavailable: ' + chrome);
const profile = mkdtempSync(join(tmpdir(), 'warconquer-cdp-'));
const browser = spawn(chrome, [
  '--headless=new', '--no-sandbox', '--disable-gpu', '--disable-dev-shm-usage',
  '--disable-background-networking', '--no-first-run', '--no-default-browser-check',
  '--hide-scrollbars', '--window-size=1280,800', '--remote-debugging-port=0',
  '--user-data-dir=' + profile, 'about:blank'
], { stdio: 'ignore' });

const pause = ms => new Promise(done => setTimeout(done, ms));
async function withTimeout(promise, ms, what) {
  let timer;
  try {
    return await Promise.race([
      promise,
      new Promise((_, reject) => { timer = setTimeout(() => reject(new Error('Timeout: ' + what)), ms); })
    ]);
  } finally { clearTimeout(timer); }
}
async function getPageSocket() {
  const portFile = join(profile, 'DevToolsActivePort');
  const deadline = performance.now() + 20000;
  while (performance.now() < deadline) {
    if (browser.exitCode !== null) throw new Error('Chrome exited before starting CDP');
    if (existsSync(portFile)) {
      try {
        const port = readFileSync(portFile, 'utf8').split(String.fromCharCode(10))[0].trim();
        const response = await fetch('http://127.0.0.1:' + port + '/json/list', {
          signal: AbortSignal.timeout(1000)
        });
        const targets = await response.json();
        const page = targets.find(t => t.type === 'page');
        if (page?.webSocketDebuggerUrl) return page.webSocketDebuggerUrl;
      } catch {
        // CDP's HTTP endpoint may not be ready immediately.
      }
    }
    await pause(50);
  }
  throw new Error('Chrome did not expose a CDP page within 20 seconds');
}
function connect(url) {
  return new Promise((resolve, reject) => {
    const socket = new WebSocket(url);
    const pending = new Map();
    const events = new Map();
    let serial = 0;
    socket.addEventListener('error', () => reject(new Error('CDP WebSocket connection failed')), { once: true });
    socket.addEventListener('open', () => resolve({
      send(method, params = {}) {
        const id = ++serial;
        return withTimeout(new Promise((ok, fail) => {
          pending.set(id, { ok, fail });
          socket.send(JSON.stringify({ id, method, params }));
        }), 10000, method);
      },
      once(method) {
        return withTimeout(new Promise(ok => {
          const queue = events.get(method) || [];
          queue.push(ok);
          events.set(method, queue);
        }), 10000, method);
      },
      close() { socket.close(); }
    }), { once: true });
    socket.addEventListener('message', event => {
      const message = JSON.parse(event.data);
      if (message.id) {
        const p = pending.get(message.id);
        if (!p) return;
        pending.delete(message.id);
        if (message.error) p.fail(new Error(JSON.stringify(message.error)));
        else p.ok(message.result || {});
      } else if (message.method) {
        const queue = events.get(message.method);
        if (queue?.length) queue.shift()(message.params || {});
      }
    });
  });
}
let client;
try {
  const socketUrl = await getPageSocket();
  const readyAt = performance.now();
  client = await connect(socketUrl);
  await client.send('Page.enable');
  await client.send('Runtime.enable');
  await client.send('Emulation.setDeviceMetricsOverride', {
    width: 1280, height: 800, deviceScaleFactor: 1, mobile: false
  });
  const entries = [];
  for (const { html, rel } of pages) {
    const pageStarted = performance.now();
    const loaded = client.once('Page.loadEventFired');
    const nav = await client.send('Page.navigate', { url: pathToFileURL(html).href });
    if (nav.errorText) throw new Error('Navigation failed: ' + nav.errorText);
    await loaded;
    await client.send('Runtime.evaluate', {
      expression: "(async()=>{await document.fonts.ready;await Promise.all([...document.images].map(img=>img.complete?null:new Promise(done=>{img.addEventListener('load',done,{once:true});img.addEventListener('error',done,{once:true});})));await new Promise(done=>requestAnimationFrame(()=>requestAnimationFrame(done)));})()",
      awaitPromise: true
    });
    const metrics = await client.send('Page.getLayoutMetrics');
    const size = metrics.cssContentSize || metrics.contentSize;
    const width = Math.ceil(Math.max(size.width, 1280));
    const height = Math.ceil(Math.max(size.height, 800));
    const shot = await client.send('Page.captureScreenshot', {
      format: 'png', fromSurface: true, captureBeyondViewport: true,
      clip: { x: 0, y: 0, width, height, scale: 1 }
    });
    const output = batch ? resolve(destination, rel + '.png') : destination;
    mkdirSync(dirname(output), { recursive: true });
    writeFileSync(output, Buffer.from(shot.data, 'base64'));
    const entry = {
      source: rel, png: batch ? rel + '.png' : output,
      width, height, elapsedMs: Math.round(performance.now() - pageStarted)
    };
    entries.push(entry);
    console.log('PAGE_RENDER ' + JSON.stringify(entry));
  }
  if (batch) {
    writeFileSync(join(destination, 'manifest.json'), JSON.stringify({
      engine: 'chrome-cdp',
      chromeStarts: 1,
      chromeStartupMs: Math.round(readyAt - started),
      pages: entries
    }, null, 2) + '\n');
  }
  console.log('RENDER_METRICS ' + JSON.stringify({
    chromeStartupMs: Math.round(readyAt - started),
    browserWorkMs: Math.round(performance.now() - readyAt),
    totalMs: Math.round(performance.now() - started),
    pagesRendered: entries.length
  }));
} finally {
  client?.close();
  browser.kill('SIGTERM');
}
