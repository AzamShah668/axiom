// 09 Short 3 "blunder" (owner's script): a ball that speeds up going up -> gravity normally slows it -> scientists expected
// expansion to slow -> supernova light measured -> expansion is speeding up -> Einstein's dropped term (Λ) is back -> how?
// Real physics for the balls (rapier), galaxies whose spacing follows a(t), plain text only (owner rule), photo always whole.
// params: { words: [[t, word], ...] } at the final voice speed; shot starts are word indices of each sentence.
import * as THREE from 'three';
import RAPIER from 'rapier';
import { cl, ease, easeOut, easeInOut, rng, stars, glow, Overlay, composer } from './_lib.js';

const AMBER = '#f5c242', AMBER_HEX = 0xf5c242, BLUE_HEX = 0x7fb8ff;
const SHOT_WORDS = [0, 15, 24, 35, 45, 54, 73, 84];
let R, W, H, S, C, comp, ov, wd, st, ev, total;
let ground, ball, ballGlow, trail, galaxies, galBase, sn, snRing, pulse, rays, rayBase, photo;
let simA, simB;

const w = i => wd[i][0];
function shotAt(t) { let i = 0; for (let k = 0; k < st.length; k++) if (t >= st[k]) i = k; return i; }

function simulate(steps, setup, onStep) {           // fixed-step rapier sim, returns [y, vy] per 1/120 s
  const world = new RAPIER.World({ x: 0, y: -9.81, z: 0 }); world.timestep = 1 / 120;
  world.createCollider(RAPIER.ColliderDesc.cuboid(50, 0.5, 50).setTranslation(0, -0.5, 0).setRestitution(0.6));
  const body = world.createRigidBody(RAPIER.RigidBodyDesc.dynamic().setTranslation(0, 0.5, 0).setCcdEnabled(true));
  world.createCollider(RAPIER.ColliderDesc.ball(0.5).setRestitution(0.6).setDensity(1), body);
  setup && setup(body);
  const out = [];
  for (let k = 0; k < steps; k++) { onStep(body, k / 120); world.step(); const p = body.translation(), v = body.linvel(); out.push([p.y, v.y]); }
  return out;
}
const sample = (sim, u) => { const k = cl(Math.floor(u * 120), 0, sim.length - 1); return sim[k]; };

function spiralTexture(seed, hue) {
  const c = document.createElement('canvas'); c.width = c.height = 256; const x = c.getContext('2d'), r = rng(seed);
  const g = x.createRadialGradient(128, 128, 0, 128, 128, 40); g.addColorStop(0, 'rgba(255,240,215,1)'); g.addColorStop(1, 'rgba(255,220,180,0)');
  x.fillStyle = g; x.fillRect(0, 0, 256, 256);
  for (let i = 0; i < 1400; i++) {
    const arm = i % 2, d = Math.pow(r(), 0.7), th = arm * Math.PI + d * 7 + (r() - 0.5) * 0.7, rad = 12 + d * 108;
    x.fillStyle = `hsla(${hue + r() * 40},70%,${55 + r() * 35}%,${0.25 + 0.5 * (1 - d)})`;
    x.beginPath(); x.arc(128 + rad * Math.cos(th), 128 + rad * Math.sin(th) * 0.55, 0.6 + r() * 1.6, 0, 7); x.fill();
  }
  const t = new THREE.CanvasTexture(c); t.colorSpace = THREE.SRGBColorSpace; return t;
}

