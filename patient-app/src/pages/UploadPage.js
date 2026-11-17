import React, { useState, useRef, useEffect } from 'react';
import { uploadPhoto } from '../api';
import RiskBadge from '../components/RiskBadge';
import { ScanOrb3D } from '../three/Scene3D';

const SCAN_STEPS = [
  'Validating wound photo…',
  'Locating wound region…',
  'Measuring redness (LAB colour)…',
  'Checking swelling & discharge…',
  'Comparing colour drift…',
  'Scoring infection risk…',
];
const API_BASE = window.API_BASE || 'http://localhost:8000';

/* Futuristic AI scan overlay drawn on top of the photo while it is analysed */
function ScanOverlay({ label }) {
  const [step, setStep] = useState(0);
  const [pct, setPct] = useState(4);
  useEffect(() => {
    const s = setInterval(() => setStep(i => Math.min(i + 1, SCAN_STEPS.length - 1)), 900);
    const p = setInterval(() => setPct(v => Math.min(96, v + Math.max(1, (96 - v) * 0.09))), 120);
    return () => { clearInterval(s); clearInterval(p); };
  }, []);
  const corner = (pos) => ({
    position: 'absolute', width: 26, height: 26, borderColor: '#22D3EE', borderStyle: 'solid', borderWidth: 0,
    ...(pos.includes('t') ? { top: 14, borderTopWidth: 3 } : { bottom: 14, borderBottomWidth: 3 }),
    ...(pos.includes('l') ? { left: 14, borderLeftWidth: 3 } : { right: 14, borderRightWidth: 3 }),
    borderRadius: 4, filter: 'drop-shadow(0 0 6px #22D3EE)',
  });
  return (
    <div style={{ position: 'absolute', inset: 0, background: 'rgba(8,8,30,0.55)', backdropFilter: 'saturate(1.3)', animation: 'fadeIn 0.3s ease' }}>
      {/* grid */}
      <div style={{ position: 'absolute', inset: 0, opacity: 0.5,
        backgroundImage: 'linear-gradient(rgba(34,211,238,0.12) 1px, transparent 1px), linear-gradient(90deg, rgba(34,211,238,0.12) 1px, transparent 1px)',
        backgroundSize: '28px 28px' }} />
      {/* laser sweep */}
      <div style={{ position: 'absolute', left: 0, right: 0, height: '90px', animation: 'wwScanSweep 1.8s ease-in-out infinite alternate',
        background: 'linear-gradient(180deg, transparent, rgba(34,211,238,0.28) 85%, rgba(103,232,249,0.95) 100%)' }} />
      {['tl', 'tr', 'bl', 'br'].map(c => <div key={c} style={corner(c)} />)}
      {label && (
        <div style={{ position: 'absolute', top: 18, left: '50%', transform: 'translateX(-50%)', padding: '5px 12px', borderRadius: 999,
          background: 'rgba(8,8,30,0.75)', border: '1px solid rgba(34,211,238,0.4)', color: '#67E8F9', fontSize: 11.5, fontWeight: 800,
          letterSpacing: '0.04em', whiteSpace: 'nowrap' }}>{label}</div>
      )}
      {/* 3D AI orb */}
      <div style={{ position: 'absolute', left: '50%', top: '44%', width: 170, height: 170, transform: 'translate(-50%,-50%)' }}>
        <ScanOrb3D scanning style={{ position: 'absolute', inset: 0 }} />
      </div>
      {/* status */}
      <div style={{ position: 'absolute', left: 16, right: 16, bottom: 16, padding: '12px 14px', borderRadius: 14,
        background: 'rgba(8,8,30,0.7)', border: '1px solid rgba(34,211,238,0.3)', color: '#fff', backdropFilter: 'blur(8px)' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 12.5, fontWeight: 700 }}>
          <span key={step} style={{ animation: 'fadeIn 0.3s ease' }}>🧠 {SCAN_STEPS[step]}</span>
          <span style={{ color: '#67E8F9' }}>{Math.round(pct)}%</span>
        </div>
        <div style={{ height: 4, borderRadius: 4, background: 'rgba(255,255,255,0.12)', marginTop: 8, overflow: 'hidden' }}>
          <div style={{ width: `${pct}%`, height: '100%', borderRadius: 4, background: 'linear-gradient(90deg, #22D3EE, #8B5CF6)',
            boxShadow: '0 0 10px #22D3EE' }} />
        </div>
      </div>
      <style>{`@keyframes wwScanSweep { from { top: -90px; } to { top: calc(100% - 4px); } }`}</style>
    </div>
  );
}

