// Speed test: starfield, glowing planet with atmosphere, orbiting moon, camera push, bloom.
import * as THREE from 'three';
import { stars, glow, composer, ease } from './_lib.js';
let R, S, C, comp, planet, moon, atm;
export async function init({ renderer, W, H }) {
  R = renderer; S = new THREE.Scene(); C = new THREE.PerspectiveCamera(40, W / H, 0.1, 2000);
  S.add(stars()); S.add(new THREE.AmbientLight(0x223355, 0.4));
  const sun = new THREE.DirectionalLight(0xffeedd, 3); sun.position.set(-5, 2, 4); S.add(sun);
  planet = new THREE.Mesh(new THREE.SphereGeometry(2, 96, 64), new THREE.MeshStandardMaterial({ color: 0x3a6fb0, roughness: 0.8 })); S.add(planet);
  atm = glow(0x6fb6ff, 7); S.add(atm);
  moon = new THREE.Mesh(new THREE.SphereGeometry(0.35, 48, 32), new THREE.MeshStandardMaterial({ color: 0xaaaaaa, roughness: 1 })); S.add(moon);
  comp = composer(R, S, C);
}
export function render(t) {
  C.position.set(0, 0.6, 12 - 3 * ease(t / 6)); C.lookAt(0, 0, 0);
  planet.rotation.y = t * 0.2; moon.position.set(4 * Math.cos(t * 0.8), 0.4 * Math.sin(t * 0.8), 4 * Math.sin(t * 0.8));
  comp.render();
}
