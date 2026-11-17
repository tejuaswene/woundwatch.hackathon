import React, { useState, useEffect } from 'react';
import { getNotifications, markRead } from '../api';

function NotificationsPage({ user }) {
  const [notifs, setNotifs] = useState([]);
  const [loading, setLoading] = useState(true);

  const fetch = () => {
    getNotifications(user.phone).then(res => {
      setNotifs(res.data);
      setLoading(false);
    }).catch(() => setLoading(false));
  };

  useEffect(() => {
    fetch();
    const interval = setInterval(fetch, 15000);
    return () => clearInterval(interval);
  }, [user.phone]);

  const handleRead = async (id) => {
    await markRead(id);
    setNotifs(prev => prev.map(n => n.id === id ? { ...n, read: true } : n));
  };

  const unread = notifs.filter(n => !n.read).length;

  const getIcon = (title) => {
    if (title?.includes('SOS')) return '🚨';
    if (title?.includes('RED') || title?.includes('HIGH')) return '⚠️';
    if (title?.includes('Doctor')) return '👨‍⚕️';
    return '📋';
  };

  const getBorderColor = (n) => {
    if (n.read) return '#E8E7F0';
    if (n.title?.includes('SOS')) return '#D64545';
    if (n.title?.includes('RED') || n.title?.includes('HIGH')) return '#E89B2C';
    return '#7F79B6';
  };

  const timeAgo = (dateStr) => {
    const diff = Date.now() - new Date(dateStr).getTime();
    const mins = Math.floor(diff / 60000);
    if (mins < 1) return 'Just now';
    if (mins < 60) return `${mins}m ago`;
    const hrs = Math.floor(mins / 60);
    if (hrs < 24) return `${hrs}h ago`;
    const days = Math.floor(hrs / 24);
    return `${days}d ago`;
  };

  return (
    <div style={{ padding: '20px', paddingTop: '16px', maxWidth: '480px', margin: '0 auto' }}>
      {/* Header */}
      <div style={{
        display: 'flex', justifyContent: 'space-between', alignItems: 'center',
        marginBottom: '20px', animation: 'fadeInUp 0.4s ease forwards'
      }}>
        <div>
          <h2 style={{ fontSize: '24px', fontWeight: 900, letterSpacing: '-0.03em' }}>Notifications</h2>
          <p style={{ fontSize: '12px', color: '#8C8AAE', marginTop: '2px', fontWeight: 500 }}>
            {unread > 0 ? `${unread} unread` : 'All caught up!'}
          </p>
        </div>
        {unread > 0 && (
          <div style={{
            width: '32px', height: '32px', borderRadius: '10px',
            background: 'linear-gradient(135deg, #D64545, #EF4444)',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            color: '#fff', fontSize: '14px', fontWeight: 800,
            animation: 'scaleIn 0.3s ease'
          }}>{unread}</div>
        )}
      </div>

      {loading ? (
        /* Skeleton */
        <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
          {[1, 2, 3].map(i => (
            <div key={i} style={{
              background: '#fff', borderRadius: '16px', padding: '20px',
              boxShadow: '0 2px 8px rgba(47,43,110,0.04)'
            }}>
              <div style={{ display: 'flex', gap: '12px' }}>
                <div style={{ width: '40px', height: '40px', borderRadius: '12px' }} className="skeleton" />
                <div style={{ flex: 1 }}>
                  <div style={{ width: '60%', height: '14px', marginBottom: '8px' }} className="skeleton" />
                  <div style={{ width: '90%', height: '12px' }} className="skeleton" />
                </div>
              </div>
            </div>
          ))}
        </div>
      ) : notifs.length === 0 ? (
        /* Empty */
        <div style={{
          textAlign: 'center', padding: '60px 20px',
          animation: 'fadeInUp 0.5s ease forwards'
        }}>
          <div style={{
            width: '72px', height: '72px', borderRadius: '22px', margin: '0 auto 16px',
            background: 'linear-gradient(135deg, #EEEDFA, #F5F4FA)',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            fontSize: '32px'
          }}>🔔</div>
          <p style={{ fontWeight: 700, color: '#2F2B6E', fontSize: '16px' }}>No notifications yet</p>
          <p style={{ color: '#8C8AAE', fontSize: '13px', marginTop: '6px' }}>
            Alerts from your doctor and AI analysis will appear here
          </p>
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
          {notifs.map((n, i) => (
            <div key={n.id} onClick={() => !n.read && handleRead(n.id)} style={{
              background: n.read ? '#FAFAFA' : '#fff',
              borderRadius: '16px', padding: '16px',
              borderLeft: `4px solid ${getBorderColor(n)}`,
              boxShadow: n.read ? 'none' : '0 2px 10px rgba(47,43,110,0.06)',
              opacity: n.read ? 0.65 : 1,
              cursor: n.read ? 'default' : 'pointer',
              transition: 'all 0.25s ease',
              animation: `fadeInUp 0.4s ${i * 0.05}s ease forwards`, opacity: 0
            }}>
              <div style={{ display: 'flex', gap: '12px', alignItems: 'start' }}>
                <div style={{
                  width: '40px', height: '40px', borderRadius: '12px', flexShrink: 0,
                  background: n.title?.includes('SOS') ? '#FEF2F2'
                    : n.title?.includes('RED') ? '#FFF8ED'
                    : '#F0EEFF',
                  display: 'flex', alignItems: 'center', justifyContent: 'center',
                  fontSize: '18px'
                }}>{getIcon(n.title)}</div>
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <p style={{
                      fontWeight: 700, fontSize: '14px',
                      color: n.title?.includes('SOS') ? '#D64545' : '#2F2B6E'
                    }}>{n.title}</p>
                    {!n.read && (
                      <div style={{
                        width: '8px', height: '8px', borderRadius: '50%',
                        background: '#2BA84A', flexShrink: 0
                      }} />
                    )}
                  </div>
                  <p style={{
                    fontSize: '13px', color: '#555', marginTop: '4px', lineHeight: '1.5',
                    overflow: 'hidden', textOverflow: 'ellipsis',
                    display: '-webkit-box', WebkitLineClamp: 2, WebkitBoxOrient: 'vertical'
                  }}>{n.message}</p>
                  <p style={{ fontSize: '11px', color: '#8C8AAE', marginTop: '6px', fontWeight: 500 }}>
                    {timeAgo(n.created_at)}
                  </p>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

export default NotificationsPage;