/* Circular Progress Ring */
function ProgressRing({ value, color, size = 80, strokeWidth = 6, label }) {
  const r = (size - strokeWidth) / 2;
  const circ = 2 * Math.PI * r;
  const offset = circ - (value / 100) * circ;
  return (
    <div style={{ textAlign: 'center' }}>
      <svg width={size} height={size} style={{ transform: 'rotate(-90deg)' }}>
        <circle cx={size/2} cy={size/2} r={r} fill="none" stroke="rgba(0,0,0,0.06)" strokeWidth={strokeWidth} />
        <circle cx={size/2} cy={size/2} r={r} fill="none" stroke={color} strokeWidth={strokeWidth}
          strokeDasharray={circ} strokeDashoffset={offset} strokeLinecap="round"
          style={{ transition: 'stroke-dashoffset 1.5s cubic-bezier(0.16, 1, 0.3, 1)' }} />
        <text x={size/2} y={size/2} textAnchor="middle" dominantBaseline="central"
          style={{ transform: 'rotate(90deg)', transformOrigin: 'center', fontSize: `${size * 0.22}px`, fontWeight: 800, fill: color }}>
          {value}%
        </text>
      </svg>
      {label && <p style={{ fontSize: '11px', fontWeight: 600, color: '#8C8AAE', marginTop: '4px' }}>{label}</p>}
    </div>
  );
}

const MAX_PHOTOS = 10;
const riskColor = { GREEN: '#2BA84A', YELLOW: '#E89B2C', RED: '#D64545' };
const riskOrder = { RED: 3, YELLOW: 2, GREEN: 1 };
let nextId = 1;

