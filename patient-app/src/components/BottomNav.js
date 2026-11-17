import React from 'react';
import { useNavigate, useLocation } from 'react-router-dom';

const tabs = [
  { path: '/', icon: '🏠', label: 'Home' },
  { path: '/upload', icon: '📸', label: 'Scan' },
  { path: '/history', icon: '📊', label: 'History' },
  { path: '/chat', icon: '💬', label: 'AI Chat' },
  { path: '/notifications', icon: '🔔', label: 'Alerts' },
];

function BottomNav() {
  const nav = useNavigate();
  const loc = useLocation();

  return (
    <div style={{
      position: 'fixed', bottom: 0, left: 0, right: 0,
      background: 'rgba(255,255,255,0.85)',
      backdropFilter: 'blur(24px)', WebkitBackdropFilter: 'blur(24px)',
      borderTop: '1px solid rgba(232,231,240,0.5)',
      display: 'flex', justifyContent: 'space-around', alignItems: 'center',
      padding: '6px 8px 10px', zIndex: 40,
      boxShadow: '0 -4px 20px rgba(47,43,110,0.06)',
    }}>
      {tabs.map(t => {
        const active = loc.pathname === t.path;
        return (
          <button key={t.path} onClick={() => nav(t.path)} style={{
            display: 'flex', flexDirection: 'column', alignItems: 'center',
            gap: '2px', padding: '6px 12px', border: 'none',
            background: 'transparent', cursor: 'pointer',
            transition: 'all 0.3s cubic-bezier(0.4, 0, 0.2, 1)',
            transform: active ? 'translateY(-2px)' : 'none',
          }}>
            <div style={{
              fontSize: '22px',
              filter: active ? 'none' : 'grayscale(0.6)',
              opacity: active ? 1 : 0.5,
              transition: 'all 0.3s ease',
              transform: active ? 'scale(1.15)' : 'scale(1)',
            }}>{t.icon}</div>
            <span style={{
              fontSize: '10px', fontWeight: active ? 700 : 500,
              color: active ? '#2F2B6E' : '#8C8AAE',
              transition: 'all 0.3s ease',
            }}>{t.label}</span>
            {active && (
              <div style={{
                width: '4px', height: '4px', borderRadius: '50%',
                background: '#2BA84A', marginTop: '1px',
                animation: 'scaleIn 0.3s ease',
                boxShadow: '0 0 6px rgba(43,168,74,0.5)',
              }} />
            )}
          </button>
        );
      })}
    </div>
  );
}

export default BottomNav;
