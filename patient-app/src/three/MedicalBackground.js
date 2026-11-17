/**
 * Full-screen medical 3D scene:
 *  - Glowing particle field (custom shader, additive, twinkling)
 *  - Rotating DNA double helix (instanced spheres + rungs)
 *  - Floating glossy medical cross with rim glow
 *  - Smooth mouse parallax camera
 */
import React, { useEffect, useMemo, useRef } from 'react';
import { Canvas, useFrame, useThree } from '@react-three/fiber';
import * as THREE from 'three';

const CYAN = new THREE.Color('#22D3EE');
const VIOLET = new THREE.Color('#8B5CF6');
const LAVENDER = new THREE.Color('#A5A1E8');

/* ---------- shared mouse (window-level, works even with pointer-events: none) ---------- */
function useWindowPointer() {
  const p = useRef({ x: 0, y: 0 });
  useEffect(() => {
    const onMove = (e) => {
      const t = e.touches ? e.touches[0] : e;
      p.current.x = (t.clientX / window.innerWidth) * 2 - 1;
      p.current.y = -((t.clientY / window.innerHeight) * 2 - 1);
    };
    window.addEventListener('pointermove', onMove, { passive: true });
    window.addEventListener('touchmove', onMove, { passive: true });
    return () => {
      window.removeEventListener('pointermove', onMove);
      window.removeEventListener('touchmove', onMove);
    };
  }, []);
  return p;
}

/* ---------- particles ---------- */
const particleVert = /* glsl */ `
  attribute float aSize;
  attribute float aSeed;
  attribute vec3 aColor;
  uniform float uTime;
  uniform float uPixelRatio;
  varying vec3 vColor;
  varying float vAlpha;
  void main() {
    vec3 p = position;
    p.y += sin(uTime * 0.25 + aSeed * 6.2831) * 0.25;
    p.x += cos(uTime * 0.18 + aSeed * 4.0) * 0.15;
    vec4 mv = modelViewMatrix * vec4(p, 1.0);
    gl_Position = projectionMatrix * mv;
    float twinkle = 0.55 + 0.45 * sin(uTime * (0.8 + aSeed) + aSeed * 20.0);
    gl_PointSize = aSize * uPixelRatio * (30.0 / -mv.z);
    vColor = aColor;
    vAlpha = twinkle;
  }
`;
const particleFrag = /* glsl */ `
  varying vec3 vColor;
  varying float vAlpha;
  void main() {
    float d = length(gl_PointCoord - 0.5);
    float a = smoothstep(0.5, 0.0, d);
    a *= a;
    gl_FragColor = vec4(vColor, a * vAlpha);
  }
`;

function Particles({ count }) {
  const ref = useRef();
  const { positions, colors, sizes, seeds } = useMemo(() => {
    const positions = new Float32Array(count * 3);
    const colors = new Float32Array(count * 3);
    const sizes = new Float32Array(count);
    const seeds = new Float32Array(count);
    const c = new THREE.Color();
    for (let i = 0; i < count; i++) {
      positions[i * 3] = (Math.random() - 0.5) * 30;
      positions[i * 3 + 1] = (Math.random() - 0.5) * 18;
      positions[i * 3 + 2] = -Math.random() * 16 + 2;
      c.copy(CYAN).lerp(VIOLET, Math.random());
      if (Math.random() < 0.12) c.set('#ffffff');
      colors.set([c.r, c.g, c.b], i * 3);
      sizes[i] = 1.5 + Math.random() * 4.5;
      seeds[i] = Math.random();
    }
    return { positions, colors, sizes, seeds };
  }, [count]);

  const material = useMemo(() => new THREE.ShaderMaterial({
    uniforms: { uTime: { value: 0 }, uPixelRatio: { value: Math.min(window.devicePixelRatio || 1, 2) } },
    vertexShader: particleVert,
    fragmentShader: particleFrag,
    transparent: true,
    depthWrite: false,
    blending: THREE.AdditiveBlending,
  }), []);

  useEffect(() => () => material.dispose(), [material]);

  useFrame((state, dt) => {
    material.uniforms.uTime.value = state.clock.elapsedTime;
    if (ref.current) ref.current.rotation.y += dt * 0.012;
  });

  return (
    <points ref={ref} material={material}>
      <bufferGeometry>
        <bufferAttribute attach="attributes-position" count={count} array={positions} itemSize={3} />
        <bufferAttribute attach="attributes-aColor" count={count} array={colors} itemSize={3} />
        <bufferAttribute attach="attributes-aSize" count={count} array={sizes} itemSize={1} />
        <bufferAttribute attach="attributes-aSeed" count={count} array={seeds} itemSize={1} />
      </bufferGeometry>
    </points>
  );
}

