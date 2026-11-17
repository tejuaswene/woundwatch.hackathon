import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { getStats, getPatients } from '../api';
import { ScanOrb3D } from '../three/Scene3D';
import TiltCard from '../three/TiltCard';
import useCountUp from '../hooks/useCountUp';

const riskColor = { RED: '#D64545', YELLOW: '#E89B2C', GREEN: '#2BA84A', NONE: '#8C8AAE' };
const riskBg = { RED: '#FDEAEA', YELLOW: '#FFF5E5', GREEN: '#E8F8EC', NONE: '#F5F4F8' };
const riskLabel = { RED: 'High risk', YELLOW: 'Monitor', GREEN: 'Healing', NONE: 'No scans' };

function StatCard({ label, value, icon, color, glow, hint, onClick, delay }) {
  const n = useCountUp(value);
  return (
    <TiltCard onClick={onClick} max={9} style={{
      background: '#fff', padding: 22, boxShadow: '0 4px 20px rgba(47,43,110,0.06)',
      border: '1px solid #EEEDF6', animation: `fadeInUp 0.6s ${delay}s ease both`, overflow: 'hidden',
    }}>
      <div style={{ position: 'absolute', right: -30, top: -30, width: 110, height: 110, borderRadius: '50%',
        background: `radial-gradient(circle, ${glow} 0%, transparent 70%)` }} />
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', position: 'relative' }}>
        <div>
          <p style={{ fontSize: 12.5, color: '#8C8AAE', fontWeight: 600, marginBottom: 10 }}>{label}</p>
          <p style={{ fontSize: 34, fontWeight: 900, color, letterSpacing: '-0.03em', lineHeight: 1 }}>{n}</p>
          {hint && <p style={{ fontSize: 11.5, color: '#A3A1C2', marginTop: 8 }}>{hint}</p>}
        </div>
        <div style={{ width: 46, height: 46, borderRadius: 14, display: 'grid', placeItems: 'center', fontSize: 22,
          background: `linear-gradient(135deg, ${glow}, #fff)`, boxShadow: `0 8px 20px ${glow}` }}>{icon}</div>
      </div>
    </TiltCard>
  );
}

