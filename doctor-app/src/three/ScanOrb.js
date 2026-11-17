/**
 * AI scan orb:
 *  - Fresnel-glow energy core + wireframe icosahedron shell
 *  - 3 HUD scanning rings (partial arcs) spinning on different axes
 *  - Vertical scan sweep disc
 *  - Orbiting data nodes linked to the core
 * Colour eases smoothly when the risk level changes; spins faster while scanning.
 */
import React, { useEffect, useMemo, useRef } from 'react';
import { Canvas, useFrame } from '@react-three/fiber';
import * as THREE from 'three';

const fresnelVert = /* glsl */ `
  varying vec3 vN; varying vec3 vV;
  void main() {
    vec4 mv = modelViewMatrix * vec4(position, 1.0);
    vN = normalize(normalMatrix * normal);
    vV = normalize(-mv.xyz);
    gl_Position = projectionMatrix * mv;
  }
`;
const fresnelFrag = /* glsl */ `
  uniform vec3 uColor; uniform float uTime; uniform float uPower; uniform float uBase;
  varying vec3 vN; varying vec3 vV;
  void main() {
    float f = pow(1.0 - abs(dot(vN, vV)), uPower);
    float pulse = 0.85 + 0.15 * sin(uTime * 2.4);
    vec3 col = mix(uColor, vec3(1.0), f * 0.35);
    gl_FragColor = vec4(col * pulse, (uBase + f) * pulse);
  }
`;

function useFresnel(power, base) {
  const mat = useMemo(() => new THREE.ShaderMaterial({
    uniforms: { uColor: { value: new THREE.Color('#22D3EE') }, uTime: { value: 0 }, uPower: { value: power }, uBase: { value: base } },
    vertexShader: fresnelVert, fragmentShader: fresnelFrag,
    transparent: true, depthWrite: false, blending: THREE.AdditiveBlending,
  }), [power, base]);
  useEffect(() => () => mat.dispose(), [mat]);
  return mat;
}