/* ---------- DNA helix ---------- */
function DNAHelix({ position, scale = 1, tilt = 0.35 }) {
  const group = useRef();
  const spheres = useRef();
  const rungs = useRef();
  const PAIRS = 26;
  const R = 0.9;

  useEffect(() => {
    const m = new THREE.Matrix4();
    const q = new THREE.Quaternion();
    const up = new THREE.Vector3(0, 1, 0);
    const a = new THREE.Vector3(), b = new THREE.Vector3(), mid = new THREE.Vector3(), dir = new THREE.Vector3();
    const col = new THREE.Color();
    for (let i = 0; i < PAIRS; i++) {
      const t = i * 0.5;
      const y = (i - PAIRS / 2) * 0.3;
      a.set(Math.cos(t) * R, y, Math.sin(t) * R);
      b.set(Math.cos(t + Math.PI) * R, y, Math.sin(t + Math.PI) * R);
      m.makeTranslation(a.x, a.y, a.z); spheres.current.setMatrixAt(i * 2, m);
      m.makeTranslation(b.x, b.y, b.z); spheres.current.setMatrixAt(i * 2 + 1, m);
      spheres.current.setColorAt(i * 2, col.copy(CYAN));
      spheres.current.setColorAt(i * 2 + 1, col.copy(VIOLET));
      mid.addVectors(a, b).multiplyScalar(0.5);
      dir.subVectors(b, a);
      const len = dir.length();
      q.setFromUnitVectors(up, dir.normalize());
      m.compose(mid, q, new THREE.Vector3(1, len, 1));
      rungs.current.setMatrixAt(i, m);
      rungs.current.setColorAt(i, col.copy(CYAN).lerp(VIOLET, (i % 4) / 4));
    }
    spheres.current.instanceMatrix.needsUpdate = true;
    rungs.current.instanceMatrix.needsUpdate = true;
    if (spheres.current.instanceColor) spheres.current.instanceColor.needsUpdate = true;
    if (rungs.current.instanceColor) rungs.current.instanceColor.needsUpdate = true;
  }, []);

  const spin = useRef();
  useFrame((state, dt) => {
    if (!group.current || !spin.current) return;
    spin.current.rotation.y += dt * 0.35;   // spin around the helix's own axis
    group.current.position.y = position[1] + Math.sin(state.clock.elapsedTime * 0.5) * 0.15;
  });

  return (
    <group ref={group} position={position} rotation={[0, 0, tilt]} scale={scale}>
     <group ref={spin}>
      <instancedMesh ref={spheres} args={[null, null, PAIRS * 2]}>
        <sphereGeometry args={[0.12, 20, 20]} />
        <meshStandardMaterial roughness={0.25} metalness={0.2} emissive="#3B2F8F" emissiveIntensity={0.6} toneMapped={false} />
      </instancedMesh>
      <instancedMesh ref={rungs} args={[null, null, PAIRS]}>
        <cylinderGeometry args={[0.025, 0.025, 1, 8]} />
        <meshStandardMaterial transparent opacity={0.55} emissive="#22D3EE" emissiveIntensity={0.35} toneMapped={false} />
      </instancedMesh>
     </group>
    </group>
  );
}

/* ---------- medical cross ---------- */
const rimVert = /* glsl */ `
  varying vec3 vN; varying vec3 vV;
  void main() {
    vec4 mv = modelViewMatrix * vec4(position, 1.0);
    vN = normalize(normalMatrix * normal);
    vV = normalize(-mv.xyz);
    gl_Position = projectionMatrix * mv;
  }
`;
const rimFrag = /* glsl */ `
  uniform vec3 uColor; varying vec3 vN; varying vec3 vV;
  void main() {
    float f = pow(1.0 - abs(dot(vN, vV)), 2.2);
    gl_FragColor = vec4(uColor, f * 0.9);
  }
`;