function DashboardPage({ doctor }) {
  const [stats, setStats] = useState(null);
  const [patients, setPatients] = useState([]);
  const [loaded, setLoaded] = useState(false);
  const [error, setError] = useState('');
  const [barReady, setBarReady] = useState(false);
  const nav = useNavigate();

  useEffect(() => {
    Promise.all([getStats(), getPatients()])
      .then(([s, p]) => { setStats(s.data); setPatients(p.data || []); })
      .catch(() => setError('Could not load data — is the backend running on port 8000?'))
      .finally(() => { setLoaded(true); setTimeout(() => setBarReady(true), 150); });
  }, []);

  const red = patients.filter(p => p.latest_risk === 'RED');
  const yellow = patients.filter(p => p.latest_risk === 'YELLOW');
  const worst = red.length ? 'RED' : yellow.length ? 'YELLOW' : patients.length ? 'GREEN' : null;
  const totalScans = stats ? (stats.total_scans ?? stats.total_photos ?? 0) : 0;
  const pending = stats?.unreviewed ?? 0;

  const hour = new Date().getHours();
  const greet = hour < 12 ? 'Good morning' : hour < 17 ? 'Good afternoon' : 'Good evening';
  const headline = red.length
    ? `${red.length} patient${red.length > 1 ? 's' : ''} at high risk need${red.length > 1 ? '' : 's'} your attention`
    : pending ? `${pending} wound photo${pending > 1 ? 's' : ''} waiting for your review` : 'All patients are stable right now';

  return (
    <div>
      {/* ===== 3D hero ===== */}
      <div style={{
        position: 'relative', borderRadius: 28, overflow: 'hidden', marginBottom: 24, minHeight: 250,
        background: 'radial-gradient(600px 300px at 85% 50%, rgba(34,211,238,0.16), transparent 70%), radial-gradient(500px 300px at 10% 0%, rgba(139,92,246,0.35), transparent 70%), linear-gradient(135deg, #0C0B2A 0%, #1B1650 100%)',
        boxShadow: '0 24px 60px rgba(27,22,80,0.35)', animation: 'fadeInUp 0.6s ease both',
      }}>
        {/* HUD grid */}
        <div style={{ position: 'absolute', inset: 0, opacity: 0.35, pointerEvents: 'none',
          backgroundImage: 'linear-gradient(rgba(255,255,255,0.05) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,0.05) 1px, transparent 1px)',
          backgroundSize: '32px 32px', maskImage: 'linear-gradient(90deg, transparent, #000 40%, #000)', WebkitMaskImage: 'linear-gradient(90deg, transparent, #000 40%, #000)' }} />

        <div style={{ position: 'relative', display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 20, padding: '34px 38px' }}>
          <div style={{ maxWidth: 560, color: '#fff', zIndex: 1 }}>
            <p style={{ fontSize: 13, fontWeight: 700, color: '#67E8F9', letterSpacing: '0.06em' }}>
              {greet.toUpperCase()}, {(doctor.name || '').toUpperCase()}
            </p>
            <h1 style={{ color: '#fff', fontSize: 30, lineHeight: 1.15, fontWeight: 900, letterSpacing: '-0.03em', marginTop: 10 }}>
              {loaded ? headline : 'Loading today’s overview…'}
            </h1>
            <p style={{ color: 'rgba(226,232,255,0.65)', fontSize: 14, marginTop: 10 }}>
              {doctor.hospital} · {new Date().toLocaleDateString('en-IN', { weekday: 'long', day: 'numeric', month: 'long' })}
            </p>
            <div style={{ display: 'flex', gap: 10, marginTop: 22, flexWrap: 'wrap' }}>
              <button onClick={() => nav('/patients')} style={{ background: 'linear-gradient(135deg, #06B6D4, #7C3AED)', boxShadow: '0 10px 26px rgba(124,58,237,0.4)' }}>
                Review patients →
              </button>
              <button onClick={() => nav('/alerts')} style={{ background: 'rgba(255,255,255,0.08)', border: '1px solid rgba(255,255,255,0.16)' }}>
                🚨 Open alerts
              </button>
            </div>
          </div>

          {/* 3D AI orb, coloured by the worst current risk */}
          <div style={{ position: 'relative', width: 260, height: 220, flexShrink: 0 }}>
            <ScanOrb3D level={worst} style={{ position: 'absolute', inset: -20 }} />
            {worst && (
              <div style={{ position: 'absolute', bottom: 0, left: '50%', transform: 'translateX(-50%)', padding: '5px 12px', borderRadius: 999,
                fontSize: 11, fontWeight: 800, letterSpacing: '0.05em', color: '#fff', whiteSpace: 'nowrap',
                background: 'rgba(255,255,255,0.08)', border: `1px solid ${riskColor[worst]}`, backdropFilter: 'blur(6px)' }}>
                AI WATCH · {worst === 'RED' ? 'ALERT' : worst === 'YELLOW' ? 'MONITORING' : 'STABLE'}
              </div>
            )}
          </div>
        </div>
      </div>

      {error && (
        <div style={{ background: '#FDEAEA', color: '#B42318', padding: '12px 16px', borderRadius: 14, marginBottom: 20, fontWeight: 600, fontSize: 13 }}>{error}</div>
      )}

      {/* ===== Stat cards ===== */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: 16, marginBottom: 24 }}>
        <StatCard delay={0.05} label="Total patients" value={stats?.total_patients ?? 0} icon="👥" color="#2F2B6E" glow="rgba(127,121,182,0.28)" onClick={() => nav('/patients')} />
        <StatCard delay={0.1} label="Wound scans" value={totalScans} icon="📷" color="#0E7490" glow="rgba(34,211,238,0.28)" />
        <StatCard delay={0.15} label="High-risk scans" value={stats?.red ?? 0} icon="🚨" color="#D64545" glow="rgba(214,69,69,0.22)" hint={stats ? `${stats.alert_rate}% of all scans` : ''} />
        <StatCard delay={0.2} label="Pending review" value={pending} icon="📋" color="#E89B2C" glow="rgba(232,155,44,0.25)" onClick={() => nav('/patients')} hint="Photos without a doctor review" />
      </div>

      {/* ===== Risk distribution ===== */}
      {stats && totalScans > 0 && (
        <div style={{ background: '#fff', borderRadius: 22, padding: 24, marginBottom: 24, border: '1px solid #EEEDF6',
          boxShadow: '0 4px 20px rgba(47,43,110,0.05)', animation: 'fadeInUp 0.6s 0.25s ease both' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
            <p style={{ fontWeight: 800, color: '#2F2B6E', fontSize: 15 }}>Risk distribution · all scans</p>
            <p style={{ fontSize: 12, color: '#8C8AAE' }}>{totalScans} scans</p>
          </div>
          <div style={{ display: 'flex', gap: 4, height: 16, borderRadius: 10, overflow: 'hidden', background: '#F2F1F8' }}>
            {[['GREEN', stats.green], ['YELLOW', stats.yellow], ['RED', stats.red]].map(([k, v]) => v > 0 && (
              <div key={k} title={`${riskLabel[k]}: ${v}`} style={{
                width: barReady ? `${(v / totalScans) * 100}%` : '0%', background: `linear-gradient(90deg, ${riskColor[k]}cc, ${riskColor[k]})`,
                borderRadius: 10, transition: 'width 1.2s cubic-bezier(0.16,1,0.3,1)',
              }} />
            ))}
          </div>
          <div style={{ display: 'flex', gap: 22, marginTop: 12 }}>
            {[['GREEN', stats.green], ['YELLOW', stats.yellow], ['RED', stats.red]].map(([k, v]) => (
              <span key={k} style={{ fontSize: 12.5, color: '#55537A', display: 'flex', alignItems: 'center', gap: 7 }}>
                <span style={{ width: 9, height: 9, borderRadius: 3, background: riskColor[k] }} />
                {riskLabel[k]} <b style={{ color: '#2F2B6E' }}>{v}</b>
              </span>
            ))}
          </div>
        </div>
      )}

      {/* ===== Attention list ===== */}
      <div style={{ background: '#fff', borderRadius: 22, padding: 24, border: '1px solid #EEEDF6',
        boxShadow: '0 4px 20px rgba(47,43,110,0.05)', animation: 'fadeInUp 0.6s 0.3s ease both' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 14 }}>
          <div>
            <p style={{ fontWeight: 800, color: '#2F2B6E', fontSize: 16 }}>Patients requiring attention</p>
            <p style={{ fontSize: 12, color: '#8C8AAE', marginTop: 2 }}>Sorted by latest AI risk</p>
          </div>
          <button onClick={() => nav('/patients')} style={{ background: '#F5F4FA', color: '#2F2B6E', fontSize: 13, padding: '8px 16px' }}>View all</button>
        </div>

        {!loaded ? (
          [1, 2, 3].map(i => <div key={i} className="skeleton" style={{ height: 54, marginBottom: 8 }} />)
        ) : patients.length === 0 ? (
          <p style={{ color: '#8C8AAE', fontSize: 14, textAlign: 'center', padding: 30 }}>No patients registered yet</p>
        ) : (
          <table style={{ width: '100%', borderCollapse: 'separate', borderSpacing: '0 6px' }}>
            <thead>
              <tr>
                {['Patient', 'Surgery', 'AI risk', 'Score', 'Review', 'Last scan'].map(h => (
                  <th key={h} style={{ padding: '6px 14px', textAlign: 'left', fontSize: 11.5, color: '#8C8AAE', fontWeight: 700, letterSpacing: '0.03em' }}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {patients.slice(0, 8).map((p, i) => (
                <tr key={p.phone} onClick={() => nav(`/patient/${p.phone}`)} className="ww-row"
                  style={{ cursor: 'pointer', animation: `fadeInUp 0.45s ${0.35 + i * 0.04}s ease both` }}>
                  <td style={{ padding: '12px 14px', borderRadius: '14px 0 0 14px' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                      <div style={{ width: 36, height: 36, borderRadius: 12, display: 'grid', placeItems: 'center', fontWeight: 800, fontSize: 14,
                        color: riskColor[p.latest_risk], background: riskBg[p.latest_risk] }}>{(p.name || p.phone || '?')[0].toUpperCase()}</div>
                      <div>
                        <p style={{ fontWeight: 700, fontSize: 14, color: '#1F1D3D' }}>{p.name || p.phone}</p>
                        <p style={{ fontSize: 12, color: '#8C8AAE' }}>{p.age ? `${p.age} yrs` : ''}{p.gender ? ` · ${p.gender}` : ''}</p>
                      </div>
                    </div>
                  </td>
                  <td style={{ padding: '12px 14px', fontSize: 13, color: '#55537A' }}>{p.surgery_type || '—'}</td>
                  <td style={{ padding: '12px 14px' }}>
                    <span style={{ display: 'inline-flex', alignItems: 'center', gap: 6, background: riskBg[p.latest_risk], color: riskColor[p.latest_risk],
                      padding: '4px 11px', borderRadius: 999, fontSize: 12, fontWeight: 800 }}>
                      <span style={{ width: 7, height: 7, borderRadius: '50%', background: riskColor[p.latest_risk],
                        boxShadow: p.latest_risk === 'RED' ? `0 0 8px ${riskColor.RED}` : 'none' }} />
                      {riskLabel[p.latest_risk] || p.latest_risk}
                    </span>
                  </td>
                  <td style={{ padding: '12px 14px', fontSize: 14, fontWeight: 800, color: riskColor[p.latest_risk] }}>
                    {p.latest_risk === 'NONE' ? '—' : `${Math.round((p.latest_score || 0) * 100)}%`}
                  </td>
                  <td style={{ padding: '12px 14px' }}>
                    {p.unreviewed > 0
                      ? <span style={{ background: '#FFF5E5', color: '#B9771B', padding: '3px 10px', borderRadius: 999, fontSize: 12, fontWeight: 700 }}>{p.unreviewed} pending</span>
                      : <span style={{ fontSize: 12, color: '#2BA84A', fontWeight: 600 }}>✓ Up to date</span>}
                  </td>
                  <td style={{ padding: '12px 14px', fontSize: 12, color: '#8C8AAE', borderRadius: '0 14px 14px 0' }}>
                    {p.last_scan ? new Date(p.last_scan).toLocaleDateString('en-IN', { day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit' }) : '—'}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      <style>{`
        .ww-row td { background: #FAFAFD; transition: background 0.2s, transform 0.2s; }
        .ww-row:hover td { background: #F1EFFB; }
      `}</style>
    </div>
  );
}

export default DashboardPage;