function Orb({ color, scanning }) {
  const target = useMemo(() => new THREE.Color(color), [color]);
  const current = useRef(new THREE.Color(color));
  const core = useFresnel(2.0, 0.18);
  const halo = useFresnel(3.2, 0.0);
  const shell = useRef(), ringA = useRef(), ringB = useRef(), ringC = useRef(), sweep = useRef(), nodes = useRef(), links = useRef();
  const shellMat = useRef(), ringMats = useRef([]), sweepMat = useRef(), nodeMat = useRef(), linkMat = useRef();
  const speed = useRef(1);

  const NODE_COUNT = 7;
  const nodeData = useMemo(() => Array.from({ length: NODE_COUNT }, (_, i) => ({
    r: 2.05 + (i % 3) * 0.18, speed: 0.35 + (i % 4) * 0.12, phase: (i / NODE_COUNT) * Math.PI * 2, tilt: (i % 2 ? 1 : -1) * (0.3 + i * 0.07),
  })), []);
  const linkPositions = useMemo(() => new Float32Array(NODE_COUNT * 6), []);
  const tmp = useMemo(() => ({ m: new THREE.Matrix4(), p: new THREE.Vector3() }), []); // no per-frame allocations

  useFrame((state, dt) => {
    const t = state.clock.elapsedTime;
    speed.current += ((scanning ? 3.2 : 1) - speed.current) * 0.05;
    const s = speed.current;

    // smooth colour transition
    current.current.lerp(target, 0.06);
    const c = current.current;
    core.uniforms.uColor.value.copy(c); core.uniforms.uTime.value = t;
    halo.uniforms.uColor.value.copy(c); halo.uniforms.uTime.value = t;
    shellMat.current && shellMat.current.color.copy(c);
    ringMats.current.forEach(m => m && m.color.copy(c));
    sweepMat.current && sweepMat.current.color.copy(c);
    nodeMat.current && nodeMat.current.color.copy(c);
    linkMat.current && linkMat.current.color.copy(c);

    if (shell.current) { shell.current.rotation.y += dt * 0.25 * s; shell.current.rotation.x += dt * 0.1 * s; }
    if (ringA.current) ringA.current.rotation.z += dt * 0.9 * s;
    if (ringB.current) { ringB.current.rotation.z -= dt * 0.6 * s; }
    if (ringC.current) { ringC.current.rotation.z += dt * 0.4 * s; }
    if (sweep.current) {
      const y = Math.sin(t * 1.3 * Math.min(s, 2)) * 1.05;
      sweep.current.position.y = y;
      const r = Math.sqrt(Math.max(0.0001, 1.25 * 1.25 - y * y));
      sweep.current.scale.set(r, r, r);
      sweepMat.current.opacity = 0.35 + 0.25 * Math.cos(t * 2.6);
    }

    // orbiting nodes + links to core
    if (nodes.current) {
      const m = tmp.m;
      const p = tmp.p;
      nodeData.forEach((n, i) => {
        const a = n.phase + t * n.speed * s;
        p.set(Math.cos(a) * n.r, Math.sin(a * 0.7) * n.tilt, Math.sin(a) * n.r);
        m.makeTranslation(p.x, p.y, p.z);
        nodes.current.setMatrixAt(i, m);
        linkPositions.set([p.x * 0.42, p.y * 0.42, p.z * 0.42, p.x, p.y, p.z], i * 6);
      });
      nodes.current.instanceMatrix.needsUpdate = true;
      if (links.current) links.current.geometry.attributes.position.needsUpdate = true;
    }
  });

  return (
    <group rotation={[0.35, 0, 0]}>
      {/* core */}
      <mesh material={core}><sphereGeometry args={[0.85, 48, 48]} /></mesh>
      <mesh material={halo} scale={1.6}><sphereGeometry args={[0.85, 32, 32]} /></mesh>
      {/* wireframe shell */}
      <mesh ref={shell}>
        <icosahedronGeometry args={[1.22, 1]} />
        <meshBasicMaterial ref={shellMat} wireframe transparent opacity={0.35} blending={THREE.AdditiveBlending} depthWrite={false} />
      </mesh>
      {/* HUD rings */}
      <group rotation={[Math.PI / 2, 0, 0]}>
        <mesh ref={ringA}>
          <torusGeometry args={[1.62, 0.018, 8, 128, Math.PI * 1.45]} />
          <meshBasicMaterial ref={el => (ringMats.current[0] = el)} transparent opacity={0.9} blending={THREE.AdditiveBlending} depthWrite={false} />
        </mesh>
      </group>
      <group rotation={[Math.PI / 2.6, 0.5, 0]}>
        <mesh ref={ringB}>
          <torusGeometry args={[1.85, 0.012, 8, 128, Math.PI * 0.9]} />
          <meshBasicMaterial ref={el => (ringMats.current[1] = el)} transparent opacity={0.7} blending={THREE.AdditiveBlending} depthWrite={false} />
        </mesh>
      </group>
      <group rotation={[-Math.PI / 3, -0.6, 0]}>
        <mesh ref={ringC}>
          <torusGeometry args={[2.0, 0.008, 8, 128, Math.PI * 1.7]} />
          <meshBasicMaterial ref={el => (ringMats.current[2] = el)} transparent opacity={0.5} blending={THREE.AdditiveBlending} depthWrite={false} />
        </mesh>
      </group>
      {/* scan sweep */}
      <mesh ref={sweep} rotation={[-Math.PI / 2, 0, 0]}>
        <ringGeometry args={[0.92, 1.0, 96]} />
        <meshBasicMaterial ref={sweepMat} transparent opacity={0.5} side={THREE.DoubleSide} blending={THREE.AdditiveBlending} depthWrite={false} />
      </mesh>
      {/* data nodes */}
      <instancedMesh ref={nodes} args={[null, null, NODE_COUNT]}>
        <sphereGeometry args={[0.055, 12, 12]} />
        <meshBasicMaterial ref={nodeMat} toneMapped={false} />
      </instancedMesh>
      <lineSegments ref={links}>
        <bufferGeometry>
          <bufferAttribute attach="attributes-position" count={NODE_COUNT * 2} array={linkPositions} itemSize={3} />
        </bufferGeometry>
        <lineBasicMaterial ref={linkMat} transparent opacity={0.25} blending={THREE.AdditiveBlending} depthWrite={false} />
      </lineSegments>
    </group>
  );
}

export default function ScanOrb({ color = '#22D3EE', scanning = false, frameloop = 'always' }) {
  return (
    <Canvas
      frameloop={frameloop}
      dpr={[1, 1.75]}
      camera={{ position: [0, 0, 6.2], fov: 42 }}
      gl={{ antialias: true, alpha: true, powerPreference: 'high-performance' }}
      style={{ position: 'absolute', inset: 0, pointerEvents: 'none' }}
    >
      <Orb color={color} scanning={scanning} />
    </Canvas>
  );
}