function MedicalCross({ position, scale = 1 }) {
  const group = useRef();
  const geometry = useMemo(() => {
    const s = 0.42, l = 1.15;
    const sh = new THREE.Shape();
    sh.moveTo(-s, l); sh.lineTo(s, l); sh.lineTo(s, s); sh.lineTo(l, s); sh.lineTo(l, -s);
    sh.lineTo(s, -s); sh.lineTo(s, -l); sh.lineTo(-s, -l); sh.lineTo(-s, -s); sh.lineTo(-l, -s);
    sh.lineTo(-l, s); sh.lineTo(-s, s); sh.closePath();
    const g = new THREE.ExtrudeGeometry(sh, { depth: 0.45, bevelEnabled: true, bevelThickness: 0.14, bevelSize: 0.12, bevelSegments: 6 });
    g.center();
    return g;
  }, []);
  const rimMat = useMemo(() => new THREE.ShaderMaterial({
    uniforms: { uColor: { value: new THREE.Color('#67E8F9') } },
    vertexShader: rimVert, fragmentShader: rimFrag,
    transparent: true, depthWrite: false, blending: THREE.AdditiveBlending,
  }), []);
  useEffect(() => () => { geometry.dispose(); rimMat.dispose(); }, [geometry, rimMat]);

  useFrame((state) => {
    const t = state.clock.elapsedTime;
    if (!group.current) return;
    group.current.rotation.y = Math.sin(t * 0.4) * 0.6 + t * 0.15;
    group.current.rotation.x = Math.sin(t * 0.3) * 0.2;
    group.current.position.y = position[1] + Math.sin(t * 0.8) * 0.2;
  });

  return (
    <group ref={group} position={position} scale={scale}>
      <mesh geometry={geometry}>
        <meshPhysicalMaterial color="#F4F3FF" roughness={0.12} metalness={0.05} clearcoat={1} clearcoatRoughness={0.08}
          emissive="#7C6CF0" emissiveIntensity={0.18} />
      </mesh>
      <mesh geometry={geometry} material={rimMat} scale={1.04} />
    </group>
  );
}

/* ---------- camera rig + responsive layout ---------- */
function Rig({ pointer }) {
  const { camera } = useThree();
  useFrame(() => {
    camera.position.x += (pointer.current.x * 0.9 - camera.position.x) * 0.035;
    camera.position.y += (pointer.current.y * 0.6 - camera.position.y) * 0.035;
    camera.lookAt(0, 0, -2);
  });
  return null;
}

const CAM_Z = 7;
/**
 * Place objects in the empty margins, never behind the main content:
 *  - Phone (portrait): helix lies across the bottom edge, cross floats top-right
 *  - Desktop: helix stands at the right edge, cross floats bottom-left
 * fx/fy are screen fractions (-1..1); z pushes the object back (smaller, dimmer).
 */
function Layout({ showHelix, showCross }) {
  const { viewport } = useThree();
  const narrow = viewport.aspect < 1;
  const at = (fx, fy, z) => {
    const k = (CAM_Z - z) / CAM_Z; // visible size grows with depth
    return [fx * (viewport.width * k) / 2, fy * (viewport.height * k) / 2, z];
  };
  return (
    <>
      {showHelix && (narrow
        ? <DNAHelix position={at(0, -0.86, -3)} scale={0.8} tilt={Math.PI / 2 - 0.25} />
        : <DNAHelix position={at(0.9, 0.02, -3)} scale={1.05} tilt={0.22} />)}
      {showCross && (narrow
        ? <MedicalCross position={at(0.62, 0.8, -2)} scale={0.42} />
        : <MedicalCross position={at(-0.86, -0.72, -2.5)} scale={0.62} />)}
    </>
  );
}

export default function MedicalBackground({ frameloop = 'always', density = 1, showHelix = true, showCross = true }) {
  const pointer = useWindowPointer();
  const count = Math.round((window.innerWidth < 700 ? 700 : 1500) * density);
  return (
    <Canvas
      frameloop={frameloop}
      dpr={[1, 1.75]}
      camera={{ position: [0, 0, 7], fov: 50 }}
      gl={{ antialias: true, alpha: true, powerPreference: 'high-performance' }}
      style={{ position: 'absolute', inset: 0, pointerEvents: 'none' }}
    >
      <ambientLight intensity={0.5} />
      <pointLight position={[4, 4, 5]} intensity={40} color="#A5F3FC" />
      <pointLight position={[-5, -3, 3]} intensity={30} color="#C4B5FD" />
      <directionalLight position={[0, 5, 5]} intensity={1.2} color={LAVENDER} />
      <Particles count={count} />
      <Layout showHelix={showHelix} showCross={showCross} />
      <Rig pointer={pointer} />
    </Canvas>
  );
}
