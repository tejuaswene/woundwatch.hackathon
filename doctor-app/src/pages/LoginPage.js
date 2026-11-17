import React, { useState, useEffect } from 'react';
import { doctorLogin } from '../api';
import { MedicalBackground3D } from '../three/Scene3D';

const FEATURES = [
  { icon: '🧠', title: 'AI wound screening', text: 'Daily photo risk scoring with colour-drift analysis' },
  { icon: '📍', title: 'Live SOS with GPS', text: 'Know where your patient is the moment they need you' },
  { icon: '📄', title: 'One-click PDF reports', text: 'Review a photo, the patient gets a signed report' },
];

function LoginPage({ onLogin }) {
  const [doctorId, setDoctorId] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [mounted, setMounted] = useState(false);

  useEffect(() => { const t = setTimeout(() => setMounted(true), 60); return () => clearTimeout(t); }, []);

  const handleLogin = async (e) => {
    e && e.preventDefault();
    setLoading(true); setError('');
    try {
      const res = await doctorLogin(doctorId, password);
      onLogin(res.data);
    } catch (err) {
      setError(err?.response ? 'Invalid Doctor ID or password' : 'Cannot reach the server. Is the backend running on port 8000?');
    }
    setLoading(false);
  };

  const rise = (delay) => ({
    opacity: mounted ? 1 : 0,
    transform: mounted ? 'translateY(0)' : 'translateY(24px)',
    transition: `opacity 0.9s ${delay}s cubic-bezier(0.16,1,0.3,1), transform 0.9s ${delay}s cubic-bezier(0.16,1,0.3,1)`,
  });

  const field = {
    background: 'rgba(255,255,255,0.06)', border: '1px solid rgba(255,255,255,0.14)', color: '#fff',
    borderRadius: '14px', padding: '14px 16px', fontSize: '15px',
  };

  return (
    <div className="ww-login" style={{
      minHeight: '100vh', position: 'relative', overflow: 'hidden',
      background: 'radial-gradient(1200px 700px at 15% 20%, #1B1650 0%, transparent 60%), radial-gradient(900px 600px at 85% 80%, #0B3A4F 0%, transparent 60%), #070A1C',
      display: 'flex', alignItems: 'center', justifyContent: 'center', padding: '32px',
    }}>
      <MedicalBackground3D />

      {/* vignette so text stays readable over the 3D scene */}
      <div style={{ position: 'absolute', inset: 0, pointerEvents: 'none',
        background: 'radial-gradient(ellipse at center, transparent 30%, rgba(7,10,28,0.65) 100%)' }} />

      <div className="ww-login-grid" style={{
        position: 'relative', zIndex: 2, width: '100%', maxWidth: '1120px',
        display: 'grid', gridTemplateColumns: '1.15fr 0.85fr', gap: '56px', alignItems: 'center',
      }}>
        {/* Left: story */}
        <div style={{ color: '#fff' }}>
          <div style={{ ...rise(0.05), display: 'inline-flex', alignItems: 'center', gap: '8px', padding: '6px 14px',
            borderRadius: '999px', border: '1px solid rgba(34,211,238,0.35)', background: 'rgba(34,211,238,0.08)',
            fontSize: '12px', fontWeight: 700, color: '#67E8F9', letterSpacing: '0.04em' }}>
            <span style={{ width: 7, height: 7, borderRadius: '50%', background: '#22D3EE', boxShadow: '0 0 10px #22D3EE', animation: 'pulse 1.6s infinite' }} />
            WOUNDWATCH · DOCTOR CONSOLE
          </div>
          <h1 style={{ ...rise(0.15), color: '#fff', fontSize: 'clamp(34px, 4.4vw, 56px)', lineHeight: 1.05, fontWeight: 900,
            letterSpacing: '-0.035em', marginTop: '22px' }}>
            Predict infection<br />
            <span style={{ background: 'linear-gradient(90deg, #67E8F9, #A78BFA 60%, #F0ABFC)', WebkitBackgroundClip: 'text',
              backgroundClip: 'text', WebkitTextFillColor: 'transparent' }}>before it becomes visible.</span>
          </h1>
          <p style={{ ...rise(0.25), color: 'rgba(226,232,255,0.7)', fontSize: '16px', lineHeight: 1.6, marginTop: '18px', maxWidth: '520px' }}>
            One photo a day from every post-surgical patient. AI flags the risky ones, you review, and they
            get your advice as a PDF — before a small redness becomes a readmission.
          </p>
          <div style={{ display: 'grid', gap: '12px', marginTop: '30px', maxWidth: '520px' }}>
            {FEATURES.map((f, i) => (
              <div key={f.title} style={{ ...rise(0.35 + i * 0.08), display: 'flex', gap: '14px', alignItems: 'center',
                padding: '14px 16px', borderRadius: '16px', background: 'rgba(255,255,255,0.04)',
                border: '1px solid rgba(255,255,255,0.08)', backdropFilter: 'blur(6px)' }}>
                <div style={{ width: 40, height: 40, borderRadius: 12, display: 'grid', placeItems: 'center', fontSize: 20,
                  background: 'linear-gradient(135deg, rgba(34,211,238,0.18), rgba(139,92,246,0.22))' }}>{f.icon}</div>
                <div>
                  <p style={{ fontWeight: 700, fontSize: '14px', color: '#fff' }}>{f.title}</p>
                  <p style={{ fontSize: '12.5px', color: 'rgba(226,232,255,0.6)' }}>{f.text}</p>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Right: glass login card */}
        <form onSubmit={handleLogin} style={{
          ...rise(0.2), position: 'relative', padding: '40px 36px', borderRadius: '28px',
          background: 'linear-gradient(160deg, rgba(255,255,255,0.12), rgba(255,255,255,0.04))',
          border: '1px solid rgba(255,255,255,0.16)', backdropFilter: 'blur(22px)', WebkitBackdropFilter: 'blur(22px)',
          boxShadow: '0 40px 100px rgba(0,0,0,0.45), inset 0 1px 0 rgba(255,255,255,0.18)',
        }}>
          <div style={{ position: 'absolute', inset: -1, borderRadius: 28, padding: 1, pointerEvents: 'none',
            background: 'linear-gradient(140deg, rgba(103,232,249,0.6), transparent 35%, transparent 65%, rgba(167,139,250,0.6))',
            WebkitMask: 'linear-gradient(#000 0 0) content-box, linear-gradient(#000 0 0)', WebkitMaskComposite: 'xor', maskComposite: 'exclude' }} />
          <div style={{ width: 56, height: 56, borderRadius: 18, display: 'grid', placeItems: 'center', fontSize: 28, marginBottom: 18,
            background: 'linear-gradient(135deg, #22D3EE, #8B5CF6)', boxShadow: '0 12px 30px rgba(139,92,246,0.45)' }}>🩺</div>
          <h2 style={{ color: '#fff', fontSize: '24px', fontWeight: 800 }}>Welcome back, Doctor</h2>
          <p style={{ color: 'rgba(226,232,255,0.6)', fontSize: '13.5px', marginTop: '4px', marginBottom: '26px' }}>
            Sign in to see today's wound reviews and alerts
          </p>

          <label style={{ display: 'block', fontSize: 12, fontWeight: 700, color: 'rgba(226,232,255,0.75)', marginBottom: 8, letterSpacing: '0.04em' }}>DOCTOR ID</label>
          <input value={doctorId} onChange={e => setDoctorId(e.target.value)} placeholder="Enter your Doctor ID" style={{ ...field, marginBottom: 18 }} autoComplete="username" />

          <label style={{ display: 'block', fontSize: 12, fontWeight: 700, color: 'rgba(226,232,255,0.75)', marginBottom: 8, letterSpacing: '0.04em' }}>PASSWORD</label>
          <input type="password" value={password} onChange={e => setPassword(e.target.value)} placeholder="Enter password" style={{ ...field, marginBottom: 24 }} autoComplete="current-password" />

          <button type="submit" disabled={loading} style={{
            width: '100%', padding: '15px', fontSize: '15px', borderRadius: '14px',
            background: 'linear-gradient(135deg, #06B6D4, #7C3AED)', boxShadow: '0 14px 34px rgba(124,58,237,0.45)',
          }}>
            {loading ? 'Signing in…' : 'Enter dashboard →'}
          </button>

          {error && <p style={{ color: '#FCA5A5', fontSize: 13, textAlign: 'center', marginTop: 14, fontWeight: 600 }}>{error}</p>}
        </form>
      </div>

      <style>{`
        .ww-login input::placeholder { color: rgba(226,232,255,0.35); }
        .ww-login input:focus { border-color: #67E8F9 !important; box-shadow: 0 0 0 4px rgba(34,211,238,0.15) !important; }
        @media (max-width: 900px) { .ww-login-grid { grid-template-columns: 1fr !important; gap: 32px !important; } }
      `}</style>
    </div>
  );
}

export default LoginPage;