export async function init(ctx) {
  ({ renderer: R, W, H } = ctx);
  wd = ctx.params.words; st = SHOT_WORDS.map(i => w(i)); total = ctx.dur;
  ev = { maari: w(5), jaate: w(9), fast: w(12), gravity: w(16), slow: w(21), sci: w(24), slow2: w(33), exploding: w(39), light: w(42),
         measure: w(43), fast2: w(49), expand: w(50), einstein: w(54), hata: w(61), accel: w(66), chala: w(83), neeche: w(84) };
  await RAPIER.init();
  // shot A: kicked at "maari", speeds up from "jaate" (an extra upward push, the "impossible" ball)
  simA = simulate(Math.ceil((st[1] + 0.5) * 120), null, (b, t) => {
    if (Math.abs(t - ev.maari) < 0.5 / 120) b.applyImpulse({ x: 0, y: 16 * b.mass(), z: 0 }, true);
    if (t > ev.jaate) b.addForce({ x: 0, y: 0, z: 0 }, false), b.resetForces(true), b.addForce({ x: 0, y: (9.81 + 12) * b.mass(), z: 0 }, true);
  });
  // shot B: a normal throw, slowed by gravity, falls back and bounces
  const tB = st[1] + 0.3;
  simB = simulate(Math.ceil((st[2] - st[1] + 0.5) * 120), null, (b, t) => {
    if (Math.abs(t - (tB - st[1])) < 0.5 / 120) b.applyImpulse({ x: 0, y: 10.5 * b.mass(), z: 0 }, true);
  });

  S = new THREE.Scene(); S.fog = new THREE.FogExp2(0x02040a, 0.012);
  C = new THREE.PerspectiveCamera(50, W / H, 0.1, 3000);
  const sf = stars(9000, 900); sf.material.size = 2.2; S.add(sf);
  S.add(new THREE.AmbientLight(0x334466, 0.6));
  const key = new THREE.DirectionalLight(0xfff0dd, 2.2); key.position.set(-4, 6, 5); S.add(key);

  ground = new THREE.Group();
  const grid = new THREE.GridHelper(200, 100, 0x5b93e6, 0x28497c); grid.material.transparent = true; grid.material.opacity = 0.8; ground.add(grid);
  const horizon = glow(0x3d6fb5, 1); horizon.scale.set(260, 16, 1); horizon.position.set(0, 0, -90); horizon.material.opacity = 0.35; ground.add(horizon);
  S.add(ground);
  ball = new THREE.Mesh(new THREE.SphereGeometry(0.5, 64, 48), new THREE.MeshStandardMaterial({ color: AMBER_HEX, emissive: 0x8a5a10, roughness: 0.35, metalness: 0.1 }));
  ballGlow = glow(AMBER_HEX, 3.2); ball.add(ballGlow); S.add(ball);
  trail = new THREE.Mesh(new THREE.CylinderGeometry(0.34, 0.0, 1, 24, 1, true), new THREE.MeshBasicMaterial({ color: AMBER_HEX, transparent: true, opacity: 0.22, blending: THREE.AdditiveBlending, depthWrite: false }));
  S.add(trail);

  galaxies = new THREE.Group(); galBase = [];
  const r = rng(11), texs = [0, 1, 2, 3].map(k => spiralTexture(20 + k, [30, 200, 220, 15][k]));
  for (let i = 0; i < 240; i++) {
    const u = r() * 2 - 1, th = r() * 6.283, rr = 14 + 70 * Math.cbrt(r()), s = Math.sqrt(1 - u * u);
    const sp = new THREE.Sprite(new THREE.SpriteMaterial({ map: texs[i % 4], transparent: true, blending: THREE.AdditiveBlending, depthWrite: false, rotation: r() * 6.283 }));
    sp.scale.setScalar(5 + 8 * r()); galaxies.add(sp); galBase.push(new THREE.Vector3(rr * s * Math.cos(th), rr * u * 0.8, rr * s * Math.sin(th)));
  }
  S.add(galaxies);

  sn = new THREE.Group();
  const host = new THREE.Sprite(new THREE.SpriteMaterial({ map: spiralTexture(5, 25), transparent: true, blending: THREE.AdditiveBlending, depthWrite: false }));
  host.scale.setScalar(16); sn.add(host);
  const flash = glow(0xdff0ff, 1); flash.position.set(3.2, 1.2, 0.1); flash.name = 'flash'; sn.add(flash);
  snRing = new THREE.Mesh(new THREE.RingGeometry(0.9, 1, 96), new THREE.MeshBasicMaterial({ color: 0x9fd0ff, transparent: true, blending: THREE.AdditiveBlending, depthWrite: false, side: THREE.DoubleSide }));
  snRing.position.copy(flash.position); sn.add(snRing);
  sn.position.set(0, 0, -40); S.add(sn);
  pulse = glow(0xdff0ff, 1.6); S.add(pulse);

  rays = new THREE.Group(); rayBase = [];
  const rr2 = rng(3);
  for (let i = 0; i < 90; i++) {
    const u = rr2() * 2 - 1, th = rr2() * 6.283, s = Math.sqrt(1 - u * u), d = new THREE.Vector3(s * Math.cos(th), u, s * Math.sin(th));
    const m = new THREE.Mesh(new THREE.CylinderGeometry(0.03, 0.03, 1, 6), new THREE.MeshBasicMaterial({ color: i % 3 ? 0xcfe6ff : AMBER_HEX, transparent: true, blending: THREE.AdditiveBlending, depthWrite: false }));
    rays.add(m); rayBase.push([d, 25 + 30 * rr2(), rr2()]);
  }
  const core = glow(0xffffff, 3); core.name = 'core'; rays.add(core); S.add(rays);

  photo = await new Promise(ok => { const im = new Image(); im.onload = () => ok(im); im.onerror = () => ok(null); im.src = '/assets/assets/photos/Einstein.jpg'; });
  ov = new Overlay(W, H);
  comp = composer(R, S, C, { bloom: 1.25, threshold: 0.3, vignette: 0.5 });
  const np = comp.passes[1]; np.effects && np.effects.forEach(e => e.blendMode && e.constructor.name === 'NoiseEffect' && (e.blendMode.opacity.value = 0.12));
}

