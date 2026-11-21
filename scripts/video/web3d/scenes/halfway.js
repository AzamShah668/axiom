// 09 Short 4 "halfway" (owner's script, 2026-11-21): universe half its life -> DESI 3D map of 1 crore+ galaxies -> dark energy
// weakening -> Henry Tye's model -> 33 billion years, today 13.8 -> expansion stops, shrinks to a point -> an Indian physicist
// (Ashtekar) says it is not the end -> full video. Plain text only; photos whole; SOLID black title patch (owner rule).
import * as THREE from 'three';
import { cl, ease, easeOut, easeInOut, rng, stars, glow, Overlay, composer } from './_lib.js';

const AMBER = '#f5c242', AMBER_HEX = 0xf5c242, BLUE = '#9fd0ff';
const SHOT_WORDS = [0, 7, 26, 44, 56, 80, 97, 110];
const TITLE = ['THE UNIVERSE IS', 'HALFWAY DEAD'], PATCH = 380;
let R, W, H, S, C, comp, ov, wd, st, ev, total;
let pt, gal, galBase, galCol, desi, beam, wedge, wedgeBase, pushers, core, ring, photos = {};
const w = i => wd[i][0];
const shotAt = t => { let i = 0; for (let k = 0; k < st.length; k++) if (t >= st[k]) i = k; return i; };
const img = src => new Promise(ok => { const im = new Image(); im.onload = () => ok(im); im.onerror = () => ok(null); im.src = src; });

function points(n, fill, size, seed) {
  const r = rng(seed), p = new Float32Array(n * 3), c = new Float32Array(n * 3), col = new THREE.Color();
  for (let i = 0; i < n; i++) { const [x, y, z, h, l] = fill(r, i); p.set([x, y, z], i * 3); col.setHSL(h, 0.7, l); c.set([col.r, col.g, col.b], i * 3); }
  const g = new THREE.BufferGeometry(); g.setAttribute('position', new THREE.BufferAttribute(p, 3)); g.setAttribute('color', new THREE.BufferAttribute(c, 3));
  const m = new THREE.Points(g, new THREE.PointsMaterial({ size, sizeAttenuation: true, vertexColors: true, transparent: true, blending: THREE.AdditiveBlending, depthWrite: false, map: dot() }));
  return [m, p.slice()];
}
let _dot; function dot() { if (_dot) return _dot; const c = document.createElement('canvas'); c.width = c.height = 64; const x = c.getContext('2d');
  const g = x.createRadialGradient(32, 32, 0, 32, 32, 32); g.addColorStop(0, '#fff'); g.addColorStop(0.3, 'rgba(255,255,255,.6)'); g.addColorStop(1, 'rgba(255,255,255,0)');
  x.fillStyle = g; x.fillRect(0, 0, 64, 64); return (_dot = new THREE.CanvasTexture(c)); }

