import React, { useEffect, useState } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { getNotifications } from '../api';

const links = [
  { path: '/', label: 'Dashboard', icon: '📊' },
  { path: '/patients', label: 'Patients', icon: '👥' },
  { path: '/alerts', label: 'Alerts', icon: '🚨', badge: true },
];

function Sidebar({ doctor, onLogout }) {
  const nav = useNavigate();
  const loc = useLocation();
  const [unread, setUnread] = useState(0);
  const [sos, setSos] = useState(0);

  // Live unread alert count (polls every 15 s)
  useEffect(() => {
    let alive = true;
    const load = () => getNotifications(doctor.doctor_id).then(res => {
      if (!alive) return;
      const list = res.data || [];
      setUnread(list.filter(n => !n.read).length);
      setSos(list.filter(n => !n.read && (n.title || '').includes('SOS')).length);
    }).catch(() => {});
    load();
    const id = setInterval(load, 15000);
    return () => { alive = false; clearInterval(id); };
  }, [doctor.doctor_id]);

  const activeIndex = Math.max(0, links.findIndex(l =>
    l.path === '/' ? loc.pathname === '/' : loc.pathname.startsWith(l.path) || (l.path === '/patients' && loc.pathname.startsWith('/patient/'))
  ));

  return (
    <aside style={{
      width: '260px', height: '100vh', position: 'fixed', left: 0, top: 0, zIndex: 50,
      background: 'radial-gradient(400px 300px at 0% 0%, rgba(34,211,238,0.14), transparent 60%), radial-gradient(400px 400px at 100% 100%, rgba(139,92,246,0.2), transparent 60%), linear-gradient(180deg, #13103A 0%, #0A0A22 100%)',
      color: '#fff', display: 'flex', flexDirection: 'column', borderRight: '1px solid rgba(255,255,255,0.06)',
    }}>
      {/* Logo */}
      <div style={{ padding: '26px 22px 22px', display: 'flex', alignItems: 'center', gap: 12 }}>
        <div style={{ width: 42, height: 42, borderRadius: 13, display: 'grid', placeItems: 'center', fontSize: 21,
          background: 'linear-gradient(135deg, #22D3EE, #8B5CF6)', boxShadow: '0 8px 22px rgba(139,92,246,0.45)' }}>🩺</div>
        <div>
          <h2 style={{ color: '#fff', fontSize: 18, fontWeight: 800, letterSpacing: '-0.02em' }}>WoundWatch</h2>
          <p style={{ fontSize: 11, color: 'rgba(226,232,255,0.5)', fontWeight: 600, letterSpacing: '0.06em' }}>DOCTOR CONSOLE</p>
        </div>
      </div>

      {/* Doctor card */}
      <div style={{ margin: '0 16px 18px', padding: 14, borderRadius: 16, background: 'rgba(255,255,255,0.05)',
        border: '1px solid rgba(255,255,255,0.08)', display: 'flex', gap: 12, alignItems: 'center' }}>
        <div style={{ width: 38, height: 38, borderRadius: '50%', display: 'grid', placeItems: 'center', fontWeight: 800,
          background: 'linear-gradient(135deg, rgba(34,211,238,0.3), rgba(139,92,246,0.4))', fontSize: 15 }}>
          {(doctor.name || 'D').replace(/^Dr\.?\s*/i, '')[0]}
        </div>
        <div style={{ minWidth: 0 }}>
          <p style={{ fontSize: 14, fontWeight: 700, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>{doctor.name}</p>
          <p style={{ fontSize: 11.5, color: 'rgba(226,232,255,0.55)' }}>{doctor.specialization}</p>
        </div>
        <span title="Online" style={{ marginLeft: 'auto', width: 8, height: 8, borderRadius: '50%', background: '#34D399', boxShadow: '0 0 8px #34D399' }} />
      </div>

      {/* Nav with sliding indicator */}
      <nav style={{ position: 'relative', padding: '4px 12px', flex: 1 }}>
        <div style={{
          position: 'absolute', left: 12, right: 12, height: 46, top: 4 + activeIndex * 50, borderRadius: 13,
          background: 'linear-gradient(90deg, rgba(34,211,238,0.18), rgba(139,92,246,0.18))',
          border: '1px solid rgba(255,255,255,0.1)', transition: 'top 0.45s cubic-bezier(0.16,1,0.3,1)',
        }}>
          <span style={{ position: 'absolute', left: -12, top: 11, width: 4, height: 24, borderRadius: 4,
            background: 'linear-gradient(#22D3EE, #8B5CF6)', boxShadow: '0 0 12px #22D3EE' }} />
        </div>
        {links.map((link, i) => {
          const active = i === activeIndex;
          return (
            <div key={link.path} onClick={() => nav(link.path)} style={{
              position: 'relative', height: 46, marginBottom: 4, padding: '0 16px', borderRadius: 13, cursor: 'pointer',
              display: 'flex', alignItems: 'center', gap: 12,
              color: active ? '#fff' : 'rgba(226,232,255,0.6)', transition: 'color 0.25s',
            }}
              onMouseEnter={e => { if (!active) e.currentTarget.style.color = '#fff'; }}
              onMouseLeave={e => { if (!active) e.currentTarget.style.color = 'rgba(226,232,255,0.6)'; }}
            >
              <span style={{ fontSize: 17 }}>{link.icon}</span>
              <span style={{ fontSize: 14, fontWeight: active ? 700 : 600 }}>{link.label}</span>
              {link.badge && unread > 0 && (
                <span style={{
                  marginLeft: 'auto', minWidth: 22, height: 22, padding: '0 7px', borderRadius: 11, fontSize: 11, fontWeight: 800,
                  display: 'grid', placeItems: 'center', color: '#fff',
                  background: sos ? '#EF4444' : 'rgba(139,92,246,0.7)',
                  boxShadow: sos ? '0 0 0 0 rgba(239,68,68,0.6)' : 'none', animation: sos ? 'sosPulse 1.6s infinite' : 'none',
                }}>{unread}</span>
              )}
            </div>
          );
        })}
      </nav>

      {/* Logout */}
      <div style={{ padding: '16px', borderTop: '1px solid rgba(255,255,255,0.06)' }}>
        <button onClick={onLogout} style={{
          width: '100%', background: 'rgba(255,255,255,0.06)', color: 'rgba(226,232,255,0.8)',
          border: '1px solid rgba(255,255,255,0.1)', padding: 11, fontSize: 13,
        }}>
          Log out
        </button>
      </div>
    </aside>
  );
}

export default Sidebar;
