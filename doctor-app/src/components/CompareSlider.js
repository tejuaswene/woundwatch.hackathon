import React, { useState, useRef, useCallback, useEffect } from 'react';
import { photoUrl } from '../api';

const riskColor = { GREEN: '#2BA84A', YELLOW: '#E89B2C', RED: '#D64545' };

const fmtDate = (d) => new Date(d).toLocaleDateString('en-IN', { day: 'numeric', month: 'short' });

/**
 * Before / After wound comparison:
 * drag the handle to reveal how the wound changed between two days,
 * with the change in every AI metric shown underneath.
 * `photos` is newest-first (as returned by the API).
 */
function CompareSlider({ photos }) {
  const ordered = [...photos].reverse(); // oldest -> newest
  const firstTime = new Date(ordered[0].uploaded_at).getTime();
  const dayOf = (p) => Math.floor((new Date(p.uploaded_at).getTime() - firstTime) / 86400000) + 1;

  const [beforeId, setBeforeId] = useState(ordered[0].id);
  const [afterId, setAfterId] = useState(ordered[ordered.length - 1].id);
  const [pos, setPos] = useState(50);
  const [heat, setHeat] = useState(false);
  const [heatOk, setHeatOk] = useState(true);
  const box = useRef(null);
  const dragging = useRef(false);

  // keep selections valid if the photo list changes
  useEffect(() => {
    if (!ordered.find(p => p.id === beforeId)) setBeforeId(ordered[0].id);
    if (!ordered.find(p => p.id === afterId)) setAfterId(ordered[ordered.length - 1].id);
  }, [photos]); // eslint-disable-line

  const before = ordered.find(p => p.id === beforeId) || ordered[0];
  const after = ordered.find(p => p.id === afterId) || ordered[ordered.length - 1];

  const moveTo = useCallback((clientX) => {
    const r = box.current.getBoundingClientRect();
    setPos(Math.max(0, Math.min(100, ((clientX - r.left) / r.width) * 100)));
  }, []);

  useEffect(() => {
    const move = (e) => { if (dragging.current) moveTo(e.clientX); };
    const up = () => { dragging.current = false; };
    window.addEventListener('pointermove', move);
    window.addEventListener('pointerup', up);
    return () => { window.removeEventListener('pointermove', move); window.removeEventListener('pointerup', up); };
  }, [moveTo]);

  const src = (p) => photoUrl(heat && heatOk ? `heatmap_${p.filename}` : p.filename);

  // metric deltas (higher = worse for all of them)
  const metrics = [
    { label: 'Risk score', a: (before.risk_score || 0) * 100, b: (after.risk_score || 0) * 100, unit: '%' },
    { label: 'Redness', a: before.redness_index || 0, b: after.redness_index || 0, unit: '' },
    { label: 'Swelling', a: before.swelling_score || 0, b: after.swelling_score || 0, unit: '' },
    { label: 'Colour drift', a: before.color_deviation || 0, b: after.color_deviation || 0, unit: '' },
  ];
  const riskDelta = Math.round(metrics[0].b - metrics[0].a);
  const days = Math.max(0, Math.round((new Date(after.uploaded_at) - new Date(before.uploaded_at)) / 86400000));
  const verdict = riskDelta >= 10 ? { t: 'Worsening', c: '#D64545', bg: '#FDEAEA', i: '📈' }
    : riskDelta <= -10 ? { t: 'Improving', c: '#2BA84A', bg: '#E8F8EC', i: '📉' }
    : { t: 'Stable', c: '#E89B2C', bg: '#FFF5E5', i: '➡️' };

  const select = (value, onChange, other) => (
    <select value={value} onChange={e => onChange(Number(e.target.value))}
      style={{ width: 'auto', padding: '8px 12px', fontSize: 13, fontWeight: 600, borderRadius: 10, cursor: 'pointer' }}>
      {ordered.map(p => (
        <option key={p.id} value={p.id} disabled={p.id === other}>
          Day {dayOf(p)} · {fmtDate(p.uploaded_at)} · {Math.round((p.risk_score || 0) * 100)}%
        </option>
      ))}
    </select>
  );

  const tag = (text, p, side) => (
    <div style={{
      position: 'absolute', top: 12, [side]: 12, padding: '6px 11px', borderRadius: 10, zIndex: 3,
      background: 'rgba(10,10,34,0.72)', color: '#fff', fontSize: 11.5, fontWeight: 800, letterSpacing: '0.04em',
      backdropFilter: 'blur(6px)', borderLeft: `3px solid ${riskColor[p.risk_level] || '#7F79B6'}`, pointerEvents: 'none',
    }}>
      {text} · DAY {dayOf(p)} · {fmtDate(p.uploaded_at)}
      <span style={{ marginLeft: 8, color: riskColor[p.risk_level] }}>{Math.round((p.risk_score || 0) * 100)}%</span>
    </div>
  );

  return (
    <div>
      {/* controls */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 10, flexWrap: 'wrap', marginBottom: 14 }}>
        <span style={{ fontSize: 12, fontWeight: 700, color: '#8C8AAE' }}>BEFORE</span>
        {select(beforeId, setBeforeId, afterId)}
        <span style={{ color: '#B8B6D0' }}>→</span>
        <span style={{ fontSize: 12, fontWeight: 700, color: '#8C8AAE' }}>AFTER</span>
        {select(afterId, setAfterId, beforeId)}
        <div style={{ marginLeft: 'auto', display: 'flex', gap: 4, background: '#EEEDFA', borderRadius: 10, padding: 3 }}>
          {[{ k: false, l: 'Photo' }, { k: true, l: '🔥 Heatmap' }].map(t => (
            <button key={t.l} onClick={() => { setHeatOk(true); setHeat(t.k); }} style={{
              padding: '6px 12px', fontSize: 12, borderRadius: 8,
              background: heat === t.k ? '#fff' : 'transparent', color: heat === t.k ? '#2F2B6E' : '#8C8AAE',
              boxShadow: heat === t.k ? '0 2px 6px rgba(47,43,110,0.1)' : 'none',
            }}>{t.l}</button>
          ))}
        </div>
      </div>

      {/* slider */}
      <div
        ref={box}
        onPointerDown={(e) => { dragging.current = true; moveTo(e.clientX); }}
        tabIndex={0}
        onKeyDown={(e) => {
          if (e.key === 'ArrowLeft') setPos(p => Math.max(0, p - 4));
          if (e.key === 'ArrowRight') setPos(p => Math.min(100, p + 4));
        }}
        style={{
          position: 'relative', height: 400, borderRadius: 18, overflow: 'hidden', background: '#0A0A22',
          cursor: 'ew-resize', userSelect: 'none', touchAction: 'none', outline: 'none',
          boxShadow: '0 12px 36px rgba(27,22,80,0.25)',
        }}
      >
        {/* AFTER (full) */}
        <img src={src(after)} alt="After" draggable={false} onError={() => heat && setHeatOk(false)}
          style={{ position: 'absolute', inset: 0, width: '100%', height: '100%', objectFit: 'cover' }} />
        {/* BEFORE (clipped to the left of the handle) */}
        <img src={src(before)} alt="Before" draggable={false} onError={() => heat && setHeatOk(false)}
          style={{ position: 'absolute', inset: 0, width: '100%', height: '100%', objectFit: 'cover',
            clipPath: `inset(0 ${100 - pos}% 0 0)` }} />

        {tag('BEFORE', before, 'left')}
        {tag('AFTER', after, 'right')}

        {/* handle */}
        <div style={{ position: 'absolute', top: 0, bottom: 0, left: `${pos}%`, width: 3, marginLeft: -1.5, zIndex: 2,
          background: 'linear-gradient(#22D3EE, #8B5CF6)', boxShadow: '0 0 14px rgba(34,211,238,0.9)', pointerEvents: 'none' }}>
          <div style={{
            position: 'absolute', top: '50%', left: '50%', transform: 'translate(-50%,-50%)',
            width: 44, height: 44, borderRadius: '50%', background: '#fff', display: 'grid', placeItems: 'center',
            boxShadow: '0 6px 20px rgba(0,0,0,0.35), 0 0 0 4px rgba(34,211,238,0.35)', fontSize: 15, fontWeight: 900, color: '#2F2B6E',
          }}>⟷</div>
        </div>

        {heat && !heatOk && (
          <div style={{ position: 'absolute', bottom: 12, left: 12, zIndex: 3, padding: '6px 10px', borderRadius: 8,
            background: 'rgba(10,10,34,0.75)', color: '#FCD34D', fontSize: 11.5, fontWeight: 700 }}>
            Heatmap not available for one of these photos — showing originals
          </div>
        )}
      </div>

      {/* change summary */}
      <div style={{ display: 'grid', gridTemplateColumns: '1.3fr repeat(4, 1fr)', gap: 10, marginTop: 14 }}>
        <div style={{ background: verdict.bg, borderRadius: 14, padding: '12px 14px', display: 'flex', alignItems: 'center', gap: 10 }}>
          <span style={{ fontSize: 24 }}>{verdict.i}</span>
          <div>
            <p style={{ fontWeight: 900, color: verdict.c, fontSize: 15 }}>{verdict.t}</p>
            <p style={{ fontSize: 11.5, color: '#55537A' }}>
              Risk {riskDelta >= 0 ? '+' : ''}{riskDelta} pts over {days} day{days !== 1 ? 's' : ''}
            </p>
          </div>
        </div>
        {metrics.map(m => {
          const d = Math.round(m.b - m.a);
          const col = d > 2 ? '#D64545' : d < -2 ? '#2BA84A' : '#8C8AAE';
          return (
            <div key={m.label} style={{ background: '#F7F6FB', borderRadius: 14, padding: '12px 14px' }}>
              <p style={{ fontSize: 11, color: '#8C8AAE', fontWeight: 700 }}>{m.label}</p>
              <p style={{ fontSize: 13, color: '#2F2B6E', fontWeight: 700, marginTop: 4 }}>
                {Math.round(m.a)}{m.unit} → {Math.round(m.b)}{m.unit}
              </p>
              <p style={{ fontSize: 12.5, fontWeight: 900, color: col, marginTop: 2 }}>
                {d > 0 ? '▲' : d < 0 ? '▼' : '■'} {d > 0 ? '+' : ''}{d}{m.unit}
              </p>
            </div>
          );
        })}
      </div>
    </div>
  );
}

export default CompareSlider;
