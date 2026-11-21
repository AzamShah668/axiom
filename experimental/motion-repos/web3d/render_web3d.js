// Headless three.js renderer for our editing styles (three + postprocessing + rapier, all MIT).
// The picture is a pure function of time: each scene exports init(ctx) and render(t).
//   node scripts/video/web3d/render_web3d.js <scene> --dur 6 --out x.mp4 [--fps 30] [--size 1920x1080] [--workers 3] [--params '{"k":1}' | --params @file.json] [--assets work/media] [--from S --total S: render a slice of a longer film]
// Needs: sh scripts/setup/fetch_motion_tools.sh (puts node_modules in $WEB3D, default /home/user/tools/web3d).
const http = require('http'), fs = require('fs'), path = require('path'), os = require('os');
const { execFileSync } = require('child_process');
const { chromium } = require('playwright');
const a = process.argv.slice(2), opt = (k, d) => { const i = a.indexOf('--' + k); return i >= 0 ? a[i + 1] : d; };
const scene = a[0], fps = +opt('fps', 30), dur = +opt('dur', 6), out = path.resolve(opt('out', `${scene}.mp4`));
const [W, H] = opt('size', '1920x1080').split('x').map(Number), workers = +opt('workers', 3);
let params = opt('params', '{}'); if (params.startsWith('@')) params = fs.readFileSync(params.slice(1), 'utf8');
const ASSETS = path.resolve(opt('assets', 'work/media')), from = +opt('from', 0), total = +opt('total', 0) || dur, ffmpeg = process.env.FFMPEG || 'ffmpeg';
const HERE = __dirname, MODS = path.join(process.env.WEB3D || '/home/user/tools/web3d', 'node_modules');
const TYPES = { '.js': 'text/javascript', '.mjs': 'text/javascript', '.html': 'text/html', '.wasm': 'application/wasm', '.jpg': 'image/jpeg', '.png': 'image/png', '.ttf': 'font/ttf' };
const srv = http.createServer((q, r) => {
  const u = decodeURIComponent(q.url.split('?')[0]);
  const f = u.startsWith('/node_modules/') ? path.join(MODS, u.slice(14)) : u.startsWith('/assets/') ? path.join(ASSETS, u.slice(8)) : path.join(HERE, u);
  fs.readFile(f, (e, b) => { if (e) { r.writeHead(404); return r.end(); } r.writeHead(200, { 'Content-Type': TYPES[path.extname(f)] || 'application/octet-stream' }); r.end(b); });
});
(async () => {
  await new Promise(ok => srv.listen(0, ok));
  const port = srv.address().port, N = Math.round(dur * fps), tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'web3d-'));
  const browser = await chromium.launch({ args: ['--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist'] });
  const t0 = Date.now();
  const stills = opt('stills', '');                 // --stills 1.5,8,12 -> <out dir>/s_<t>.jpg review stills
  if (stills) {
    const page = await browser.newPage({ viewport: { width: W, height: H } });
    page.on('pageerror', e => { console.error('[pageerror]', e.message); process.exit(1); });
    await page.goto(`http://127.0.0.1:${port}/page.html?scene=${scene}&w=${W}&h=${H}&dur=${total}`);
    await page.evaluate(p => window.START(p), params);
    await page.waitForFunction('window.READY === true', null, { timeout: 120000 });
    fs.mkdirSync(out, { recursive: true });
    for (const t of stills.split(',')) fs.writeFileSync(path.join(out, `s_${t}.jpg`), Buffer.from(await page.evaluate(x => window.frameAt(x), +t), 'base64'));
    await browser.close(); srv.close(); console.log('stills', out); return;
  }
  await Promise.all([...Array(workers)].map(async (_, w) => {
    const page = await browser.newPage({ viewport: { width: W, height: H } });
    page.on('pageerror', e => { console.error('[pageerror]', e.message); process.exit(1); });
    page.on('console', m => m.type() === 'error' && console.error('[page]', m.text()));
    await page.goto(`http://127.0.0.1:${port}/page.html?scene=${scene}&w=${W}&h=${H}&dur=${total}`);
    await page.evaluate(p => window.START(p), params);
    await page.waitForFunction('window.READY === true', null, { timeout: 120000 });
    for (let i = w; i < N; i += workers) {
      const b64 = await page.evaluate(t => window.frameAt(t), from + i / fps);
      fs.writeFileSync(path.join(tmp, `f${String(i).padStart(6, '0')}.jpg`), Buffer.from(b64, 'base64'));
      if (i % (workers * 30) === w) process.stdout.write(`w${w} ${i}/${N} ${((Date.now() - t0) / 1000).toFixed(0)}s\n`);
    }
  }));
  await browser.close(); srv.close();
  execFileSync(ffmpeg, ['-v', 'error', '-y', '-framerate', String(fps), '-i', path.join(tmp, 'f%06d.jpg'), '-c:v', 'libx264', '-preset', 'medium', '-crf', '16', '-pix_fmt', 'yuv420p', out]);
  fs.rmSync(tmp, { recursive: true });
  console.log(`done ${out} ${N} frames ${((Date.now() - t0) / 1000).toFixed(1)}s (${((Date.now() - t0) / N).toFixed(0)} ms/frame)`);
})();