export async function init(ctx) {
  ({ renderer: R, W, H } = ctx); wd = ctx.params.words; st = SHOT_WORDS.map(w); total = ctx.dur;
  ev = { hai0: w(6), desi: w(9), crore: w(16), galaxies: w(19), map: w(23), data: w(27), phailane: w(35), dark: w(37), kamzor: w(40),
         tye: w(47), model: w(54), umr: w(62), b33: w(64), aaj: w(69), t138: w(71), rukega: w(87), wapas: w(91), simat: w(95),
         indian: w(99), equations: w(102), nahi: w(108), kya: w(113), neeche: w(117) };
  S = new THREE.Scene(); C = new THREE.PerspectiveCamera(50, W / H, 0.1, 4000);
  const sf = stars(9000, 1200); sf.material.size = 2.0; S.add(sf);
  // the universe: a ball of galaxies whose size follows the story
  [gal, galBase] = points(5000, (r) => { const u = r() * 2 - 1, th = r() * 6.283, rr = 40 * Math.cbrt(r()), s = Math.sqrt(1 - u * u);
    return [rr * s * Math.cos(th), rr * u, rr * s * Math.sin(th), 0.08 + 0.55 * (r() < 0.5 ? 0 : 1) + 0.05 * r(), 0.55 + 0.3 * r()]; }, 2.2, 5);
  S.add(gal);
  // DESI: a dome on a ridge with a fan of fibre beams, and its wedge-shaped 3D map
  desi = new THREE.Group();
  const ridge = new THREE.Mesh(new THREE.PlaneGeometry(400, 60), new THREE.MeshBasicMaterial({ color: 0x05080f })); ridge.position.set(0, -30, -60); desi.add(ridge);
  const dome = new THREE.Mesh(new THREE.SphereGeometry(4, 48, 24, 0, Math.PI * 2, 0, Math.PI / 2), new THREE.MeshStandardMaterial({ color: 0xc8ccd6, roughness: 0.5 }));
  dome.position.set(0, -0.1, -60); desi.add(dome);
  const tower = new THREE.Mesh(new THREE.CylinderGeometry(3.6, 3.6, 10, 48), new THREE.MeshStandardMaterial({ color: 0xaab0bc, roughness: 0.6 })); tower.position.set(0, -5, -60); desi.add(tower);
  desi.add(new THREE.AmbientLight(0x445577, 0.8)); const dl = new THREE.DirectionalLight(0xffeedd, 1.5); dl.position.set(-5, 10, 5); desi.add(dl);
  beam = new THREE.Group(); const br = rng(9);
  for (let i = 0; i < 40; i++) { const m = new THREE.Mesh(new THREE.CylinderGeometry(0.03, 0.03, 300, 4), new THREE.MeshBasicMaterial({ color: AMBER_HEX, transparent: true, opacity: 0.25, blending: THREE.AdditiveBlending, depthWrite: false }));
    m.position.set(0, 150, 0); const piv = new THREE.Group(); piv.add(m); piv.rotation.set((br() - 0.5) * 0.35, 0, (br() - 0.5) * 0.35); beam.add(piv); }
  beam.position.set(0, 3, -60); desi.add(beam); S.add(desi);
  [wedge, wedgeBase] = points(9000, (r) => { const d = 6 + 120 * Math.pow(r(), 0.6), a = (r() - 0.5) * 1.6, fil = Math.sin(d * 0.35 + a * 9) * 0.5 + 0.5;
    return [d * Math.sin(a), (r() - 0.5) * 4, -d * Math.cos(a), 0.55 + 0.1 * fil, 0.35 + 0.4 * fil * r()]; }, 1.7, 13);
  S.add(wedge);
  // dark energy pushers: arrows around the ball
  pushers = new THREE.Group(); const pr = rng(4);
  for (let i = 0; i < 26; i++) { const u = pr() * 2 - 1, th = pr() * 6.283, s = Math.sqrt(1 - u * u), d = new THREE.Vector3(s * Math.cos(th), u, s * Math.sin(th));
    const a = new THREE.ArrowHelper(d, d.clone().multiplyScalar(46), 14, 0x9fd0ff, 5, 3.4); a.userData.d = d; pushers.add(a); }
  S.add(pushers);
  core = glow(0xffffff, 1); S.add(core); pt = glow(0xffffff, 1); S.add(pt);
  ring = new THREE.Mesh(new THREE.RingGeometry(0.95, 1, 128), new THREE.MeshBasicMaterial({ color: 0xffe2a0, transparent: true, blending: THREE.AdditiveBlending, depthWrite: false, side: THREE.DoubleSide })); S.add(ring);
  photos.tye = await img('/assets/assets/photos/Tye.jpg'); photos.ash = await img('/assets/assets/photos/Ashtekar.jpg');
  ov = new Overlay(W, H);
  comp = composer(R, S, C, { bloom: 1.2, threshold: 0.3, vignette: 0.5 });
}