function setVis(i) {
  ground.visible = i <= 1; ball.visible = i <= 1; trail.visible = i <= 1;
  galaxies.visible = i === 2 || i === 4 || i === 5 || i === 7; sn.visible = i === 3; pulse.visible = i === 3; rays.visible = i === 6;
}

function arrow(x, y, len, color, up = true, lw = 14) {     // a 2D arrow on the overlay (graphic, not text)
  if (Math.abs(len) < 4) return; const g = ov.x, d = up ? -1 : 1; g.save(); g.strokeStyle = g.fillStyle = color; g.lineWidth = lw; g.lineCap = 'round';
  g.beginPath(); g.moveTo(x, y); g.lineTo(x, y + d * (len - 26)); g.stroke();
  g.beginPath(); g.moveTo(x, y + d * len); g.lineTo(x - 26, y + d * (len - 34)); g.lineTo(x + 26, y + d * (len - 34)); g.closePath(); g.fill(); g.restore();
}

function graph(t, i) {
  if (i !== 2 && i !== 4) return; const showMeasured = i === 4;                          // expansion speed vs time: expected (slowing) and measured (speeding up)
  const x0 = 150, x1 = W - 150, y0 = H * 0.70, y1 = H * 0.54, g = ov.x, a = i === 2 ? ease((t - st[2] - 0.6) / 0.4) : 1;
  if (a <= 0) return;
  g.save(); g.globalAlpha = a; g.fillStyle = 'rgba(4,8,18,.72)'; g.fillRect(x0 - 40, y1 - 90, x1 - x0 + 80, y0 - y1 + 150);
  g.strokeStyle = 'rgba(255,255,255,.6)'; g.lineWidth = 3; g.beginPath(); g.moveTo(x0, y1 - 20); g.lineTo(x0, y0); g.lineTo(x1, y0); g.stroke();
  ov.text('EXPANSION SPEED', x0, y1 - 55, { size: 40, align: 'left', font: 'Montserrat', weight: 700, color: 'rgba(255,255,255,.85)', shadow: false });
  ov.text('TIME →', x1, y0 + 40, { size: 34, align: 'right', font: 'Montserrat', weight: 700, color: 'rgba(255,255,255,.6)', shadow: false });
  const draw = (f, p, color, dash) => { g.setLineDash(dash); g.strokeStyle = color; g.lineWidth = 9; g.beginPath();
    for (let k = 0; k <= 100 * p; k++) { const u = k / 100, X = x0 + (x1 - x0) * u, Y = y0 - (y0 - y1) * f(u); k ? g.lineTo(X, Y) : g.moveTo(X, Y); } g.stroke(); g.setLineDash([]); };
  const pe = easeInOut((t - st[2] - 0.9) / 2.2);
  draw(u => 0.9 - 0.55 * Math.pow(u, 0.8), pe, 'rgba(255,255,255,.85)', [22, 16]);
  if (pe > 0.95) ov.text('EXPECTED', x1 - 10, y0 - (y0 - y1) * 0.35 - 40, { size: 40, align: 'right', font: 'Montserrat', weight: 800, shadow: false });
  if (showMeasured) {
    const pm = easeInOut((t - ev.fast2 + 0.6) / 1.6);
    draw(u => 0.9 - 0.55 * Math.pow(u, 0.8) * (1 - u) + 0.0 + 0.62 * Math.pow(u, 2.4), pm, AMBER, []);
    if (pm > 0.95) ov.text('MEASURED', x1 - 10, y1 - 30, { size: 44, align: 'right', font: 'Montserrat', weight: 800, color: AMBER, shadow: false });
  }
  g.restore();
}

