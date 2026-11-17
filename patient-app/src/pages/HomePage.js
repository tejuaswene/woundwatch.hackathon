import React, { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { getHistory } from '../api';
import RiskBadge from '../components/RiskBadge';
import { ScanOrb3D } from '../three/Scene3D';
import TiltCard from '../three/TiltCard';

/* Animated Counter Hook */
function useAnimatedCounter(target, duration = 1200) {
  const [val, setVal] = useState(0);
  const started = useRef(false);
  useEffect(() => {
    if (target == null || started.current) return;
    started.current = true;
    const start = performance.now();
    const tick = (now) => {
      const elapsed = now - start;
      const progress = Math.min(elapsed / duration, 1);
      const eased = 1 - Math.pow(1 - progress, 3);
      setVal(Math.round(eased * target));
      if (progress < 1) requestAnimationFrame(tick);
    };
    requestAnimationFrame(tick);
  }, [target, duration]);
  return val;
}

/* Circular Progress Ring */
function ProgressRing({ value, color, size = 90, strokeWidth = 7, hideLabel = false }) {
  const r = (size - strokeWidth) / 2;
  const circ = 2 * Math.PI * r;
  const offset = circ - (value / 100) * circ;
  return (
    <svg width={size} height={size} style={{ transform: 'rotate(-90deg)' }}>
      <circle cx={size/2} cy={size/2} r={r} fill="none"
        stroke="rgba(0,0,0,0.07)" strokeWidth={strokeWidth} />
      <circle cx={size/2} cy={size/2} r={r} fill="none"
        stroke={color} strokeWidth={strokeWidth}
        strokeDasharray={circ} strokeDashoffset={offset}
        strokeLinecap="round"
        style={{ transition: 'stroke-dashoffset 1.5s cubic-bezier(0.16, 1, 0.3, 1)' }}
      />
      {!hideLabel && (
        <text x={size/2} y={size/2} textAnchor="middle" dominantBaseline="central"
          style={{ transform: 'rotate(90deg)', transformOrigin: 'center', fontSize: `${size * 0.26}px`, fontWeight: 900, fill: color }}>
          {value}%
        </text>
      )}
    </svg>
  );
}

function HomePage({ user, onLogout }) {
  const nav = useNavigate();
  const [latest, setLatest] = useState(null);
  const [totalScans, setTotalScans] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getHistory(user.phone).then(res => {
      const photos = res.data || [];
      setTotalScans(photos.length);
      if (photos.length > 0) setLatest(photos[0]);
      setLoading(false);
    }).catch(() => setLoading(false));
  }, [user.phone]);

  const hour = new Date().getHours();
  const greeting = hour < 12 ? 'Good Morning' : hour < 17 ? 'Good Afternoon' : 'Good Evening';
  const greetIcon = hour < 12 ? '🌅' : hour < 17 ? '☀️' : '🌙';

  const riskColor = { GREEN: '#2BA84A', YELLOW: '#E89B2C', RED: '#D64545' };
  const riskBg = { GREEN: 'linear-gradient(135deg, #E8F8EC, #D0F0D8)', YELLOW: 'linear-gradient(135deg, #FFF5E5, #FFECC8)', RED: 'linear-gradient(135deg, #FDEAEA, #FDDEDE)' };

  const riskVal = latest ? Math.round(latest.risk_score * 100) : 0;
  const animatedRisk = useAnimatedCounter(loading ? null : riskVal);
  const animatedScans = useAnimatedCounter(loading ? null : totalScans);

  const actions = [
    { icon: '📸', label: 'Scan Wound', desc: 'AI Analysis', path: '/upload', gradient: 'linear-gradient(135deg, #2F2B6E, #7F79B6)' },
    { icon: '📊', label: 'History', desc: 'Past Scans', path: '/history', gradient: 'linear-gradient(135deg, #7F79B6, #A78BFA)' },
    { icon: '💬', label: 'AI Chat', desc: 'Ask Questions', path: '/chat', gradient: 'linear-gradient(135deg, #2BA84A, #22C55E)' },
    { icon: '🔔', label: 'Alerts', desc: 'Notifications', path: '/notifications', gradient: 'linear-gradient(135deg, #E89B2C, #F59E0B)' },
  ];

  const tips = [
    { icon: '🧼', text: 'Keep the wound area clean and dry. Wash hands before touching.' },
    { icon: '📷', text: 'Take photos in consistent lighting for accurate AI analysis.' },
    { icon: '💊', text: 'Take prescribed antibiotics on schedule. Never skip doses.' },
    { icon: '🩹', text: 'Change dressings as recommended. Watch for unusual discharge.' },
    { icon: '🌡️', text: 'Monitor for fever above 100.4°F — it may signal infection.' },
  ];
  const todayTip = tips[new Date().getDate() % tips.length];

  return (
    <div style={{ padding: '20px 16px 100px', maxWidth: '480px', margin: '0 auto' }}>
      {/* Greeting */}
      <div style={{ marginBottom: '24px', animation: 'fadeInUp 0.5s ease forwards', position: 'relative' }}>
        {onLogout && (
          <button
            onClick={() => { if (window.confirm('Log out of WoundWatch?')) onLogout(); }}
            title="Log out"
            style={{
              position: 'absolute', top: 0, right: 0, padding: '8px 14px', borderRadius: '12px',
              background: '#fff', color: '#7F79B6', fontSize: '12px', fontWeight: 700,
              border: '1px solid #E8E7F0', boxShadow: '0 2px 8px rgba(47,43,110,0.06)', cursor: 'pointer',
            }}
          >
            ⎋ Logout
          </button>
        )}
        <p style={{ fontSize: '14px', color: '#8C8AAE', fontWeight: 500 }}>
          {greetIcon} {greeting}
        </p>
        <h1 style={{
          fontSize: '28px', fontWeight: 900, letterSpacing: '-0.03em', marginTop: '4px',
          background: 'linear-gradient(135deg, #2F2B6E 0%, #7F79B6 50%, #2BA84A 100%)',
          backgroundSize: '200% 200%', animation: 'gradientShift 4s ease infinite',
          WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent', backgroundClip: 'text',
        }}>
          {user.name || 'Patient'}
        </h1>
      </div>

      {/* Empty state — 3D AI orb invites the first scan */}
      {!loading && !latest && (
        <div onClick={() => nav('/upload')} style={{
          position: 'relative', borderRadius: '28px', overflow: 'hidden', marginBottom: '20px', cursor: 'pointer',
          background: 'radial-gradient(300px 200px at 50% 40%, rgba(34,211,238,0.18), transparent 70%), linear-gradient(160deg, #0C0B2A, #1B1650)',
          padding: '22px', color: '#fff', textAlign: 'center', boxShadow: '0 18px 44px rgba(27,22,80,0.35)',
          animation: 'fadeInUp 0.5s 0.08s ease forwards', opacity: 0,
        }}>
          <div style={{ position: 'relative', height: '190px' }}>
            <ScanOrb3D level={null} style={{ position: 'absolute', inset: 0 }} />
          </div>
          <p style={{ fontWeight: 800, fontSize: '18px' }}>Start your first AI wound scan</p>
          <p style={{ fontSize: '12.5px', color: 'rgba(226,232,255,0.65)', marginTop: '4px' }}>One photo a day helps catch infection early</p>
          <div style={{ display: 'inline-block', marginTop: '14px', padding: '10px 18px', borderRadius: '12px', fontWeight: 700, fontSize: '13px',
            background: 'linear-gradient(135deg, #06B6D4, #7C3AED)', boxShadow: '0 10px 24px rgba(124,58,237,0.4)' }}>📸 Scan now</div>
        </div>
      )}

      {/* Risk Status Card — 3D tilt + live 3D AI orb */}
      {!loading && latest && (
        <TiltCard max={7} radius={24} style={{
          background: riskBg[latest.risk_level] || '#F5F4FA',
          padding: '22px 18px 22px 24px',
          marginBottom: '20px',
          border: `2px solid ${riskColor[latest.risk_level]}25`,
          boxShadow: `0 12px 40px ${riskColor[latest.risk_level]}22`,
          animation: 'fadeInUp 0.5s 0.08s ease forwards', opacity: 0,
        }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <div style={{ position: 'relative', zIndex: 1 }}>
              <p style={{ fontSize: '12px', fontWeight: 600, color: '#8C8AAE', textTransform: 'uppercase', letterSpacing: '0.5px' }}>
                Current Status
              </p>
              <div style={{ display: 'flex', alignItems: 'baseline', gap: '4px', marginTop: '8px' }}>
                <span style={{
                  fontSize: '44px', fontWeight: 900, color: riskColor[latest.risk_level],
                  animation: 'countPop 0.6s 0.5s ease forwards', opacity: 0,
                  transformOrigin: 'left bottom',
                }}>{animatedRisk}</span>
                <span style={{ fontSize: '18px', fontWeight: 700, color: riskColor[latest.risk_level], opacity: 0.7 }}>%</span>
              </div>
              <RiskBadge level={latest.risk_level} size="md" />
              <p style={{ fontSize: '11px', color: '#8C8AAE', marginTop: '8px' }}>
                AI screening · not a diagnosis
              </p>
            </div>
            {/* 3D AI orb coloured by risk, with the score ring around it */}
            <div style={{ position: 'relative', width: '128px', height: '128px', flexShrink: 0 }}>
              <div style={{
                position: 'absolute', inset: '9px', borderRadius: '50%', overflow: 'hidden',
                background: 'radial-gradient(circle at 50% 40%, #1E1A5A 0%, #0A0A22 75%)',
                boxShadow: `inset 0 0 18px rgba(0,0,0,0.6), 0 10px 26px ${riskColor[latest.risk_level]}55`,
              }}>
                <ScanOrb3D level={latest.risk_level} style={{ position: 'absolute', inset: '-18px' }} />
              </div>
              <div style={{ position: 'absolute', inset: 0, pointerEvents: 'none' }}>
                <ProgressRing value={animatedRisk} color={riskColor[latest.risk_level]} size={128} strokeWidth={5} hideLabel />
              </div>
            </div>
          </div>
        </TiltCard>
      )}

      {/* Stats Row */}
      {!loading && (
        <div style={{
          display: 'flex', gap: '10px', marginBottom: '20px',
          animation: 'fadeInUp 0.5s 0.15s ease forwards', opacity: 0,
        }}>
          <div style={{
            flex: 1, background: '#fff', borderRadius: '18px', padding: '16px',
            textAlign: 'center', boxShadow: '0 2px 12px rgba(47,43,110,0.06)',
            transition: 'transform 0.3s ease',
          }}
          onMouseEnter={e => e.currentTarget.style.transform = 'translateY(-3px)'}
          onMouseLeave={e => e.currentTarget.style.transform = 'none'}
          >
            <p style={{ fontSize: '28px', fontWeight: 900, color: '#2F2B6E' }}>{animatedScans}</p>
            <p style={{ fontSize: '11px', color: '#8C8AAE', fontWeight: 600 }}>Total Scans</p>
          </div>
          <div style={{
            flex: 1, background: '#fff', borderRadius: '18px', padding: '16px',
            textAlign: 'center', boxShadow: '0 2px 12px rgba(47,43,110,0.06)',
            transition: 'transform 0.3s ease',
          }}
          onMouseEnter={e => e.currentTarget.style.transform = 'translateY(-3px)'}
          onMouseLeave={e => e.currentTarget.style.transform = 'none'}
          >
            <p style={{ fontSize: '28px', fontWeight: 900, color: '#7F79B6' }}>
              {latest ? new Date(latest.uploaded_at).toLocaleDateString('en-IN', { day: 'numeric', month: 'short' }) : '--'}
            </p>
            <p style={{ fontSize: '11px', color: '#8C8AAE', fontWeight: 600 }}>Last Scan</p>
          </div>
        </div>
      )}

      {/* Quick Actions — 3D Tilt Cards */}
      <div style={{ marginBottom: '20px' }}>
        <p style={{ fontWeight: 700, fontSize: '15px', color: '#2F2B6E', marginBottom: '12px',
          animation: 'fadeInUp 0.5s 0.2s ease forwards', opacity: 0 }}>
          Quick Actions
        </p>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
          {actions.map((a, i) => (
            <TiltCard key={a.path} onClick={() => nav(a.path)} max={12} radius={20} style={{
              background: a.gradient, padding: '20px',
              color: '#fff', overflow: 'hidden',
              boxShadow: '0 6px 24px rgba(47,43,110,0.15)',
              animation: `fadeInUp 0.5s ${0.25 + i * 0.06}s ease forwards`, opacity: 0,
            }}>
              {/* Decorative circle */}
              <div style={{
                position: 'absolute', top: '-12px', right: '-12px',
                width: '56px', height: '56px', borderRadius: '50%',
                background: 'rgba(255,255,255,0.1)',
              }} />
              <div style={{
                position: 'absolute', bottom: '-20px', left: '-8px',
                width: '40px', height: '40px', borderRadius: '50%',
                background: 'rgba(255,255,255,0.06)',
              }} />
              <span style={{ fontSize: '28px', display: 'block', marginBottom: '10px' }}>{a.icon}</span>
              <p style={{ fontWeight: 800, fontSize: '15px', letterSpacing: '-0.01em' }}>{a.label}</p>
              <p style={{ fontSize: '11px', opacity: 0.65, fontWeight: 500, marginTop: '2px' }}>{a.desc}</p>
            </TiltCard>
          ))}
        </div>
      </div>

      {/* AI Tip of the Day */}
      <div style={{
        background: '#fff', borderRadius: '20px', padding: '18px 20px',
        boxShadow: '0 2px 12px rgba(47,43,110,0.06)',
        display: 'flex', gap: '14px', alignItems: 'center',
        animation: 'fadeInUp 0.5s 0.5s ease forwards', opacity: 0,
        border: '1px solid rgba(127,121,182,0.08)',
        transition: 'transform 0.3s ease, box-shadow 0.3s ease',
      }}
      onMouseEnter={e => { e.currentTarget.style.transform = 'translateY(-2px)'; e.currentTarget.style.boxShadow = '0 8px 28px rgba(47,43,110,0.1)'; }}
      onMouseLeave={e => { e.currentTarget.style.transform = 'none'; e.currentTarget.style.boxShadow = '0 2px 12px rgba(47,43,110,0.06)'; }}
      >
        <div style={{
          width: '44px', height: '44px', borderRadius: '14px',
          background: 'linear-gradient(135deg, #EEEDFA, #F5F4FA)',
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          fontSize: '22px', flexShrink: 0,
        }}>{todayTip.icon}</div>
        <div>
          <p style={{ fontWeight: 700, fontSize: '12px', color: '#7F79B6', marginBottom: '4px', textTransform: 'uppercase', letterSpacing: '0.5px' }}>
            💡 Tip of the Day
          </p>
          <p style={{ fontSize: '13px', color: '#555', lineHeight: '1.5' }}>{todayTip.text}</p>
        </div>
      </div>

      {/* Loading skeleton */}
      {loading && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '14px', marginBottom: '20px' }}>
          <div style={{ height: '140px', borderRadius: '24px' }} className="skeleton" />
          <div style={{ display: 'flex', gap: '10px' }}>
            <div style={{ flex: 1, height: '80px', borderRadius: '18px' }} className="skeleton" />
            <div style={{ flex: 1, height: '80px', borderRadius: '18px' }} className="skeleton" />
          </div>
        </div>
      )}
    </div>
  );
}

export default HomePage;
