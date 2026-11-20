// Shared helpers for web3d scenes: deterministic random, starfield, glow sprites, plain text, easing, bloom composer.
import * as THREE from 'three';
import { EffectComposer, RenderPass, EffectPass, BloomEffect, VignetteEffect, NoiseEffect, BlendFunction } from 'postprocessing';
export const cl = (x, a = 0, b = 1) => Math.min(b, Math.max(a, x));
export const ease = x => { x = cl(x); return x * x * (3 - 2 * x); };
export const easeOut = x => 1 - Math.pow(1 - cl(x), 3);
export const easeInOut = x => { x = cl(x); return x < .5 ? 4 * x * x * x : 1 - Math.pow(-2 * x + 2, 3) / 2; };
export const win = (t, a, b, f = .35) => ease((t - a) / f) * (1 - ease((t - b + f) / f));   // 0..1 visible between a and b
export function rng(seed = 1) { let s = seed >>> 0; return () => ((s = (s * 1664525 + 1013904223) >>> 0) / 4294967296); }
export function stars(n = 6000, r = 400, seed = 7) {
  const R = rng(seed), p = new Float32Array(n * 3), c = new Float32Array(n * 3), col = new THREE.Color();
  for (let i = 0; i < n; i++) {
    const u = R() * 2 - 1, th = R() * Math.PI * 2, rr = r * (0.4 + 0.6 * R()), s = Math.sqrt(1 - u * u);
    p.set([rr * s * Math.cos(th), rr * u, rr * s * Math.sin(th)], i * 3);
    col.setHSL(0.58 + 0.1 * R(), 0.4, 0.55 + 0.45 * R() ** 3); c.set([col.r, col.g, col.b], i * 3);
  }
  const g = new THREE.BufferGeometry(); g.setAttribute('position', new THREE.BufferAttribute(p, 3)); g.setAttribute('color', new THREE.BufferAttribute(c, 3));
  return new THREE.Points(g, new THREE.PointsMaterial({ size: 1.6, sizeAttenuation: false, vertexColors: true, transparent: true, depthWrite: false }));
}
let _glowTex;
export function glowTex() {
  if (_glowTex) return _glowTex;
  const c = document.createElement('canvas'); c.width = c.height = 256; const x = c.getContext('2d');
  const g = x.createRadialGradient(128, 128, 0, 128, 128, 128);
  g.addColorStop(0, 'rgba(255,255,255,1)'); g.addColorStop(0.15, 'rgba(255,255,255,.55)'); g.addColorStop(0.5, 'rgba(255,255,255,.1)'); g.addColorStop(1, 'rgba(255,255,255,0)');
  x.fillStyle = g; x.fillRect(0, 0, 256, 256); return (_glowTex = new THREE.CanvasTexture(c));
}
export function glow(color = 0xffd27a, size = 4) {
  const s = new THREE.Sprite(new THREE.SpriteMaterial({ map: glowTex(), color, transparent: true, blending: THREE.AdditiveBlending, depthWrite: false }));
  s.scale.setScalar(size); return s;
}
// Plain text (owner rule: no animated/glowing text) drawn on a 2D overlay canvas, composited by text layer.
export class Overlay {
  constructor(W, H) { this.W = W; this.H = H; this.c = document.createElement('canvas'); this.c.width = W; this.c.height = H; this.x = this.c.getContext('2d');
    this.tex = new THREE.CanvasTexture(this.c); this.tex.colorSpace = THREE.SRGBColorSpace;
    this.scene = new THREE.Scene(); this.cam = new THREE.OrthographicCamera(-W / 2, W / 2, H / 2, -H / 2, 0, 10);
    this.scene.add(new THREE.Mesh(new THREE.PlaneGeometry(W, H), new THREE.MeshBasicMaterial({ map: this.tex, transparent: true, depthTest: false, toneMapped: false }))); }
  clear() { this.x.clearRect(0, 0, this.W, this.H); }
  text(s, x, y, { size = 72, color = '#ffffff', alpha = 1, weight = 800, align = 'center', font = 'Poppins, "Noto Sans Devanagari", sans-serif', shadow = true } = {}) {
    if (alpha <= 0.001) return; const g = this.x; g.save(); g.globalAlpha = alpha; g.font = `${weight} ${size}px ${font}`; g.textAlign = align; g.textBaseline = 'middle';
    if (shadow) { g.shadowColor = 'rgba(0,0,0,.85)'; g.shadowBlur = size * 0.25; g.shadowOffsetY = size * 0.05; }
    g.fillStyle = color; g.fillText(s, x, y); g.restore(); }
  draw(renderer) { this.tex.needsUpdate = true; renderer.autoClear = false; renderer.clearDepth(); renderer.render(this.scene, this.cam); renderer.autoClear = true; }
}
export function composer(renderer, scene, camera, { bloom = 1.1, threshold = 0.25, vignette = 0.55 } = {}) {
  const c = new EffectComposer(renderer, { frameBufferType: THREE.HalfFloatType });
  c.addPass(new RenderPass(scene, camera));
  c.addPass(new EffectPass(camera, new BloomEffect({ intensity: bloom, luminanceThreshold: threshold, luminanceSmoothing: 0.3, mipmapBlur: true }),
    new VignetteEffect({ darkness: vignette, offset: 0.3 }), new NoiseEffect({ blendFunction: BlendFunction.OVERLAY, premultiply: true })));
  return c;
}
