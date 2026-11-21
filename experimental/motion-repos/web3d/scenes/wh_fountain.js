// White hole as a 3D particle fountain (fast-cut 10): light and matter only stream OUT of a glowing core; slow push in.
import * as THREE from 'three';
import { stars, glow, glowTex, composer, ease, rng } from './_lib.js';
let R, S, C, comp, pts, base, core;
const N = 6000;
export async function init({ renderer, W, H }) {
  R = renderer; S = new THREE.Scene(); C = new THREE.PerspectiveCamera(45, W / H, 0.1, 3000);
  const sf = stars(8000, 900); sf.material.size = 2.0; S.add(sf);
  const r = rng(7), p = new Float32Array(N * 3), c = new Float32Array(N * 3), col = new THREE.Color();
  base = [];
  for (let i = 0; i < N; i++) {
    const u = r() * 2 - 1, th = r() * 6.283, s = Math.sqrt(1 - u * u);
    base.push([s * Math.cos(th), u, s * Math.sin(th), 6 + 18 * r(), r()]);
    col.setHSL(0.09 + 0.06 * r(), 0.55, 0.75 + 0.2 * r()); c.set([col.r, col.g, col.b], i * 3);
  }
  const g = new THREE.BufferGeometry(); g.setAttribute('position', new THREE.BufferAttribute(p, 3)); g.setAttribute('color', new THREE.BufferAttribute(c, 3));
  pts = new THREE.Points(g, new THREE.PointsMaterial({ size: 1.1, map: glowTex(), vertexColors: true, transparent: true, blending: THREE.AdditiveBlending, depthWrite: false }));
  S.add(pts);
  core = glow(0xffffff, 7); S.add(core); const halo = glow(0xffd9a0, 22); halo.material.opacity = 0.5; S.add(halo);
  comp = composer(R, S, C, { bloom: 2.0, threshold: 0.15, vignette: 0.45 });
}
export function render(t) {
  C.position.set(0, 4, 70 - 14 * ease(t / 3)); C.lookAt(0, 0, 0);
  const a = pts.geometry.attributes.position;
  for (let i = 0; i < N; i++) {
    const [x, y, z, sp, ph] = base[i], life = (t * 0.55 + ph) % 1.0, d = 1.5 + sp * life * 2.2;
    a.setXYZ(i, x * d, y * d, z * d);
  }
  a.needsUpdate = true; core.scale.setScalar(7 + Math.sin(t * 5) * 0.6);
  comp.render();
}