export function render(t) {
  const i = shotAt(t), u = t - st[i];
  setVis(i); ov.clear();
  let fovPunch = 0;
  if (i > 0 && u < 0.35) fovPunch = 9 * Math.pow(1 - u / 0.35, 2);

  if (i === 0 || i === 1) {
    const sim = i === 0 ? simA : simB, [y, vy] = sample(sim, i === 0 ? t : u);
    ball.position.set(0, y, 0); ball.rotation.x = -y * 0.6;
    const sp = Math.abs(vy); trail.visible = sp > 3; trail.scale.set(1, Math.min(7, sp * 0.28), 1);
    trail.position.set(0, y - Math.sign(vy) * (0.5 + trail.scale.y / 2), 0); trail.rotation.z = vy > 0 ? 0 : Math.PI;
    const camY = i === 0 ? Math.max(1.6, y * 0.92 + 0.8) : 3.2, camZ = i === 0 ? 9 + 0.04 * y : 14.5;
    C.position.set(i === 0 ? 1.2 : -1.0, camY, camZ); C.lookAt(0, i === 0 ? Math.max(1.2, y) : 3.8, 0);
    ballGlow.material.opacity = 0.55 + 0.45 * cl(sp / 20);
    // velocity arrow next to the ball (projected), and gravity arrow in shot B
    C.updateMatrixWorld(); const p = ball.position.clone().project(C), bx = cl((p.x * 0.5 + 0.5) * W, 260, W - 260), by = cl((-p.y * 0.5 + 0.5) * H, 560, H * 0.72);
    if (t > ev.maari + 0.05) { arrow(bx + 150, by, Math.min(520, sp * 22), AMBER, vy >= 0); ov.text('SPEED', bx + 150, by + (vy >= 0 ? 60 : -60), { size: 44, font: 'Montserrat', weight: 800, color: AMBER, alpha: cl(sp / 3) }); }
    if (i === 1 && t > ev.gravity) { const a = ease((t - ev.gravity) / 0.25); ov.x.globalAlpha = a; arrow(bx - 150, by - 40, 230, '#9fd0ff', false); ov.x.globalAlpha = 1;
      ov.text('GRAVITY', bx - 150, by - 90, { size: 44, font: 'Montserrat', weight: 800, color: '#9fd0ff', alpha: a }); }
    if (i === 0) { const a = ease((t - ev.maari) / 0.08) * (1 - ease((t - ev.maari - 0.1) / 0.4)); ballGlow.scale.setScalar(3.2 + 2.2 * a); }
  } else if (i === 2 || i === 4 || i === 5 || i === 7) {
    let a = 1, rot = 0.05 * t, dist = 105;
    if (i === 2) { const q = cl(u / (st[3] - st[2])); a = 1 + 0.35 * easeOut(q * 1.3); dist = 95 - 15 * q; }
    if (i === 4) { const q = cl(u / (st[5] - st[4])); a = 1.0 + 0.1 * q + 1.25 * Math.pow(q, 2.6); dist = 80 + 30 * easeInOut(q); }
    if (i === 5) { a = 1.6 + 0.04 * u; dist = 150; }
    if (i === 7) { a = 1.8 + 0.05 * u; dist = 160; }
    galaxies.children.forEach((g, k) => { g.position.copy(galBase[k]).multiplyScalar(a); g.material.opacity = i === 5 || i === 7 ? 0.45 : 1; });
    C.position.set(Math.sin(rot) * dist, 10 + (i === 4 ? 6 * Math.sin(u) : 0), Math.cos(rot) * dist); C.lookAt(0, 0, 0);
    if (i === 4 && Math.abs(t - ev.fast2) < 0.5) fovPunch += 6 * Math.pow(1 - Math.abs(t - ev.fast2) / 0.5, 2);
  } else if (i === 3) {
    const q = cl(u / (st[4] - st[3])); C.position.set(0, 1.5, 30 - 8 * easeInOut(q)); C.lookAt(0, 0.5, -40);
    const fl = sn.getObjectByName('flash'), e = t - ev.exploding, peak = e > 0 ? Math.exp(-e * 1.6) * ease(e / 0.06) : 0;
    fl.scale.setScalar(1 + 26 * peak); fl.material.opacity = cl(0.25 + peak);
    snRing.scale.setScalar(e > 0 ? 1 + e * 9 : 0.001); snRing.material.opacity = e > 0 ? 0.8 * Math.exp(-e * 1.4) : 0;
    const lp = easeInOut((t - ev.light) / 0.55), from = sn.position.clone().add(fl.position), to = C.position.clone().add(new THREE.Vector3(0, -1.4, -4));
    pulse.position.lerpVectors(from, to, lp); pulse.material.opacity = t > ev.light && lp < 1 ? 1 : 0; pulse.scale.setScalar(1.4 + 3 * lp);
    if (t > ev.measure) {                                    // brightness meter: dimmer than expected -> farther away
      const a = ease((t - ev.measure) / 0.3), m = easeOut((t - ev.measure - 0.1) / 0.8), x0 = 190, x1 = W - 190, y = H * 0.66, g = ov.x;
      g.save(); g.globalAlpha = a; g.fillStyle = 'rgba(4,8,18,.72)'; g.fillRect(x0 - 40, y - 110, x1 - x0 + 80, 220);
      g.fillStyle = 'rgba(255,255,255,.15)'; g.fillRect(x0, y - 18, x1 - x0, 36); g.fillStyle = AMBER; g.fillRect(x0, y - 18, (x1 - x0) * 0.42 * m, 36);
      const xe = x0 + (x1 - x0) * 0.72; g.fillStyle = '#fff'; g.fillRect(xe - 4, y - 40, 8, 80); g.restore();
      ov.text('BRIGHTNESS', x0, y - 70, { size: 40, align: 'left', font: 'Montserrat', weight: 800, alpha: a, shadow: false });
      ov.text('EXPECTED', xe, y + 72, { size: 36, font: 'Montserrat', weight: 700, alpha: a, shadow: false });
      ov.text('DIMMER', x0 + (x1 - x0) * 0.42 * m, y + 72, { size: 36, font: 'Montserrat', weight: 800, color: AMBER, alpha: a * cl(m * 3 - 2), shadow: false });
    }
  } else if (i === 6) {
    const q = cl(u / (st[7] - st[6])); C.position.set(0, 0, 34 - 6 * q); C.lookAt(0, 0, 0);
    rays.children.forEach((m, k) => { if (!rayBase[k]) return; const [d, r0, ph] = rayBase[k];
      const rr = ((r0 * (1 - ((u * 0.55 + ph) % 1))) + 0.5); m.position.copy(d).multiplyScalar(rr + 1.5); m.scale.set(1, 3, 1);
      m.quaternion.setFromUnitVectors(new THREE.Vector3(0, 1, 0), d); m.material.opacity = cl(rr / 6) * 0.9; });
    rays.getObjectByName('core').scale.setScalar(3 + 0.6 * Math.sin(u * 6));
    ov.text('?', W / 2, H * 0.50, { size: 300, font: 'Anton', weight: 400, color: AMBER, alpha: ease((t - ev.chala) / 0.12) });
  }

  // Einstein: the whole photo as a framed print, upper half; the dropped term Λ below it (never under text)
  if (i === 5 && photo) {
    const a = ease(u / 0.3), maxW = W * 0.62, maxH = H * 0.34, k = Math.min(maxW / photo.width, maxH / photo.height) * (1 + 0.03 * u / 5);
    const pw = photo.width * k, ph = photo.height * k, px = W / 2 - pw / 2, py = H * 0.47 - ph, g = ov.x;
    g.save(); g.globalAlpha = a; g.shadowColor = 'rgba(0,0,0,.8)'; g.shadowBlur = 40; g.fillStyle = '#f2efe8'; g.fillRect(px - 16, py - 16, pw + 32, ph + 64);
    g.shadowBlur = 0; g.drawImage(photo, px, py, pw, ph); g.restore();
    ov.text('ALBERT EINSTEIN', W / 2, py + ph + 25, { size: 30, font: 'Montserrat', weight: 800, color: '#222', alpha: a, shadow: false });
    const back = t > ev.accel, off = t > ev.hata && !back, la = ease((t - ev.einstein - 0.5) / 0.2);
    const col = back ? AMBER : off ? 'rgba(255,255,255,.35)' : '#ffffff';
    ov.text('Λ', W / 2, H * 0.60, { size: 210, font: 'Montserrat', weight: 800, color: col, alpha: la });
    ov.text(back ? 'BACK IN THE MODEL' : 'COSMOLOGICAL CONSTANT', W / 2, H * 0.695, { size: 44, font: 'Montserrat', weight: 800, color: back ? AMBER : '#fff', alpha: la });
    if (off) { const s = easeOut((t - ev.hata) / 0.25), g2 = ov.x; g2.save(); g2.strokeStyle = '#ff5a4a'; g2.lineWidth = 16; g2.lineCap = 'round';
      g2.beginPath(); g2.moveTo(W / 2 - 120, H * 0.60 + 70); g2.lineTo(W / 2 - 120 + 240 * s, H * 0.60 - 70 * (2 * s - 1)); g2.stroke(); g2.restore(); }
  }
  graph(t, i);

  if (i === 7) {                                             // end card
    const a = ease(u / 0.3); ov.text('FULL VIDEO', W / 2, H * 0.47, { size: 150, font: 'Anton', weight: 400, alpha: a });
    const b = 18 * Math.sin(u * 5); ov.x.globalAlpha = a; arrow(W / 2, H * 0.55 + b, 170, AMBER, false, 22); ov.x.globalAlpha = 1;
  }

  // title band (plain), word caption (plain), progress bar
  const g = ov.x, grd = g.createLinearGradient(0, 0, 0, 420); grd.addColorStop(0, 'rgba(0,0,0,.75)'); grd.addColorStop(1, 'rgba(0,0,0,0)');
  g.fillStyle = grd; g.fillRect(0, 0, W, 420);
  ov.text('WHY IS THE UNIVERSE', W / 2, 118, { size: 86, font: 'Anton', weight: 400 });
  ov.text('SPEEDING UP?', W / 2, 222, { size: 112, font: 'Anton', weight: 400, color: AMBER });
  if (i < 7) { let cur = null; for (const [wt, ww] of wd) if (wt <= t) cur = ww;
    if (cur) ov.text(cur.toUpperCase().replace(/[,.?]/g, ''), W / 2, H * 0.835, { size: 112, font: 'Anton', weight: 400, color: AMBER }); }
  g.fillStyle = AMBER; g.fillRect(0, H - 12, W * cl(t / total), 12);
  if (i > 0 && u < 0.3) { g.fillStyle = `rgba(255,255,255,${0.35 * Math.pow(1 - u / 0.3, 2)})`; g.fillRect(0, 0, W, H); }

  C.fov = 50 + fovPunch; C.updateProjectionMatrix();
  comp.render(); ov.draw(R);
}