/* Full detail view for one analysed photo (used when a single photo was scanned) */
function ResultDetail({ result }) {
  const [showHeatmap, setShowHeatmap] = useState(false);
  const [heatmapOk, setHeatmapOk] = useState(true);
  return (
    <>
      <div style={{
        background: riskColor[result.risk_level] || '#7F79B6', borderRadius: '24px', padding: '28px', color: '#fff',
        textAlign: 'center', marginBottom: '20px', boxShadow: `0 12px 40px ${riskColor[result.risk_level]}30`,
        position: 'relative', overflow: 'hidden',
      }}>
        <div style={{ position: 'absolute', top: '-30px', right: '-30px', width: '100px', height: '100px', borderRadius: '50%', background: 'rgba(255,255,255,0.08)' }} />
        <p style={{ fontSize: '12px', fontWeight: 600, opacity: 0.7, textTransform: 'uppercase', letterSpacing: '1px' }}>Risk Assessment</p>
        <p style={{ fontSize: '52px', fontWeight: 900, marginTop: '4px', animation: 'countPop 0.6s ease forwards' }}>
          {Math.round(result.risk_score * 100)}%
        </p>
        <RiskBadge level={result.risk_level} size="lg" />
      </div>
      <div style={{
        display: 'flex', justifyContent: 'space-around', gap: '8px', background: '#fff', borderRadius: '24px', padding: '24px 16px',
        boxShadow: '0 2px 12px rgba(47,43,110,0.06)', marginBottom: '16px', animation: 'fadeInUp 0.5s 0.1s ease forwards', opacity: 0,
      }}>
        {/* backend returns these as 0-100 indices */}
        <ProgressRing value={Math.round(Math.min(100, result.redness_index || 0))} color="#D64545" label="Redness" />
        <ProgressRing value={Math.round(Math.min(100, result.swelling_score || 0))} color="#E89B2C" label="Swelling" />
        <ProgressRing value={Math.round(Math.min(100, result.color_deviation || 0))} color="#7F79B6" label="Colour drift" />
      </div>
      {result.filename && heatmapOk && (
        <div style={{ background: '#fff', borderRadius: '20px', padding: '16px', boxShadow: '0 2px 12px rgba(47,43,110,0.06)', marginBottom: '16px',
          animation: 'fadeInUp 0.5s 0.18s ease forwards', opacity: 0 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: showHeatmap ? '12px' : 0 }}>
            <p style={{ fontWeight: 700, fontSize: '14px', color: '#2F2B6E' }}>🔥 Heatmap View</p>
            <button onClick={() => setShowHeatmap(!showHeatmap)} style={{ padding: '6px 14px', borderRadius: '8px', fontSize: '12px', fontWeight: 600,
              background: showHeatmap ? '#2F2B6E' : '#F5F4FA', color: showHeatmap ? '#fff' : '#7F79B6', border: 'none' }}>
              {showHeatmap ? 'Hide' : 'Show'}
            </button>
          </div>
          {showHeatmap && (
            <img src={`${API_BASE}/uploads/heatmap_${result.filename}`} onError={() => setHeatmapOk(false)}
              alt="Heatmap" style={{ width: '100%', borderRadius: '14px', animation: 'scaleIn 0.4s ease' }} />
          )}
        </div>
      )}
      {result.recommendation && (
        <div style={{ background: '#fff', borderRadius: '20px', padding: '18px 20px', boxShadow: '0 2px 12px rgba(47,43,110,0.06)', marginBottom: '16px',
          borderLeft: `4px solid ${riskColor[result.risk_level]}`, animation: 'fadeInUp 0.5s 0.25s ease forwards', opacity: 0 }}>
          <p style={{ fontWeight: 700, fontSize: '13px', color: '#2F2B6E', marginBottom: '8px' }}>🤖 AI Recommendation</p>
          <p style={{ fontSize: '13px', color: '#555', lineHeight: '1.6' }}>{result.recommendation}</p>
        </div>
      )}
    </>
  );
}