function bar(t, x0, x1, y, fill, a) {                        // a life/timeline bar: Big Bang .. End
  const g = ov.x; g.save(); g.globalAlpha = a; g.fillStyle = 'rgba(255,255,255,.16)'; g.fillRect(x0, y - 22, x1 - x0, 44);
  g.fillStyle = AMBER; g.fillRect(x0, y - 22, (x1 - x0) * fill, 44); g.restore();
  ov.text('BIG BANG', x0, y + 70, { size: 38, align: 'left', font: 'Montserrat', weight: 800, alpha: a, shadow: false });
  ov.text('END', x1, y + 70, { size: 38, align: 'right', font: 'Montserrat', weight: 800, alpha: a, shadow: false });
}
function print(im, cx, bottom, maxW, maxH, name, a) {           // a whole photo as a framed print, or a name card if no photo
  const g = ov.x; g.save(); g.globalAlpha = a;
  if (im) { const k = Math.min(maxW / im.width, maxH / im.height), pw = im.width * k, ph = im.height * k, px = cx - pw / 2, py = bottom - ph;
    g.shadowColor = 'rgba(0,0,0,.8)'; g.shadowBlur = 40; g.fillStyle = '#f2efe8'; g.fillRect(px - 16, py - 16, pw + 32, ph + 70); g.shadowBlur = 0; g.drawImage(im, px, py, pw, ph); g.restore();
    ov.text(name, cx, bottom + 28, { size: 30, font: 'Montserrat', weight: 800, color: '#222', alpha: a, shadow: false }); return py; }
  const cw = 640, ch = 200, px = cx - cw / 2, py = bottom - ch; g.fillStyle = 'rgba(8,12,24,.88)'; g.fillRect(px, py, cw, ch); g.strokeStyle = 'rgba(255,255,255,.35)'; g.lineWidth = 3; g.strokeRect(px, py, cw, ch); g.restore();
  ov.text(name, cx, py + 80, { size: 56, font: 'Montserrat', weight: 800, alpha: a, shadow: false });
  ov.text('CORNELL UNIVERSITY', cx, py + 145, { size: 32, font: 'Montserrat', weight: 700, color: BLUE, alpha: a, shadow: false }); return py;
}
function curve(t, t0, a) {                                    // Tye-style size of the universe: grows, peaks, falls back to a point
  const x0 = 140, x1 = W - 140, y0 = H * 0.72, y1 = H * 0.55, g = ov.x, p = easeInOut((t - t0) / 1.8);
  g.save(); g.globalAlpha = a; g.fillStyle = 'rgba(4,8,18,.72)'; g.fillRect(x0 - 40, y1 - 90, x1 - x0 + 80, y0 - y1 + 150);
  g.strokeStyle = 'rgba(255,255,255,.6)'; g.lineWidth = 3; g.beginPath(); g.moveTo(x0, y1 - 20); g.lineTo(x0, y0); g.lineTo(x1, y0); g.stroke();
  g.strokeStyle = AMBER; g.lineWidth = 9; g.beginPath();
  for (let k = 0; k <= 100 * p; k++) { const u = k / 100, X = x0 + (x1 - x0) * u, Y = y0 - (y0 - y1) * Math.sin(Math.PI * Math.pow(u, 0.85)); k ? g.lineTo(X, Y) : g.moveTo(X, Y); }
  g.stroke(); g.restore();
  ov.text('SIZE OF THE UNIVERSE', x0, y1 - 55, { size: 38, align: 'left', font: 'Montserrat', weight: 800, alpha: a * 0.9, shadow: false });
  ov.text('TIME →', x1, y0 + 40, { size: 34, align: 'right', font: 'Montserrat', weight: 700, alpha: a * 0.6, shadow: false });
}

