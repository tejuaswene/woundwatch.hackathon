import React, { useState, useEffect } from 'react';
import { getNotifications, markRead } from '../api';

// Hide the raw "| 📍 Location ...: https://..." part of the message — we show a button/map instead
const cleanMessage = (n) => (n.message || '').replace(/\s*\|\s*\u{1F4CD}.*$/u, '');

function LocationLink({ n, light }) {
  if (!n.maps_url) {
    return n.title.includes('SOS') ? (
      <p style={{ fontSize: '11px', marginTop: '6px', opacity: 0.8, color: light ? '#fff' : '#8C8AAE' }}>
        📍 Patient's location was not shared
      </p>
    ) : null;
  }
  return (
    <a href={n.maps_url} target="_blank" rel="noreferrer" style={{
      display: 'inline-flex', alignItems: 'center', gap: '6px', marginTop: '8px',
      padding: '6px 12px', borderRadius: '8px', fontSize: '12px', fontWeight: 700, textDecoration: 'none',
      background: light ? '#fff' : '#2F2B6E', color: light ? '#D64545' : '#fff'
    }}>
      📍 Open in Google Maps
      {n.location_accuracy ? <span style={{ fontWeight: 500, opacity: 0.8 }}>(±{Math.round(n.location_accuracy)} m)</span> : null}
    </a>
  );
}

function MapPreview({ n }) {
  if (n.latitude == null || n.longitude == null) return null;
  return (
    <iframe
      title={`sos-map-${n.id}`}
      src={`https://maps.google.com/maps?q=${n.latitude},${n.longitude}&z=16&output=embed`}
      style={{ width: '100%', height: '200px', border: 0, borderRadius: '10px', marginTop: '10px', background: '#eee' }}
      loading="lazy"
    />
  );
}

function AlertsPage({ doctor }) {
  const [notifs, setNotifs] = useState([]);

  const fetchNotifs = () => {
    getNotifications(doctor.doctor_id).then(res => setNotifs(res.data)).catch(() => {});
  };

  useEffect(() => {
    fetchNotifs();
    // Poll every 10 seconds for new alerts
    const interval = setInterval(fetchNotifs, 10000);
    return () => clearInterval(interval);
  }, [doctor.doctor_id]);

  const handleRead = async (id) => {
    await markRead(id);
    setNotifs(prev => prev.map(n => n.id === id ? { ...n, read: true } : n));
  };

  const unread = notifs.filter(n => !n.read).length;
  const sosAlerts = notifs.filter(n => !n.read && n.title.includes('SOS'));

  return (
    <div>
      {/* SOS Emergency Banner */}
      {sosAlerts.length > 0 && (
        <div style={{
          background: 'linear-gradient(135deg, #D64545, #B83030)', borderRadius: '16px',
          padding: '20px', marginBottom: '20px', color: '#fff',
          animation: 'sosFlash 1.5s infinite', boxShadow: '0 4px 20px rgba(214,69,69,0.4)'
        }}>
          <style>{`
            @keyframes sosFlash {
              0%, 100% { opacity: 1; }
              50% { opacity: 0.85; box-shadow: 0 4px 30px rgba(214,69,69,0.7); }
            }
          `}</style>
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '12px' }}>
            <span style={{ fontSize: '28px' }}>🚨</span>
            <div>
              <p style={{ fontSize: '18px', fontWeight: 800 }}>EMERGENCY SOS — {sosAlerts.length} Alert{sosAlerts.length > 1 ? 's' : ''}</p>
              <p style={{ fontSize: '12px', opacity: 0.9, marginTop: '2px' }}>Patient needs immediate attention</p>
            </div>
          </div>
          {sosAlerts.map(s => (
            <div key={s.id} style={{
              background: 'rgba(255,255,255,0.15)', borderRadius: '10px', padding: '12px', marginBottom: '8px'
            }}>
              <p style={{ fontSize: '13px', fontWeight: 600 }}>{cleanMessage(s)}</p>
              <LocationLink n={s} light />
              <MapPreview n={s} />
              <div style={{ display: 'flex', gap: '8px', marginTop: '8px' }}>
                <button onClick={() => handleRead(s.id)} style={{
                  padding: '6px 14px', fontSize: '11px', borderRadius: '6px', border: '1px solid rgba(255,255,255,0.4)',
                  background: 'rgba(255,255,255,0.2)', color: '#fff', cursor: 'pointer', fontWeight: 600
                }}>Acknowledge</button>
              </div>
            </div>
          ))}
        </div>
      )}

      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '24px' }}>
        <div>
          <h1 style={{ color: '#2F2B6E', fontSize: '28px', fontWeight: 800 }}>Alerts</h1>
          <p style={{ color: '#8C8AAE', fontSize: '14px', marginTop: '4px' }}>
            {unread > 0 ? `${unread} unread alert${unread > 1 ? 's' : ''}` : 'All caught up!'}
          </p>
        </div>
        <button onClick={fetchNotifs} style={{
          padding: '8px 16px', fontSize: '12px', borderRadius: '8px', border: 'none', cursor: 'pointer',
          background: '#F5F4F8', color: '#2F2B6E', fontWeight: 600
        }}>🔄 Refresh</button>
      </div>

      {notifs.length === 0 ? (
        <div style={{
          background: '#fff', borderRadius: '16px', padding: '60px', textAlign: 'center',
          boxShadow: '0 2px 12px rgba(0,0,0,0.04)', color: '#8C8AAE'
        }}>
          <div style={{ fontSize: '48px', marginBottom: '14px' }}>🔔</div>
          <p style={{ fontWeight: 600 }}>No alerts yet</p>
          <p style={{ fontSize: '13px', marginTop: '6px' }}>High risk patient alerts will appear here</p>
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
          {notifs.map(n => {
            const isSOS = n.title.includes('SOS');
            const isHighRisk = n.title.includes('HIGH');
            return (
              <div key={n.id} style={{
                background: isSOS && !n.read ? '#FEF2F2' : '#fff',
                borderRadius: '14px', padding: '20px',
                boxShadow: '0 2px 8px rgba(0,0,0,0.04)',
                borderLeft: n.read ? '5px solid #E8E7F0' : isSOS ? '5px solid #D64545' : isHighRisk ? '5px solid #E89B2C' : '5px solid #7F79B6',
                opacity: n.read ? 0.7 : 1
              }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'start' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                    <span style={{ fontSize: '20px' }}>{isSOS ? '🚨' : isHighRisk ? '⚠️' : '📋'}</span>
                    <div>
                      <p style={{
                        fontWeight: 700, fontSize: '15px',
                        color: isSOS ? '#D64545' : '#2F2B6E'
                      }}>{n.title}</p>
                      <p style={{ fontSize: '13px', color: '#555', marginTop: '4px', lineHeight: '1.4' }}>{cleanMessage(n)}</p>
                      <LocationLink n={n} />
                    </div>
                  </div>
                  <div style={{ textAlign: 'right', flexShrink: 0 }}>
                    <p style={{ fontSize: '11px', color: '#8C8AAE' }}>
                      {new Date(n.created_at).toLocaleDateString('en-IN', { day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit' })}
                    </p>
                    {!n.read && (
                      <button onClick={() => handleRead(n.id)} style={{
                        marginTop: '8px', padding: '5px 12px', fontSize: '11px',
                        background: '#F5F4F8', color: '#2F2B6E'
                      }}>Mark Read</button>
                    )}
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

export default AlertsPage;
