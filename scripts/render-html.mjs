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
const scenarioMode = process.argv[2] === '--scenario';
const inlineMode = process.argv[2] === '--interactive';
const interactive = scenarioMode || inlineMode;
const batch = process.argv[2] === '--nul-list';
const scenarioFile = scenarioMode ? realpathSync(resolve(workspace, process.argv[3])) : null;
if (scenarioFile) {
  const relScenario = relative(workspace, scenarioFile);
  if (relScenario === '..' || relScenario.startsWith('..' + sep) || isAbsolute(relScenario) || !/\.json$/i.test(scenarioFile)) {
    throw new Error('Scenario JSON must be inside the repository');
  }
}
const scenario = scenarioMode ? JSON.parse(readFileSync(scenarioFile, 'utf8'))
  : inlineMode ? { html: process.argv[3], steps: JSON.parse(process.env.RENDER_ACTIONS_JSON || '[]') } : null;
if (interactive && (typeof scenario.html !== 'string' || !Array.isArray(scenario.steps) || scenario.steps.length > 50)) {
  throw new Error('Scenario requires html and steps (max 50)');
}
const sources = interactive ? [scenario.html] : batch
  ? readFileSync(process.argv[3]).toString('utf8').split('\0').filter(Boolean)
  : [process.argv[2] || 'patate.html'];