export function render(t) {
  const i = shotAt(t), u = t - st[i]; ov.clear();
  let size = 1, fov = 50, glowAmt = 0;
  desi.visible = i === 1; wedge.visible = i === 1 && t > ev.galaxies - 0.3; gal.visible = i !== 1; pushers.visible = i === 2;
  core.visible = pt.visible = i >= 5; ring.visible = i >= 5 && ring.material.opacity > 0.01;
  if (i > 0 && u < 0.35) fov += 9 * Math.pow(1 - u / 0.35, 2);

  if (i === 0) {                                              // the universe and its life bar, filling to the halfway mark
    size = 1 + 0.03 * u; C.position.set(Math.sin(u * 0.08) * 215, 14, Math.cos(u * 0.08) * 215); C.lookAt(0, 0, 0);
    bar(t, 140, W - 140, H * 0.66, 0.5 * easeOut(u / Math.max(0.6, ev.hai0 - 0.2)), 1);
    if (t > ev.hai0 - 0.3) ov.text('HALF', W / 2, H * 0.66 - 80, { size: 64, font: 'Anton', weight: 400, color: AMBER, alpha: ease((t - ev.hai0 + 0.3) / 0.15) });
  } else if (i === 1) {                                       // DESI on its ridge, fibres to the sky, then fly into its 3D map
    const fly = easeInOut((t - ev.galaxies + 0.3) / 1.6);
    if (fly <= 0) { C.position.set(0, 2 + u * 0.4, -30 + u * 1.2); C.lookAt(0, 6 + u * 2, -60); }
    else { C.position.set(18 * (1 - fly), 4 + 150 * fly, -10 + 40 * fly); C.lookAt(0, 0, -60 + 5 * fly); }
    beam.children.forEach((p, k) => { p.children[0].material.opacity = 0.18 + 0.12 * Math.sin(u * 3 + k); });
    const wp = wedge.geometry.attributes.position, rev = easeOut((t - ev.galaxies + 0.3) / 1.4);
    for (let k = 0; k < wp.count; k++) { const z = wedgeBase[k * 3 + 2], s = (-z / 126) < rev ? 1 : 0; wp.setXYZ(k, wedgeBase[k * 3] * s, wedgeBase[k * 3 + 1] * s, z * s); }
    wp.needsUpdate = true;
    if (t > ev.desi) ov.text('DESI', W / 2, H * 0.60, { size: 120, font: 'Anton', weight: 400, alpha: ease((t - ev.desi) / 0.15) * (1 - ease((t - ev.crore + 0.2) / 0.2)) });
    if (t > ev.crore) ov.text('1 CRORE+ GALAXIES', W / 2, H * 0.66, { size: 70, font: 'Anton', weight: 400, color: AMBER, alpha: ease((t - ev.crore) / 0.15) });
    if (t > ev.map) ov.text('3D MAP', W / 2, H * 0.71, { size: 56, font: 'Montserrat', weight: 800, alpha: ease((t - ev.map) / 0.15) });
  } else if (i === 2) {                                       // dark energy pushing outward, then weakening
    const weak = easeInOut((t - ev.kamzor) / 1.0), on = ease((t - ev.phailane) / 0.4);
    size = 1 + 0.12 * cl((t - ev.phailane) / 3) * (1 - 0.6 * weak);
    C.position.set(Math.sin(t * 0.07) * 225, 18, Math.cos(t * 0.07) * 225); C.lookAt(0, 0, 0);
    pushers.children.forEach(a => { const L = 2 + 16 * on * (1 - 0.75 * weak); a.setLength(L, Math.min(5, L * 0.4), 3.4); a.position.copy(a.userData.d).multiplyScalar(44 * size);
      a.line.material.transparent = a.cone.material.transparent = true; a.line.material.opacity = a.cone.material.opacity = on * (1 - 0.5 * weak); });
    if (t > ev.dark) ov.text('DARK ENERGY', W / 2, H * 0.64, { size: 72, font: 'Anton', weight: 400, color: BLUE, alpha: ease((t - ev.dark) / 0.15) });
    if (t > ev.kamzor) ov.text('WEAKENING?', W / 2, H * 0.70, { size: 60, font: 'Anton', weight: 400, color: AMBER, alpha: ease((t - ev.kamzor) / 0.15) });
  } else if (i === 3) {                                       // Henry Tye and his model: the universe grows, peaks, comes back
    C.position.set(Math.sin(t * 0.05) * 230, 12, Math.cos(t * 0.05) * 230); C.lookAt(0, 0, 0); size = 1.1;
    print(photos.tye, W / 2, H * 0.43, W * 0.5, H * 0.18, 'HENRY TYE', ease(u / 0.3));
    curve(t, ev.model - 0.4, ease((t - ev.model + 0.6) / 0.3));
  } else if (i === 4) {                                       // 33 billion years; today 13.8 -> you are here
    C.position.set(Math.sin(t * 0.05) * 235, 12, Math.cos(t * 0.05) * 235); C.lookAt(0, 0, 0); size = 1.1;
    const y = H * 0.62, x0 = 140, x1 = W - 140, a = ease(u / 0.3);
    bar(t, x0, x1, y, (13.8 / 33) * easeOut((t - ev.t138 + 0.2) / 0.8), a);
    if (t > ev.b33) ov.text('33 BILLION YEARS', W / 2, y - 110, { size: 76, font: 'Anton', weight: 400, alpha: ease((t - ev.b33) / 0.15) });
    if (t > ev.t138) { const xm = x0 + (x1 - x0) * 13.8 / 33, b = ease((t - ev.t138) / 0.2), g = ov.x;
      g.save(); g.globalAlpha = b; g.fillStyle = '#fff'; g.fillRect(xm - 4, y - 50, 8, 100); g.restore();
      ov.text('TODAY: 13.8', xm, y + 130, { size: 52, font: 'Anton', weight: 400, color: AMBER, alpha: b });
      ov.text('YOU ARE HERE', xm, y + 190, { size: 34, font: 'Montserrat', weight: 800, alpha: b }); }
  } else if (i === 5) {                                       // expansion stops, then everything falls back to one point
    const stop = cl((t - st[5]) / Math.max(0.5, ev.rukega - st[5])), back = easeInOut((t - ev.wapas + 0.2) / Math.max(0.6, ev.simat + 0.3 - ev.wapas));
    size = (1.1 + 0.12 * easeOut(stop)) * (1 - back) + 0.004; C.position.set(0, 14, 225 - 90 * back); C.lookAt(0, 0, 0);
    glowAmt = cl((back - 0.5) / 0.4); const fl = t - ev.simat - 0.3;
    core.scale.setScalar(6 + 14 * glowAmt + 40 * (fl > 0 ? Math.exp(-fl * 2.5) : 0)); core.material.opacity = glowAmt;
    ring.scale.setScalar(fl > 0 ? 1 + fl * 45 : 0.001); ring.material.opacity = fl > 0 ? 0.35 * Math.exp(-fl * 2.5) : 0; ring.lookAt(C.position);
    if (t > ev.rukega) ov.text('EXPANSION STOPS', W / 2, H * 0.68, { size: 72, font: 'Anton', weight: 400, alpha: ease((t - ev.rukega) / 0.15) * (1 - ease((t - ev.wapas) / 0.2)) });
    if (t > ev.simat) ov.text('BACK TO ONE POINT', W / 2, H * 0.68, { size: 72, font: 'Anton', weight: 400, color: AMBER, alpha: ease((t - ev.simat) / 0.15) });
  } else if (i === 6) {                                       // an Indian physicist's equations: not the end (the point bounces back)
    const bounce = easeOut((t - ev.nahi) / 1.4); size = 0.004 + 0.5 * bounce;
    C.position.set(0, 10, 160); C.lookAt(0, 0, 0); core.scale.setScalar(8 + 16 * (1 - bounce)); core.material.opacity = 1 - 0.6 * bounce; ring.material.opacity = 0;
    print(photos.ash, W / 2, H * 0.50, W * 0.6, H * 0.25, 'ABHAY ASHTEKAR', ease(u / 0.3));
    if (t > ev.nahi) ov.text('NOT THE END', W / 2, H * 0.62, { size: 84, font: 'Anton', weight: 400, color: AMBER, alpha: ease((t - ev.nahi) / 0.15) });
  } else {                                                    // what next? -> full video
    size = 0.5 + 0.05 * u; C.position.set(0, 10, 200); C.lookAt(0, 0, 0); core.material.opacity = 0.3; ring.material.opacity = 0;
    ov.text('?', W / 2, H * 0.50, { size: 300, font: 'Anton', weight: 400, color: AMBER, alpha: ease((t - ev.kya) / 0.12) * (1 - ease((t - ev.neeche + 0.2) / 0.2)) });
    if (t > ev.neeche) { const a = ease((t - ev.neeche) / 0.25); ov.text('FULL VIDEO', W / 2, H * 0.47, { size: 150, font: 'Anton', weight: 400, alpha: a });
      const b = 18 * Math.sin(u * 5), g = ov.x; g.save(); g.globalAlpha = a; g.fillStyle = g.strokeStyle = AMBER; g.lineWidth = 22; g.lineCap = 'round';
      g.beginPath(); g.moveTo(W / 2, H * 0.55 + b); g.lineTo(W / 2, H * 0.55 + b + 140); g.stroke();
      g.beginPath(); g.moveTo(W / 2, H * 0.55 + b + 175); g.lineTo(W / 2 - 34, H * 0.55 + b + 125); g.lineTo(W / 2 + 34, H * 0.55 + b + 125); g.closePath(); g.fill(); g.restore(); }
  }
  pt.scale.setScalar(core.scale.x * 0.35); pt.material.opacity = core.material.opacity; pt.position.set(0, 0, 0.5);
  gal.material.opacity = i >= 5 ? cl((size - 0.1) / 0.4) : 1; if (i >= 5 && size < 0.1) gal.visible = false;   // additive pile-up of all points at one spot blows the bloom to black
  if (gal.visible) { const gp = gal.geometry.attributes.position; for (let k = 0; k < gp.count; k++) gp.setXYZ(k, galBase[k * 3] * size, galBase[k * 3 + 1] * size, galBase[k * 3 + 2] * size); gp.needsUpdate = true; }

  // solid black title patch (owner rule), plain title, one-word caption, progress bar, cut flash
  const g = ov.x; g.fillStyle = '#000'; g.fillRect(0, 0, W, PATCH);
  ov.text(TITLE[0], W / 2, 125, { size: 86, font: 'Anton', weight: 400 });
  ov.text(TITLE[1], W / 2, 235, { size: 118, font: 'Anton', weight: 400, color: AMBER });
  if (i < 7 || t < ev.neeche) { let cur = null; for (const [wt, ww] of wd) if (wt <= t) cur = ww;
    if (cur) ov.text(cur.toUpperCase().replace(/[,.?]/g, ''), W / 2, H * 0.835, { size: 112, font: 'Anton', weight: 400, color: AMBER }); }
  g.fillStyle = AMBER; g.fillRect(0, H - 12, W * cl(t / total), 12);
  if (i > 0 && u < 0.3) { g.fillStyle = `rgba(255,255,255,${0.3 * Math.pow(1 - u / 0.3, 2)})`; g.fillRect(0, 0, W, H); }
  C.fov = fov; C.updateProjectionMatrix(); comp.render(); ov.draw(R);
}
