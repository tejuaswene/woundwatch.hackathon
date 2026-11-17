/**
 * WoundWatch 3D — safe wrappers.
 * - Lazy-loads three.js scenes (separate JS chunk, page renders instantly)
 * - Falls back to a CSS gradient when WebGL is unavailable or crashes
 * - Respects "prefers-reduced-motion" (renders a still frame)
 * - Pauses rendering when the canvas is off-screen or the tab is hidden
 */
import React, { Suspense, lazy, useEffect, useRef, useState } from 'react';

const MedicalBackgroundScene = lazy(() => import('./MedicalBackground'));
const ScanOrbScene = lazy(() => import('./ScanOrb'));

export function webglAvailable() {
  try {
    const c = document.createElement('canvas');
    return !!(window.WebGLRenderingContext && (c.getContext('webgl2') || c.getContext('webgl')));
  } catch {
    return false;
  }
}

export function usePrefersReducedMotion() {
  const [reduced, setReduced] = useState(() =>
    typeof window !== 'undefined' && window.matchMedia
      ? window.matchMedia('(prefers-reduced-motion: reduce)').matches
      : false
  );
  useEffect(() => {
    if (!window.matchMedia) return;
    const mq = window.matchMedia('(prefers-reduced-motion: reduce)');
    const onChange = () => setReduced(mq.matches);
    mq.addEventListener ? mq.addEventListener('change', onChange) : mq.addListener(onChange);
    return () => (mq.removeEventListener ? mq.removeEventListener('change', onChange) : mq.removeListener(onChange));
  }, []);
  return reduced;
}

/** true while the element is on screen AND the browser tab is visible */
function useActive(ref) {
  const [inView, setInView] = useState(true);
  const [tabVisible, setTabVisible] = useState(!document.hidden);
  useEffect(() => {
    const el = ref.current;
    if (!el || !('IntersectionObserver' in window)) return;
    const io = new IntersectionObserver(([e]) => setInView(e.isIntersecting), { threshold: 0.01 });
    io.observe(el);
    return () => io.disconnect();
  }, [ref]);
  useEffect(() => {
    const onVis = () => setTabVisible(!document.hidden);
    document.addEventListener('visibilitychange', onVis);
    return () => document.removeEventListener('visibilitychange', onVis);
  }, []);
  return inView && tabVisible;
}

class ErrorBoundary extends React.Component {
  constructor(p) { super(p); this.state = { failed: false }; }
  static getDerivedStateFromError() { return { failed: true }; }
  componentDidCatch(err) { console.warn('[WoundWatch 3D] disabled:', err && err.message); }
  render() { return this.state.failed ? this.props.fallback : this.props.children; }
}

function Guard({ children, fallback, style, className }) {
  const ref = useRef(null);
  const active = useActive(ref);
  const reduced = usePrefersReducedMotion();
  const [ok] = useState(webglAvailable);
  return (
    <div ref={ref} className={className} style={{ position: 'relative', ...style }}>
      {ok ? (
        <ErrorBoundary fallback={fallback}>
          <Suspense fallback={fallback}>
            {children({ frameloop: reduced ? 'demand' : active ? 'always' : 'never', reduced })}
          </Suspense>
        </ErrorBoundary>
      ) : fallback}
    </div>
  );
}

const fill = { position: 'absolute', inset: 0 };

/** Full-bleed animated 3D medical background (particles + DNA helix + medical cross). */
export function MedicalBackground3D({ style, className, density = 1, showCross = true, showHelix = true }) {
  const fallback = (
    <div style={{ ...fill, background: 'radial-gradient(circle at 30% 30%, rgba(34,211,238,0.18), transparent 55%), radial-gradient(circle at 75% 70%, rgba(139,92,246,0.22), transparent 55%)' }} />
  );
  return (
    <Guard style={{ ...fill, ...style }} className={className} fallback={fallback}>
      {(p) => <MedicalBackgroundScene {...p} density={density} showCross={showCross} showHelix={showHelix} />}
    </Guard>
  );
}

/**
 * Glowing AI scan orb with HUD rings.
 * level: GREEN | YELLOW | RED | null  (sets colour)   scanning: speeds up while analyzing
 */
export function ScanOrb3D({ level, scanning = false, style, className, size }) {
  const color = { GREEN: '#2BD46A', YELLOW: '#F5A524', RED: '#FF4D5E' }[level] || '#22D3EE';
  const fallback = (
    <div style={{ ...fill, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
      <div style={{
        width: '55%', aspectRatio: '1', borderRadius: '50%',
        background: `radial-gradient(circle, ${color}cc 0%, ${color}33 45%, transparent 70%)`,
        boxShadow: `0 0 40px ${color}55`
      }} />
    </div>
  );
  return (
    <Guard style={{ width: size, height: size, ...style }} className={className} fallback={fallback}>
      {(p) => <ScanOrbScene {...p} color={color} scanning={scanning} />}
    </Guard>
  );
}
