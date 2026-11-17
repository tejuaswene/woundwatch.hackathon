/**
 * TiltCard — 3D perspective tilt that follows the mouse, with a moving light glare
 * and depth-lifted children. Pure CSS transforms (no WebGL) so it is cheap everywhere.
 * Disabled for touch input and prefers-reduced-motion.
 */
import React, { useRef, useCallback } from 'react';

const reducedMotion = () =>
  typeof window !== 'undefined' && window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;

export default function TiltCard({
  children, style, className, onClick, max = 10, scale = 1.03, glare = true, glareColor = '255,255,255', radius = 20, ...rest
}) {
  const ref = useRef(null);
  const glareRef = useRef(null);
  const frame = useRef(0);

  const onMove = useCallback((e) => {
    if (e.pointerType === 'touch' || reducedMotion()) return;
    const el = ref.current;
    if (!el) return;
    const r = el.getBoundingClientRect();
    const px = (e.clientX - r.left) / r.width;   // 0..1
    const py = (e.clientY - r.top) / r.height;   // 0..1
    cancelAnimationFrame(frame.current);
    frame.current = requestAnimationFrame(() => {
      const rx = (0.5 - py) * max * 2;
      const ry = (px - 0.5) * max * 2;
      el.style.transition = 'transform 0.08s linear, box-shadow 0.3s ease';
      el.style.transform = `perspective(900px) rotateX(${rx.toFixed(2)}deg) rotateY(${ry.toFixed(2)}deg) scale3d(${scale},${scale},${scale})`;
      if (glareRef.current) {
        glareRef.current.style.opacity = '1';
        glareRef.current.style.background =
          `radial-gradient(circle at ${(px * 100).toFixed(1)}% ${(py * 100).toFixed(1)}%, rgba(${glareColor},0.35) 0%, rgba(${glareColor},0.08) 35%, transparent 65%)`;
      }
    });
  }, [max, scale, glareColor]);

  const onLeave = useCallback(() => {
    cancelAnimationFrame(frame.current);
    const el = ref.current;
    if (!el) return;
    el.style.transition = 'transform 0.6s cubic-bezier(0.16, 1, 0.3, 1), box-shadow 0.3s ease';
    el.style.transform = 'perspective(900px) rotateX(0deg) rotateY(0deg) scale3d(1,1,1)';
    if (glareRef.current) glareRef.current.style.opacity = '0';
  }, []);

  return (
    <div
      ref={ref}
      className={className}
      onClick={onClick}
      onPointerMove={onMove}
      onPointerLeave={onLeave}
      style={{
        position: 'relative', transformStyle: 'preserve-3d', willChange: 'transform',
        borderRadius: radius, cursor: onClick ? 'pointer' : undefined, ...style,
      }}
      {...rest}
    >
      {children}
      {glare && (
        <div ref={glareRef} aria-hidden style={{
          position: 'absolute', inset: 0, borderRadius: radius, pointerEvents: 'none',
          opacity: 0, transition: 'opacity 0.3s ease', mixBlendMode: 'soft-light', zIndex: 2,
        }} />
      )}
    </div>
  );
}

/** Wrap content to lift it toward the viewer inside a TiltCard */
export function Depth({ z = 30, children, style }) {
  return <div style={{ transform: `translateZ(${z}px)`, transformStyle: 'preserve-3d', ...style }}>{children}</div>;
}
