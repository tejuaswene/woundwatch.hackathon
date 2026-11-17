import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { getPatients } from '../api';
import TiltCard from '../three/TiltCard';

const riskColor = { RED: '#D64545', YELLOW: '#E89B2C', GREEN: '#2BA84A', NONE: '#8C8AAE' };
const riskBg = { RED: '#FDEAEA', YELLOW: '#FFF5E5', GREEN: '#E8F8EC', NONE: '#F5F4F8' };
const riskLabel = { RED: 'High risk', YELLOW: 'Monitor', GREEN: 'Healing', NONE: 'No scans' };
const FILTERS = [
  { key: 'ALL', label: 'All' }, { key: 'RED', label: 'High risk' }, { key: 'YELLOW', label: 'Monitor' }, { key: 'GREEN', label: 'Healing' },
];

function PatientsPage() {
  const [patients, setPatients] = useState([]);
  const [loaded, setLoaded] = useState(false);
  const [filter, setFilter] = useState('ALL');
  const [search, setSearch] = useState('');
  const nav = useNavigate();

  useEffect(() => {
    getPatients().then(res => setPatients(res.data || [])).catch(() => {}).finally(() => setLoaded(true));
  }, []);

  const counts = patients.reduce((a, p) => ({ ...a, [p.latest_risk]: (a[p.latest_risk] || 0) + 1 }), {});
  const q = search.trim().toLowerCase();
  const filtered = patients.filter(p => {
    if (filter !== 'ALL' && p.latest_risk !== filter) return false;
    if (q && !((p.name || '').toLowerCase().includes(q) || (p.phone || '').includes(q) || (p.surgery_type || '').toLowerCase().includes(q))) return false;
    return true;
  });

  return (
    <div>
      <div style={{ display: 'flex', alignItems: 'flex-end', justifyContent: 'space-between', marginBottom: 22, animation: 'fadeInUp 0.5s ease both' }}>
        <div>
          <h1 style={{ fontSize: 30, fontWeight: 900, letterSpacing: '-0.03em' }}>Patients</h1>
          <p style={{ color: '#8C8AAE', fontSize: 14, marginTop: 4 }}>Sorted by latest AI risk — open a patient to review their photos</p>
        </div>
      </div>

      {/* Filters */}
      <div style={{ display: 'flex', gap: 12, marginBottom: 22, alignItems: 'center', flexWrap: 'wrap', animation: 'fadeInUp 0.5s 0.05s ease both' }}>
        <div style={{ position: 'relative', flex: '0 1 340px' }}>
          <span style={{ position: 'absolute', left: 14, top: '50%', transform: 'translateY(-50%)', fontSize: 15, opacity: 0.5 }}>🔍</span>
          <input value={search} onChange={e => setSearch(e.target.value)} placeholder="Search name, phone or surgery…" style={{ paddingLeft: 40 }} />
        </div>
        <div style={{ display: 'flex', gap: 4, background: '#EEEDF6', padding: 4, borderRadius: 14 }}>
          {FILTERS.map(f => {
            const on = filter === f.key;
            const n = f.key === 'ALL' ? patients.length : counts[f.key] || 0;
            return (
              <button key={f.key} onClick={() => setFilter(f.key)} style={{
                padding: '8px 14px', fontSize: 12.5, borderRadius: 11,
                background: on ? (f.key === 'ALL' ? '#2F2B6E' : riskColor[f.key]) : 'transparent',
                color: on ? '#fff' : '#55537A', boxShadow: on ? '0 6px 16px rgba(47,43,110,0.18)' : 'none',
              }}>{f.label} <span style={{ opacity: 0.7, marginLeft: 4 }}>{n}</span></button>
            );
          })}
        </div>
        <span style={{ fontSize: 13, color: '#8C8AAE', marginLeft: 'auto' }}>{filtered.length} shown</span>
      </div>

      {!loaded ? (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(300px, 1fr))', gap: 16 }}>
          {[1, 2, 3, 4, 5, 6].map(i => <div key={i} className="skeleton" style={{ height: 170, borderRadius: 22 }} />)}
        </div>
      ) : filtered.length === 0 ? (
        <div style={{ textAlign: 'center', padding: 60, color: '#8C8AAE', background: '#fff', borderRadius: 22 }}>
          <p style={{ fontSize: 40 }}>🗂️</p>
          <p style={{ fontWeight: 700, marginTop: 8 }}>No patients match</p>
        </div>
      ) : (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(300px, 1fr))', gap: 16 }}>
          {filtered.map((p, i) => {
            const c = riskColor[p.latest_risk] || riskColor.NONE;
            const score = Math.round((p.latest_score || 0) * 100);
            return (
              <TiltCard key={p.phone} onClick={() => nav(`/patient/${p.phone}`)} max={8} radius={22}
                glareColor={p.latest_risk === 'RED' ? '255,200,200' : '255,255,255'}
                style={{
                  background: '#fff', padding: 20, border: '1px solid #EEEDF6',
                  boxShadow: p.latest_risk === 'RED' ? '0 10px 30px rgba(214,69,69,0.14)' : '0 4px 18px rgba(47,43,110,0.06)',
                  animation: `fadeInUp 0.5s ${0.08 + i * 0.04}s ease both`,
                }}>
                {/* risk accent */}
                <div style={{ position: 'absolute', left: 0, top: 18, bottom: 18, width: 4, borderRadius: 4, background: c,
                  boxShadow: p.latest_risk === 'RED' ? `0 0 12px ${c}` : 'none' }} />
                <div style={{ display: 'flex', alignItems: 'center', gap: 14 }}>
                  <div style={{ width: 46, height: 46, borderRadius: 15, display: 'grid', placeItems: 'center', fontSize: 18, fontWeight: 900,
                    color: c, background: riskBg[p.latest_risk] || riskBg.NONE, transform: 'translateZ(30px)' }}>
                    {(p.name || p.phone || '?')[0].toUpperCase()}
                  </div>
                  <div style={{ minWidth: 0, flex: 1 }}>
                    <p style={{ fontWeight: 800, fontSize: 16, color: '#1F1D3D', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>{p.name || 'Unnamed patient'}</p>
                    <p style={{ fontSize: 12, color: '#8C8AAE' }}>{p.phone}{p.age ? ` · ${p.age} yrs` : ''}</p>
                  </div>
                  {/* mini score ring */}
                  <svg width="50" height="50" viewBox="0 0 50 50" style={{ flexShrink: 0 }}>
                    <circle cx="25" cy="25" r="20" fill="none" stroke="#F0EFF7" strokeWidth="5" />
                    {p.latest_risk !== 'NONE' && (
                      <circle cx="25" cy="25" r="20" fill="none" stroke={c} strokeWidth="5" strokeLinecap="round"
                        strokeDasharray={`${(score / 100) * 125.7} 125.7`} transform="rotate(-90 25 25)" />
                    )}
                    <text x="25" y="29" textAnchor="middle" fontSize="12" fontWeight="800" fill={c}>{p.latest_risk === 'NONE' ? '—' : score}</text>
                  </svg>
                </div>
                <div style={{ display: 'flex', gap: 8, marginTop: 16, flexWrap: 'wrap' }}>
                  <span style={{ fontSize: 12, fontWeight: 700, padding: '4px 10px', borderRadius: 999, color: c, background: riskBg[p.latest_risk] || riskBg.NONE }}>
                    {riskLabel[p.latest_risk] || p.latest_risk}
                  </span>
                  <span style={{ fontSize: 12, padding: '4px 10px', borderRadius: 999, background: '#F5F4FA', color: '#55537A' }}>🩹 {p.surgery_type || 'Surgery n/a'}</span>
                  <span style={{ fontSize: 12, padding: '4px 10px', borderRadius: 999, background: '#F5F4FA', color: '#55537A' }}>📷 {p.total_photos}</span>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: 14, paddingTop: 12, borderTop: '1px dashed #ECEBF5' }}>
                  {p.unreviewed > 0
                    ? <span style={{ fontSize: 12, fontWeight: 700, color: '#B9771B' }}>● {p.unreviewed} photo{p.unreviewed > 1 ? 's' : ''} to review</span>
                    : <span style={{ fontSize: 12, fontWeight: 600, color: '#2BA84A' }}>✓ All reviewed</span>}
                  <span style={{ fontSize: 11.5, color: '#A3A1C2' }}>
                    {p.last_scan ? new Date(p.last_scan).toLocaleDateString('en-IN', { day: 'numeric', month: 'short' }) : 'No scans'}
                  </span>
                </div>
              </TiltCard>
            );
          })}
        </div>
      )}
    </div>
  );
}

export default PatientsPage;