/* Compact result card for one photo in a multi-photo scan */
function ResultCard({ item, index, onRetry }) {
  const [open, setOpen] = useState(false);
  const [heat, setHeat] = useState(false);
  const [heatOk, setHeatOk] = useState(true);
  const r = item.result;
  const c = r ? riskColor[r.risk_level] : '#D64545';
  return (
    <div style={{
      background: '#fff', borderRadius: '18px', padding: '12px', boxShadow: '0 2px 12px rgba(47,43,110,0.06)',
      borderLeft: `4px solid ${c}`, animation: `fadeInUp 0.4s ${index * 0.06}s ease both`,
    }}>
      <div style={{ display: 'flex', gap: '12px', alignItems: 'center' }}>
        <img src={heat && heatOk && r ? `${API_BASE}/uploads/heatmap_${r.filename}` : item.url} alt={`Photo ${index + 1}`}
          onError={() => setHeatOk(false)}
          style={{ width: '64px', height: '64px', borderRadius: '12px', objectFit: 'cover', flexShrink: 0 }} />
        <div style={{ flex: 1, minWidth: 0 }}>
          <p style={{ fontSize: '11px', color: '#8C8AAE', fontWeight: 700 }}>PHOTO {index + 1}</p>
          {r ? (
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginTop: '3px', flexWrap: 'wrap' }}>
              <span style={{ fontSize: '22px', fontWeight: 900, color: c }}>{Math.round(r.risk_score * 100)}%</span>
              <RiskBadge level={r.risk_level} />
            </div>
          ) : (
            <p style={{ fontSize: '12.5px', color: '#B42318', fontWeight: 600, marginTop: '3px', lineHeight: 1.35 }}>⚠️ {item.error}</p>
          )}
        </div>
        {r ? (
          <button onClick={() => setOpen(o => !o)} style={{ padding: '6px 10px', borderRadius: '10px', fontSize: '12px', border: 'none',
            background: '#F5F4FA', color: '#7F79B6', fontWeight: 700, flexShrink: 0 }}>{open ? 'Less' : 'Details'}</button>
        ) : (
          <button onClick={onRetry} style={{ padding: '6px 10px', borderRadius: '10px', fontSize: '12px', border: 'none',
            background: '#FDEAEA', color: '#B42318', fontWeight: 700, flexShrink: 0 }}>Retry</button>
        )}
      </div>
      {r && open && (
        <div style={{ marginTop: '12px', animation: 'fadeIn 0.3s ease' }}>
          <div style={{ display: 'flex', gap: '6px' }}>
            {[{ l: 'Redness', v: r.redness_index, c: '#D64545' }, { l: 'Swelling', v: r.swelling_score, c: '#E89B2C' }, { l: 'Colour drift', v: r.color_deviation, c: '#7F79B6' }].map(m => (
              <div key={m.l} style={{ flex: 1, background: '#F7F6FB', borderRadius: '10px', padding: '8px', textAlign: 'center' }}>
                <p style={{ fontSize: '16px', fontWeight: 800, color: m.c }}>{Math.round(m.v || 0)}</p>
                <p style={{ fontSize: '10px', color: '#8C8AAE', fontWeight: 600 }}>{m.l}</p>
              </div>
            ))}
          </div>
          {r.recommendation && <p style={{ fontSize: '12.5px', color: '#555', lineHeight: 1.55, marginTop: '10px' }}>🤖 {r.recommendation}</p>}
          {heatOk && (
            <button onClick={() => setHeat(h => !h)} style={{ marginTop: '10px', padding: '6px 12px', borderRadius: '8px', fontSize: '12px', border: 'none',
              background: heat ? '#2F2B6E' : '#F5F4FA', color: heat ? '#fff' : '#7F79B6', fontWeight: 700 }}>
              🔥 {heat ? 'Show photo' : 'Show heatmap'}
            </button>
          )}
        </div>
      )}
    </div>
  );
}