if (!sources.length) throw new Error('No HTML files to render');
const destination = resolve(process.argv[interactive || batch ? 4 : 3] || (interactive || batch ? 'renders' : 'render.png'));
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
  const actionResults = [];
  async function settle() {
    await client.send('Runtime.evaluate', {
      expression: "new Promise(done => requestAnimationFrame(() => requestAnimationFrame(done)))",
      awaitPromise: true
    });
  }
  async function inspect(selector, withPosition = true) {
    if (typeof selector !== 'string' || !selector) throw new Error('Missing CSS selector');
    const result = await client.send('Runtime.evaluate', {
      expression: "(() => {const el = document.querySelector(" + JSON.stringify(selector) + ");if(!el)return {error:'Element not found'};" +
        (withPosition ? "el.scrollIntoView({block:'center',inline:'nearest'});const r=el.getBoundingClientRect();return {x:r.left+r.width/2,y:r.top+r.height/2,width:r.width,height:r.height};" :
          "return {text:el.textContent||''};") + "})()",
      returnByValue: true
    });
    if (result.exceptionDetails) throw new Error('Invalid selector: ' + selector);
    const value = result.result?.value;
    if (value?.error) throw new Error(selector + ': ' + value.error);
    if (!value) throw new Error('Cannot inspect: ' + selector);
    if (withPosition && (value.width <= 0 || value.height <= 0)) throw new Error('Element has no clickable area: ' + selector);
    return value;
  }
  async function click(selector) {
    const { x, y } = await inspect(selector);
    await client.send('Input.dispatchMouseEvent', { type: 'mouseMoved', x, y });
    await client.send('Input.dispatchMouseEvent', { type: 'mousePressed', x, y, button: 'left', clickCount: 1 });
    await client.send('Input.dispatchMouseEvent', { type: 'mouseReleased', x, y, button: 'left', clickCount: 1 });
  }
  async function press(key) {
    const map = {
      Enter: ['Enter', 13], Escape: ['Escape', 27], Tab: ['Tab', 9],
      Backspace: ['Backspace', 8], ArrowUp: ['ArrowUp', 38],
      ArrowDown: ['ArrowDown', 40], ArrowLeft: ['ArrowLeft', 37],
      ArrowRight: ['ArrowRight', 39]
    };
    if (!Object.hasOwn(map, key)) throw new Error('Unsupported key: ' + key);
    const [code, windowsVirtualKeyCode] = map[key];
    const params = { key, code, windowsVirtualKeyCode };
    await client.send('Input.dispatchKeyEvent', { type: 'rawKeyDown', ...params });
    await client.send('Input.dispatchKeyEvent', { type: 'keyUp', ...params });
  }
  async function typeInto(selector, text) {
    if (typeof text !== 'string') throw new Error('Type action requires text');
    await click(selector);
    await client.send('Input.dispatchKeyEvent', { type: 'rawKeyDown', key: 'Control', code: 'ControlLeft', windowsVirtualKeyCode: 17, modifiers: 2 });
    await client.send('Input.dispatchKeyEvent', { type: 'rawKeyDown', key: 'a', code: 'KeyA', windowsVirtualKeyCode: 65, modifiers: 2 });
    await client.send('Input.dispatchKeyEvent', { type: 'keyUp', key: 'a', code: 'KeyA', windowsVirtualKeyCode: 65, modifiers: 2 });
    await client.send('Input.dispatchKeyEvent', { type: 'keyUp', key: 'Control', code: 'ControlLeft', windowsVirtualKeyCode: 17 });
    await client.send('Input.insertText', { text });
  }
  async function capture(rel, name) {
    if (!/^[a-zA-Z0-9_-]+$/.test(name)) throw new Error('Invalid screenshot name: ' + name);
    await settle();
    const metrics = await client.send('Page.getLayoutMetrics');
    const size = metrics.cssContentSize || metrics.contentSize;
    const width = Math.ceil(Math.max(size.width, 1280));
    const height = Math.ceil(Math.max(size.height, 800));
    const shot = await client.send('Page.captureScreenshot', {
      format: 'png', fromSurface: true, captureBeyondViewport: true,
      clip: { x: 0, y: 0, width, height, scale: 1 }
    });
    const png = interactive ? name + '.png' : batch ? rel + '.png' : destination;
    const output = interactive || batch ? resolve(destination, png) : destination;
    mkdirSync(dirname(output), { recursive: true });
    writeFileSync(output, Buffer.from(shot.data, 'base64'));
    const entry = { source: rel, png, width, height, elapsedMs: Math.round(performance.now() - readyAt) };
    entries.push(entry);
    console.log('PAGE_RENDER ' + JSON.stringify(entry));
  }
  for (const { html, rel } of pages) {
    const loaded = client.once('Page.loadEventFired');
    const nav = await client.send('Page.navigate', { url: pathToFileURL(html).href });
    if (nav.errorText) throw new Error('Navigation failed: ' + nav.errorText);
    await loaded;
    await client.send('Runtime.evaluate', {
      expression: "(async()=>{await document.fonts.ready;await Promise.all([...document.images].map(img=>img.complete?null:new Promise(done=>{img.addEventListener('load',done,{once:true});img.addEventListener('error',done,{once:true});})));})()",
      awaitPromise: true
    });
    if (!interactive) {
      await capture(rel, 'render');
      continue;
    }
    await capture(rel, '00-initial');
    for (const [index, step] of scenario.steps.entries()) {
      const actionStart = performance.now();
      switch (step.action) {
        case 'click': await click(step.selector); break;
        case 'type': await typeInto(step.selector, step.text); break;
        case 'press': await press(step.key); break;
        case 'wait':
          if (!Number.isInteger(step.ms) || step.ms < 0 || step.ms > 5000) throw new Error('wait.ms must be 0-5000');
          await pause(step.ms); break;
        case 'assertText': {
          const result = await inspect(step.selector, false);
          if (typeof step.includes !== 'string' || !result.text.includes(step.includes)) {
            throw new Error('Text assertion failed at ' + step.selector + ': ' + JSON.stringify(result.text));
          }
          break;
        }
        case 'screenshot': await capture(rel, step.name); break;
        default: throw new Error('Unknown action at step ' + index + ': ' + step.action);
      }
      if (step.action !== 'screenshot') await settle();
      const action = { index, action: step.action, elapsedMs: Math.round(performance.now() - actionStart) };
      actionResults.push(action);
      console.log('ACTION_METRICS ' + JSON.stringify(action));
    }
    await capture(rel, '99-final');
  }
  if (batch || interactive) {
    writeFileSync(join(destination, 'manifest.json'), JSON.stringify({
      engine: 'chrome-cdp', chromeStarts: 1,
      chromeStartupMs: Math.round(readyAt - started),
      screenshots: entries, actions: actionResults
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
