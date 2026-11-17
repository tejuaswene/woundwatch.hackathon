import React, { useState, useEffect } from 'react';
import { sendOTP, verifyOTP } from '../api';
import { MedicalBackground3D } from '../three/Scene3D';

function LoginPage({ onLogin }) {
  const [phone, setPhone] = useState('');
  const [otp, setOtp] = useState('');
  const [step, setStep] = useState(1);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [mounted, setMounted] = useState(false);

  useEffect(() => { setTimeout(() => setMounted(true), 100); }, []);

  const handleSendOTP = async () => {
    if (phone.length !== 10) { setError('Enter 10-digit mobile number'); return; }
    setLoading(true); setError('');
    try {
      await sendOTP(phone);
      setStep(2);
    } catch (e) { setError(e?.response?.data?.detail || 'Failed to send OTP. Is the server running?'); }
    setLoading(false);
  };

  const handleVerify = async () => {
    if (otp.length !== 4) { setError('Enter 4-digit OTP'); return; }
    setLoading(true); setError('');
    try {
      const res = await verifyOTP(phone, otp);
      onLogin({ phone, ...res.data });
    } catch (e) { setError(e?.response?.data?.detail || 'Invalid OTP. Please try again.'); }
    setLoading(false);
  };

  return (
    <div style={{
      minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center',
      background: 'radial-gradient(700px 500px at 20% 10%, #2A1F6E 0%, transparent 60%), radial-gradient(600px 500px at 90% 90%, #0B3A4F 0%, transparent 60%), #0A0A22',
      padding: '20px', position: 'relative', overflow: 'hidden',
    }}>
      {/* Interactive 3D scene: particles + DNA helix + medical cross (falls back to gradient without WebGL) */}
      <MedicalBackground3D />
      <div style={{ position: 'absolute', inset: 0, pointerEvents: 'none',
        background: 'radial-gradient(ellipse at center, transparent 35%, rgba(10,10,34,0.6) 100%)' }} />

      {/* Glass Login Card */}
      <div style={{
        width: '100%', maxWidth: '380px', padding: '40px 32px',
        background: 'rgba(255,255,255,0.12)',
        backdropFilter: 'blur(40px)', WebkitBackdropFilter: 'blur(40px)',
        borderRadius: '28px',
        border: '1px solid rgba(255,255,255,0.18)',
        boxShadow: '0 32px 64px rgba(0,0,0,0.3), inset 0 1px 0 rgba(255,255,255,0.15)',
        transform: mounted ? 'translateY(0) scale(1)' : 'translateY(30px) scale(0.95)',
        opacity: mounted ? 1 : 0,
        transition: 'all 0.8s cubic-bezier(0.16, 1, 0.3, 1)',
        position: 'relative', zIndex: 2,
      }}>
        {/* Logo */}
        <div style={{
          textAlign: 'center', marginBottom: '32px',
          transform: mounted ? 'translateY(0)' : 'translateY(20px)',
          opacity: mounted ? 1 : 0,
          transition: 'all 0.8s 0.15s cubic-bezier(0.16, 1, 0.3, 1)',
        }}>
          <div style={{
            width: '72px', height: '72px', borderRadius: '22px', margin: '0 auto 16px',
            background: 'rgba(255,255,255,0.15)',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            fontSize: '36px',
            boxShadow: '0 8px 32px rgba(0,0,0,0.2), inset 0 1px 0 rgba(255,255,255,0.2)',
            border: '1px solid rgba(255,255,255,0.1)',
            animation: 'glowPulse 3s ease-in-out infinite',
          }}>🩹</div>
          <h1 style={{
            fontSize: '28px', fontWeight: 900, color: '#fff',
            letterSpacing: '-0.03em', marginBottom: '6px',
          }}>WoundWatch</h1>
          <p style={{ color: 'rgba(255,255,255,0.55)', fontSize: '13px', fontWeight: 500 }}>
            AI-Powered Post-Surgical Care
          </p>
        </div>

        {/* Form */}
        <div style={{
          transform: mounted ? 'translateY(0)' : 'translateY(20px)',
          opacity: mounted ? 1 : 0,
          transition: 'all 0.8s 0.3s cubic-bezier(0.16, 1, 0.3, 1)',
        }}>
          {step === 1 ? (
            <>
              <label style={{ display: 'block', color: 'rgba(255,255,255,0.7)', fontSize: '12px', fontWeight: 600, marginBottom: '8px', letterSpacing: '0.05em', textTransform: 'uppercase' }}>
                Mobile Number
              </label>
              <div style={{ display: 'flex', gap: '8px', marginBottom: '16px' }}>
                <div style={{
                  padding: '14px 12px', background: 'rgba(255,255,255,0.08)',
                  borderRadius: '14px', color: 'rgba(255,255,255,0.5)',
                  fontSize: '15px', fontWeight: 600, border: '1px solid rgba(255,255,255,0.1)',
                  display: 'flex', alignItems: 'center',
                }}>+91</div>
                <input
                  value={phone} onChange={e => setPhone(e.target.value.replace(/\D/g, '').slice(0, 10))}
                  placeholder="Enter phone number"
                  type="tel" inputMode="numeric"
                  style={{
                    flex: 1, background: 'rgba(255,255,255,0.08)',
                    border: '1px solid rgba(255,255,255,0.12)',
                    borderRadius: '14px', color: '#fff', padding: '14px 16px',
                    fontSize: '15px', fontWeight: 500,
                  }}
                />
              </div>
              <button onClick={handleSendOTP} disabled={loading} style={{
                width: '100%', padding: '16px',
                background: 'linear-gradient(135deg, #2BA84A 0%, #22C55E 100%)',
                borderRadius: '14px', fontSize: '15px', fontWeight: 700,
                color: '#fff', border: 'none',
                boxShadow: '0 8px 24px rgba(43,168,74,0.35)',
                transform: loading ? 'scale(0.98)' : 'none',
              }}>
                {loading ? (
                  <span style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '8px' }}>
                    <span style={{ width: '18px', height: '18px', border: '2px solid rgba(255,255,255,0.3)', borderTopColor: '#fff', borderRadius: '50%', display: 'inline-block', animation: 'spin 0.6s linear infinite' }} />
                    Sending...
                  </span>
                ) : 'Send OTP →'}
              </button>
            </>
          ) : (
            <>
              <label style={{ display: 'block', color: 'rgba(255,255,255,0.7)', fontSize: '12px', fontWeight: 600, marginBottom: '8px', letterSpacing: '0.05em', textTransform: 'uppercase' }}>
                Enter OTP
              </label>
              <p style={{ color: 'rgba(255,255,255,0.4)', fontSize: '12px', marginBottom: '12px' }}>
                Sent to +91 {phone}
              </p>
              <div style={{ display: 'flex', gap: '10px', justifyContent: 'center', marginBottom: '20px' }}>
                {[0,1,2,3].map(i => (
                  <input key={i} maxLength="1" value={otp[i] || ''} inputMode="numeric"
                    style={{
                      width: '56px', height: '60px', textAlign: 'center',
                      fontSize: '24px', fontWeight: 800, color: '#fff',
                      background: otp[i] ? 'rgba(43,168,74,0.2)' : 'rgba(255,255,255,0.08)',
                      border: `2px solid ${otp[i] ? 'rgba(43,168,74,0.5)' : 'rgba(255,255,255,0.12)'}`,
                      borderRadius: '16px',
                      transition: 'all 0.3s ease',
                      transform: otp[i] ? 'scale(1.05)' : 'scale(1)',
                    }}
                    onChange={e => {
                      const val = e.target.value.replace(/\D/g, '');
                      if (val.length <= 1) {
                        const newOtp = otp.split('');
                        newOtp[i] = val;
                        setOtp(newOtp.join(''));
                        if (val && i < 3) e.target.nextSibling?.focus();
                      }
                    }}
                    onKeyDown={e => {
                      if (e.key === 'Backspace' && !otp[i] && i > 0) {
                        e.target.previousSibling?.focus();
                      }
                    }}
                  />
                ))}
              </div>
              <button onClick={handleVerify} disabled={loading} style={{
                width: '100%', padding: '16px',
                background: 'linear-gradient(135deg, #2BA84A 0%, #22C55E 100%)',
                borderRadius: '14px', fontSize: '15px', fontWeight: 700,
                color: '#fff', border: 'none',
                boxShadow: '0 8px 24px rgba(43,168,74,0.35)',
              }}>
                {loading ? (
                  <span style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '8px' }}>
                    <span style={{ width: '18px', height: '18px', border: '2px solid rgba(255,255,255,0.3)', borderTopColor: '#fff', borderRadius: '50%', display: 'inline-block', animation: 'spin 0.6s linear infinite' }} />
                    Verifying...
                  </span>
                ) : 'Verify & Continue →'}
              </button>
              <button onClick={() => { setStep(1); setOtp(''); setError(''); }} style={{
                width: '100%', marginTop: '10px', padding: '12px',
                background: 'transparent', color: 'rgba(255,255,255,0.5)',
                fontSize: '13px', border: 'none',
              }}>
                ← Change Number
              </button>
            </>
          )}

          {error && (
            <div style={{
              marginTop: '14px', padding: '10px 14px', borderRadius: '12px',
              background: 'rgba(214,69,69,0.15)', color: '#FF8A8A',
              fontSize: '13px', fontWeight: 500, textAlign: 'center',
              animation: 'scaleIn 0.3s ease',
            }}>⚠️ {error}</div>
          )}
        </div>
      </div>
    </div>
  );
}

export default LoginPage;
