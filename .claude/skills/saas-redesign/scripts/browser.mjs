// Minimal headless-Chrome driver over the DevTools protocol, for verifying the
// redesign when no browser MCP is available (or its profile is locked).
//
// Usage:  OUT_DIR=/path/for/screenshots node browser.mjs ./my-steps.mjs
//
// The steps module default-exports an async function that receives `page`:
//   export default async (page) => {
//     await page.size(375, 800)                 // true viewport (plain --window-size clamps to ~500px)
//     await page.go('http://localhost:3000/orders')
//     console.log(await page.overflow())        // elements wider than the viewport, not inside a scroller
//     await page.click('.menu-toggle')
//     await page.shot('orders-375')             // -> $OUT_DIR/orders-375.png (view it with the Read tool)
//     console.log(await page.eval('location.pathname'))
//   }
// Console errors/warnings and uncaught exceptions are printed at the end.
// Needs Node 22+ (global WebSocket) and Google Chrome.
import { spawn } from 'node:child_process'
import { mkdtempSync, mkdirSync, rmSync, writeFileSync } from 'node:fs'
import { tmpdir } from 'node:os'
import { join, resolve } from 'node:path'
import { pathToFileURL } from 'node:url'

const CHROME = process.env.CHROME || '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'
const OUT_DIR = process.env.OUT_DIR || process.cwd()
mkdirSync(OUT_DIR, { recursive: true })

const profile = mkdtempSync(join(tmpdir(), 'saas-redesign-chrome-'))
const port = 9300 + Math.floor(Math.random() * 600)
const chrome = spawn(CHROME, ['--headless=new', '--disable-gpu', '--hide-scrollbars',
  `--user-data-dir=${profile}`, `--remote-debugging-port=${port}`, 'about:blank'], { stdio: 'ignore' })
const sleep = ms => new Promise(r => setTimeout(r, ms))

let targets
for (let i = 0; i < 50 && !targets; i++) {
  try { targets = await (await fetch(`http://127.0.0.1:${port}/json`)).json() } catch { await sleep(200) }
}
if (!targets) { console.error('Chrome did not start'); chrome.kill(); process.exit(1) }

const ws = new WebSocket(targets.find(t => t.type === 'page').webSocketDebuggerUrl)
await new Promise(r => { ws.onopen = r })
let nextId = 0
const pending = new Map()
const logs = []
ws.onmessage = e => {
  const m = JSON.parse(e.data)
  if (m.id && pending.has(m.id)) { pending.get(m.id)(m); pending.delete(m.id) }
  if (m.method === 'Runtime.consoleAPICalled' && ['error', 'warning'].includes(m.params.type)) {
    logs.push(`${m.params.type}: ${m.params.args.map(a => a.value ?? a.description).join(' ')}`)
  }
  if (m.method === 'Runtime.exceptionThrown') logs.push(`exception: ${m.params.exceptionDetails.exception?.description}`)
}
const send = (method, params = {}) => new Promise(r => { const id = ++nextId; pending.set(id, r); ws.send(JSON.stringify({ id, method, params })) })
await send('Runtime.enable')
await send('Page.enable')

const page = {
  async size(width, height = 1000) {
    await send('Emulation.setDeviceMetricsOverride', { width, height, deviceScaleFactor: 1, mobile: false })
  },
  async go(url, settleMs = 2500) { await send('Page.navigate', { url }); await sleep(settleMs) },
  async eval(expr) {
    const r = await send('Runtime.evaluate', { expression: expr, awaitPromise: true, returnByValue: true })
    return r.result?.result?.value ?? r.result?.exceptionDetails?.exception?.description
  },
  // Dispatches a real click event. ProfileMenu/LanguageSwitcher items listen on
  // mousedown, so use page.mousedown() for those.
  async click(selector) { return page.eval(`document.querySelector(${JSON.stringify(selector)})?.click() ?? 'not found'`) },
  async mousedown(selector) {
    return page.eval(`(() => { const el = document.querySelector(${JSON.stringify(selector)}); if (!el) return 'not found';
      el.dispatchEvent(new MouseEvent('mousedown', { bubbles: true })) })()`)
  },
  async key(key) {
    await send('Input.dispatchKeyEvent', { type: 'keyDown', key, code: key })
    await send('Input.dispatchKeyEvent', { type: 'keyUp', key, code: key })
  },
  // Lists elements sticking out past the viewport's right edge that no scrolling
  // ancestor contains: the cause of horizontal page scroll at narrow widths.
  async overflow() {
    return page.eval(`(() => {
      const W = innerWidth, hits = new Set()
      document.querySelectorAll('body *').forEach(el => {
        const b = el.getBoundingClientRect()
        if (b.width === 0 || b.right <= W + 1) return
        for (let a = el.parentElement; a; a = a.parentElement) if (getComputedStyle(a).overflowX !== 'visible') return
        hits.add(el.tagName.toLowerCase() + (el.classList.length ? '.' + [...el.classList].join('.') : ''))
      })
      return { viewport: W, scrollWidth: document.documentElement.scrollWidth, offenders: [...hits].slice(0, 10) }
    })()`)
  },
  async shot(name, fullPage = false) {
    const r = await send('Page.captureScreenshot', { format: 'png', captureBeyondViewport: fullPage })
    const file = join(OUT_DIR, `${name}.png`)
    writeFileSync(file, Buffer.from(r.result.data, 'base64'))
    return file
  },
  sleep,
}

try {
  const steps = await import(pathToFileURL(resolve(process.argv[2])).href)
  await steps.default(page)
} catch (e) {
  console.error('step error:', e)
}
if (logs.length) console.log('console:\n' + logs.join('\n'))
ws.close()
chrome.kill()
await sleep(300)
rmSync(profile, { recursive: true, force: true })
process.exit(0)