function UploadPage({ user }) {
  // items: { id, file, url, status: 'ready' | 'scanning' | 'done' | 'error', result, error }
  const [items, setItems] = useState([]);
  const [activeId, setActiveId] = useState(null);
  const [phase, setPhase] = useState('pick'); // pick | scanning | results
  const [dragOver, setDragOver] = useState(false);
  const [notice, setNotice] = useState('');
  const fileRef = useRef();
  const cameraRef = useRef();
  const itemsRef = useRef(items);
  itemsRef.current = items;

  // free preview URLs when leaving the page
  useEffect(() => () => itemsRef.current.forEach(i => URL.revokeObjectURL(i.url)), []);

  const addFiles = (fileList) => {
    const imgs = Array.from(fileList || []).filter(f => f && f.type.startsWith('image/'));
    if (!imgs.length) return;
    const room = MAX_PHOTOS - items.length;
    const accepted = imgs.slice(0, Math.max(0, room));
    setNotice(imgs.length > accepted.length ? `Only ${MAX_PHOTOS} photos at a time — extra photos were skipped.` : '');
    const added = accepted.map(f => ({ id: nextId++, file: f, url: URL.createObjectURL(f), status: 'ready', result: null, error: '' }));
    if (!added.length) return;
    setItems(prev => [...prev, ...added]);
    setActiveId(added[0].id);
  };

  const removeItem = (id) => {
    setItems(prev => {
      const it = prev.find(i => i.id === id);
      if (it) URL.revokeObjectURL(it.url);
      const rest = prev.filter(i => i.id !== id);
      if (activeId === id) setActiveId(rest.length ? rest[rest.length - 1].id : null);
      return rest;
    });
    setNotice('');
  };

  const update = (id, patch) => setItems(prev => prev.map(i => (i.id === id ? { ...i, ...patch } : i)));

  const scanOne = async (it, minMs) => {
    setActiveId(it.id);
    update(it.id, { status: 'scanning', error: '' });
    try {
      const [res] = await Promise.all([uploadPhoto(user.phone, it.file), new Promise(r => setTimeout(r, minMs))]);
      update(it.id, { status: 'done', result: res.data });
    } catch (e) {
      // backend explains rejections, e.g. "This doesn't look like a close-up wound photo"
      update(it.id, { status: 'error', error: e?.response?.data?.detail || 'Upload failed. Check your connection.' });
    }
  };

  const analyzeAll = async () => {
    const queue = items.filter(i => i.status !== 'done');
    if (!queue.length) return;
    setPhase('scanning');
    const minMs = items.length === 1 ? 2200 : 1200; // let the scan animation play
    for (const it of queue) {
      // one at a time so the AI server isn't overloaded
      // eslint-disable-next-line no-await-in-loop
      await scanOne(it, minMs);
    }
    // single photo rejected -> stay on the picker and show why, so they can swap it
    const after = itemsRef.current;
    if (after.length === 1 && after[0].status === 'error') {
      setNotice(after[0].error);
      update(after[0].id, { status: 'ready' });
      setPhase('pick');
      return;
    }
    setPhase('results');
  };

  const retry = async (id) => {
    const it = itemsRef.current.find(i => i.id === id);
    if (!it) return;
    setPhase('scanning');
    await scanOne(it, 1200);
    setPhase('results');
  };

  const reset = () => {
    items.forEach(i => URL.revokeObjectURL(i.url));
    setItems([]); setActiveId(null); setPhase('pick'); setNotice('');
  };

  const active = items.find(i => i.id === activeId) || items[0];
  const scanning = phase === 'scanning';
  const doneCount = items.filter(i => i.status === 'done').length;
  const scanIndex = items.findIndex(i => i.status === 'scanning');
  const ok = items.filter(i => i.result);
  const failed = items.filter(i => i.status === 'error');
  const worst = ok.reduce((w, i) => (!w || riskOrder[i.result.risk_level] > riskOrder[w.result.risk_level] ||
    (i.result.risk_level === w.result.risk_level && i.result.risk_score > w.result.risk_score) ? i : w), null);

  const statusDot = (it) => {
    if (it.status === 'scanning') return { bg: '#22D3EE', t: '' };
    if (it.status === 'done') return { bg: riskColor[it.result.risk_level], t: '✓' };
    if (it.status === 'error') return { bg: '#D64545', t: '!' };
    return null;
  };

  const primaryBtn = {
    padding: '14px', borderRadius: '14px', background: 'linear-gradient(135deg, #2F2B6E, #7F79B6)', color: '#fff',
    fontWeight: 700, fontSize: '14px', boxShadow: '0 6px 20px rgba(47,43,110,0.25)', border: 'none',
  };
  const softBtn = { padding: '14px', borderRadius: '14px', background: '#F5F4FA', color: '#7F79B6', fontWeight: 700, fontSize: '14px', border: 'none' };

  return (
    <div style={{ padding: '20px 16px 100px', maxWidth: '480px', margin: '0 auto' }}>
      {/* hidden inputs: gallery allows multiple, camera takes one shot at a time */}
      <input ref={fileRef} type="file" accept="image/*" multiple hidden
        onChange={e => { addFiles(e.target.files); e.target.value = ''; }} />
      <input ref={cameraRef} type="file" accept="image/*" capture="environment" hidden
        onChange={e => { addFiles(e.target.files); e.target.value = ''; }} />

      {/* Header */}
      <div style={{ marginBottom: '20px', animation: 'fadeInUp 0.4s ease forwards' }}>
        <h1 style={{
          fontSize: '26px', fontWeight: 900, letterSpacing: '-0.03em',
          background: 'linear-gradient(135deg, #2F2B6E, #7F79B6)',
          WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent', backgroundClip: 'text',
        }}>Scan Wound</h1>
        <p style={{ color: '#8C8AAE', fontSize: '13px', marginTop: '4px' }}>
          Upload one or more photos for AI-powered analysis
        </p>
      </div>

      {phase !== 'results' ? (
        <>
          {items.length === 0 ? (
            /* ===== Empty: drop zone ===== */
            <>
              <div
                onDragOver={e => { e.preventDefault(); setDragOver(true); }}
                onDragLeave={() => setDragOver(false)}
                onDrop={e => { e.preventDefault(); setDragOver(false); addFiles(e.dataTransfer.files); }}
                onClick={() => fileRef.current.click()}
                style={{
                  border: `2px dashed ${dragOver ? '#7F79B6' : '#E8E7F0'}`, borderRadius: '24px', padding: '44px 24px', textAlign: 'center',
                  background: dragOver ? 'rgba(127,121,182,0.06)' : '#fff', transition: 'all 0.3s ease', cursor: 'pointer',
                  boxShadow: dragOver ? '0 0 0 4px rgba(127,121,182,0.1)' : 'var(--shadow-sm)',
                  animation: 'fadeInUp 0.4s 0.08s ease forwards', opacity: 0,
                }}
              >
                <div style={{ width: '72px', height: '72px', borderRadius: '22px', margin: '0 auto 18px',
                  background: 'linear-gradient(135deg, #EEEDFA, #F5F4FA)', display: 'flex', alignItems: 'center', justifyContent: 'center',
                  fontSize: '32px', animation: 'float 4s ease-in-out infinite' }}>🖼️</div>
                <p style={{ fontWeight: 700, fontSize: '16px', color: '#2F2B6E', marginBottom: '6px' }}>Drop wound photos here</p>
                <p style={{ fontSize: '13px', color: '#8C8AAE' }}>or tap to choose — you can select up to {MAX_PHOTOS} at once</p>
              </div>
              <div style={{ marginTop: '12px', animation: 'fadeInUp 0.4s 0.15s ease forwards', opacity: 0 }}>
                <button onClick={() => cameraRef.current.click()} style={{ ...primaryBtn, width: '100%', borderRadius: '16px' }}>
                  📷 Take Photo with Camera
                </button>
              </div>
            </>
          ) : (
            /* ===== Selected photos ===== */
            <div style={{ animation: 'fadeInUp 0.4s ease forwards' }}>
              <div style={{ position: 'relative', borderRadius: '24px', overflow: 'hidden', boxShadow: '0 12px 40px rgba(47,43,110,0.12)', marginBottom: '12px' }}>
                {active && <img src={active.url} alt="Wound preview" style={{ width: '100%', height: '320px', objectFit: 'cover', display: 'block' }} />}
                {scanning && active && active.status === 'scanning' && (
                  <ScanOverlay key={active.id} label={items.length > 1 ? `PHOTO ${scanIndex + 1} OF ${items.length}` : ''} />
                )}
                {!scanning && (
                  <div style={{ position: 'absolute', top: '12px', right: '12px', background: 'rgba(0,0,0,0.5)', backdropFilter: 'blur(10px)',
                    borderRadius: '10px', padding: '6px 12px', color: '#fff', fontSize: '12px', fontWeight: 600 }}>
                    {items.length} photo{items.length > 1 ? 's' : ''} selected
                  </div>
                )}
              </div>

              {/* thumbnail strip */}
              <div style={{ display: 'flex', gap: '8px', overflowX: 'auto', paddingBottom: '6px', marginBottom: '12px' }}>
                {items.map((it, i) => {
                  const dot = statusDot(it);
                  const isActive = active && it.id === active.id;
                  return (
                    <div key={it.id} onClick={() => !scanning && setActiveId(it.id)} style={{
                      position: 'relative', width: '68px', height: '68px', flexShrink: 0, borderRadius: '14px', overflow: 'hidden',
                      cursor: scanning ? 'default' : 'pointer', outline: isActive ? '3px solid #7F79B6' : '1px solid #E8E7F0', outlineOffset: isActive ? '-3px' : '-1px',
                      opacity: scanning && it.status === 'ready' ? 0.55 : 1, transition: 'opacity 0.3s',
                    }}>
                      <img src={it.url} alt={`Photo ${i + 1}`} style={{ width: '100%', height: '100%', objectFit: 'cover' }} />
                      {!scanning && it.status !== 'done' && (
                        <button onClick={e => { e.stopPropagation(); removeItem(it.id); }} aria-label="Remove photo" style={{
                          position: 'absolute', top: '3px', right: '3px', width: '22px', height: '22px', padding: 0, borderRadius: '50%',
                          background: 'rgba(0,0,0,0.6)', color: '#fff', fontSize: '12px', lineHeight: '22px', border: 'none',
                        }}>✕</button>
                      )}
                      {dot && (
                        <span style={{ position: 'absolute', bottom: '4px', left: '4px', minWidth: '18px', height: '18px', borderRadius: '9px', padding: '0 4px',
                          background: dot.bg, color: '#fff', fontSize: '11px', fontWeight: 900, display: 'grid', placeItems: 'center',
                          boxShadow: it.status === 'scanning' ? '0 0 10px #22D3EE' : 'none', animation: it.status === 'scanning' ? 'pulse 1s infinite' : 'none' }}>
                          {dot.t}
                        </span>
                      )}
                    </div>
                  );
                })}
                {!scanning && items.length < MAX_PHOTOS && (
                  <>
                    <button onClick={() => fileRef.current.click()} title="Add from gallery" style={{
                      width: '68px', height: '68px', flexShrink: 0, borderRadius: '14px', border: '2px dashed #C9C6E6', background: '#fff',
                      color: '#7F79B6', fontSize: '22px', padding: 0, display: 'grid', placeItems: 'center' }}>＋</button>
                    <button onClick={() => cameraRef.current.click()} title="Take another photo" style={{
                      width: '68px', height: '68px', flexShrink: 0, borderRadius: '14px', border: '2px dashed #C9C6E6', background: '#fff',
                      fontSize: '22px', padding: 0, display: 'grid', placeItems: 'center' }}>📷</button>
                  </>
                )}
              </div>

              {notice && (
                <div style={{ marginBottom: '12px', padding: '10px 14px', borderRadius: '12px', background: '#FDEAEA', color: '#B42318', fontSize: '12.5px', fontWeight: 600, animation: 'scaleIn 0.3s ease' }}>
                  ⚠️ {notice}
                </div>
              )}

              <div style={{ display: 'flex', gap: '10px' }}>
                <button onClick={reset} disabled={scanning} style={{ ...softBtn, flex: 1 }}>Clear</button>
                <button onClick={analyzeAll} disabled={scanning} style={{ ...primaryBtn, flex: 2 }}>
                  {scanning ? (
                    <span style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '8px' }}>
                      <span style={{ width: '18px', height: '18px', border: '2px solid rgba(255,255,255,0.3)', borderTopColor: '#fff', borderRadius: '50%', display: 'inline-block', animation: 'spin 0.6s linear infinite' }} />
                      Analyzing {Math.min(doneCount + failed.length + 1, items.length)} of {items.length}…
                    </span>
                  ) : `🔬 Analyze ${items.length > 1 ? `${items.length} photos` : 'with AI'}`}
                </button>
              </div>
            </div>
          )}

          {/* Tips */}
          {!scanning && (
            <div style={{ marginTop: '24px', padding: '18px', borderRadius: '18px', background: 'rgba(127,121,182,0.06)',
              border: '1px solid rgba(127,121,182,0.08)', animation: 'fadeInUp 0.4s 0.22s ease forwards', opacity: 0 }}>
              <p style={{ fontWeight: 700, fontSize: '13px', color: '#2F2B6E', marginBottom: '10px' }}>📋 Photo Tips</p>
              {['Good lighting, avoid shadows', 'Include wound area with 2cm border', 'Keep camera steady & focused', 'Several angles of the same wound help your doctor'].map((t, i) => (
                <div key={i} style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '6px' }}>
                  <div style={{ width: '6px', height: '6px', borderRadius: '50%', background: '#7F79B6', flexShrink: 0 }} />
                  <p style={{ fontSize: '12px', color: '#666' }}>{t}</p>
                </div>
              ))}
            </div>
          )}
        </>
      ) : (
        /* ===== RESULTS ===== */
        <div style={{ animation: 'fadeInUp 0.5s ease forwards' }}>
          {items.length === 1 && ok.length === 1 ? (
            <ResultDetail result={ok[0].result} />
          ) : (
            <>
              {/* summary */}
              <div style={{
                background: worst ? riskColor[worst.result.risk_level] : '#8C8AAE', borderRadius: '24px', padding: '22px', color: '#fff',
                marginBottom: '16px', boxShadow: `0 12px 40px ${worst ? riskColor[worst.result.risk_level] : '#8C8AAE'}35`, position: 'relative', overflow: 'hidden',
              }}>
                <div style={{ position: 'absolute', top: '-30px', right: '-30px', width: '110px', height: '110px', borderRadius: '50%', background: 'rgba(255,255,255,0.1)' }} />
                <p style={{ fontSize: '12px', fontWeight: 700, opacity: 0.8, letterSpacing: '1px' }}>
                  {ok.length} OF {items.length} PHOTOS ANALYSED
                </p>
                {worst ? (
                  <>
                    <p style={{ fontSize: '15px', fontWeight: 700, marginTop: '10px', opacity: 0.9 }}>Highest risk found</p>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginTop: '2px' }}>
                      <span style={{ fontSize: '46px', fontWeight: 900, animation: 'countPop 0.6s ease forwards' }}>{Math.round(worst.result.risk_score * 100)}%</span>
                      <RiskBadge level={worst.result.risk_level} size="md" />
                    </div>
                    <p style={{ fontSize: '12px', opacity: 0.85, marginTop: '6px' }}>
                      Your doctor will review {ok.length > 1 ? 'all these photos' : 'this photo'} and send you a report.
                    </p>
                  </>
                ) : (
                  <p style={{ fontSize: '15px', fontWeight: 700, marginTop: '10px' }}>None of the photos could be analysed — see the reasons below.</p>
                )}
              </div>

              {/* per-photo results */}
              <div style={{ display: 'flex', flexDirection: 'column', gap: '10px', marginBottom: '16px' }}>
                {items.map((it, i) => <ResultCard key={it.id} item={it} index={i} onRetry={() => retry(it.id)} />)}
              </div>
            </>
          )}

          <div style={{ display: 'flex', gap: '10px', animation: 'fadeInUp 0.5s 0.3s ease forwards', opacity: 0 }}>
            <button onClick={reset} style={{ ...softBtn, flex: 1 }}>📸 New Scan</button>
            <button onClick={() => { window.location.hash = '#/history'; }} style={{ ...primaryBtn, flex: 1 }}>📊 View History</button>
          </div>
        </div>
      )}
    </div>
  );
}

export default UploadPage;
