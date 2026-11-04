/**
 * Static server for the Atlas SPA (same approach as Dynamo, no npm deps).
 * Serves dist/, falls back to index.html, caches hashed assets, gzips text.
 */
const http = require('http')
const fs = require('fs')
const path = require('path')
const zlib = require('zlib')

const DIST = path.join(__dirname, 'dist')
const PORT = parseInt(process.env.PORT || '8080', 10)
const MIME = {
  '.html': 'text/html; charset=utf-8', '.js': 'application/javascript; charset=utf-8',
  '.css': 'text/css; charset=utf-8', '.json': 'application/json; charset=utf-8',
  '.svg': 'image/svg+xml', '.png': 'image/png', '.ico': 'image/x-icon',
  '.woff': 'font/woff', '.woff2': 'font/woff2', '.map': 'application/json',
}
const GZIP = new Set(['.html', '.js', '.css', '.json', '.svg', '.map'])

function send(req, res, file) {
  const ext = path.extname(file).toLowerCase()
  const headers = {
    'Content-Type': MIME[ext] || 'application/octet-stream',
    'X-Content-Type-Options': 'nosniff',
    'X-Frame-Options': 'DENY',
    'Referrer-Policy': 'strict-origin-when-cross-origin',
    'Cache-Control': file.includes(`${path.sep}assets${path.sep}`) ? 'public, max-age=31536000, immutable' : 'no-cache',
  }
  const stream = fs.createReadStream(file)
  stream.on('error', () => { res.writeHead(500); res.end('Internal server error') })
  if (GZIP.has(ext) && /\bgzip\b/.test(req.headers['accept-encoding'] || '')) {
    headers['Content-Encoding'] = 'gzip'
    res.writeHead(200, headers)
    stream.pipe(zlib.createGzip()).pipe(res)
  } else {
    res.writeHead(200, headers)
    stream.pipe(res)
  }
}

http.createServer((req, res) => {
  let pathname = '/'
  try { pathname = decodeURIComponent(new URL(req.url, 'http://x').pathname) } catch { /* keep / */ }
  if (pathname === '/health' || pathname === '/health/') {
    res.writeHead(200, { 'Content-Type': 'application/json' }); res.end('{"status":"ok"}'); return
  }
  const file = path.join(DIST, pathname)
  if (!file.startsWith(DIST)) { res.writeHead(403); res.end('Forbidden'); return }
  fs.stat(file, (err, st) => send(req, res, !err && st.isFile() ? file : path.join(DIST, 'index.html')))
}).listen(PORT, '0.0.0.0', () => console.log(`Venture GP Atlas frontend on port ${PORT}`))
