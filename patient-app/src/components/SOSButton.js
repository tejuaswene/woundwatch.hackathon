import React, { useState, useRef } from 'react';

// Ask the phone for its GPS position. Resolves to {lat, lng, accuracy} or null (never rejects).
function getLocation(timeoutMs = 10000) {
  return new Promise(resolve => {
    if (!('geolocation' in navigator)) return resolve({ error: 'unsupported' });
    navigator.geolocation.getCurrentPosition(
      pos => resolve({ lat: pos.coords.latitude, lng: pos.coords.longitude, accuracy: pos.coords.accuracy }),
      err => resolve({ error: err.code === 1 ? 'denied' : 'unavailable' }),
      { enableHighAccuracy: true, timeout: timeoutMs, maximumAge: 60000 }
    );
  });
}

function SOSButton({ user }) {
  const [showModal, setShowModal] = useState(false);
  const [sending, setSending] = useState(false);
  const [sent, setSent] = useState(false);
  const [message, setMessage] = useState('');
  // location: null = not asked, 'loading', {lat,lng,accuracy}, or {error}
  const [location, setLocation] = useState(null);
  const locationPromise = useRef(null);
  const [locationSaved, setLocationSaved] = useState(false);

  const requestLocation = () => {
    setLocation('loading');
    locationPromise.current = getLocation().then(loc => { setLocation(loc); return loc; });
  };

  const openSOS = () => {
    setShowModal(true);
    requestLocation(); // start GPS early so it's ready when they tap Send
  };

  const quickMessages = [
    'Wound looks worse — bleeding',
    'Severe pain around wound',
    'High fever with wound swelling',
    'Wound has opened / stitches came out',
    'Foul smell / green discharge from wound',
  ];

  const sendSOS = async (sosMessage) => {
    setSending(true);
    try {
      // Wait for GPS, but never longer than 5 more seconds — the SOS must go out
      let loc = location && location !== 'loading' ? location : null;
      if (!loc && locationPromise.current) {
        loc = await Promise.race([locationPromise.current, new Promise(r => setTimeout(() => r(null), 5000))]);
      }

      const fd = new FormData();
      fd.append('phone', user.phone);
      fd.append('message', sosMessage || 'Emergency! Patient needs immediate attention.');
      if (loc && loc.lat != null) {
        fd.append('latitude', String(loc.lat));
        fd.append('longitude', String(loc.lng));
        if (loc.accuracy != null) fd.append('accuracy', String(Math.round(loc.accuracy)));
      }

      const res = await fetch(`${window.API_BASE || 'http://localhost:8000'}/api/sos`, { method: 'POST', body: fd });
      const data = await res.json();
      if (data.success) {
        // trust the server's answer, not just whether the phone found GPS
        setLocationSaved(data.location_shared === true);
        setSent(true);
        setTimeout(() => { setSent(false); setShowModal(false); setMessage(''); }, 3000);
      }
    } catch (e) {
      alert('Failed to send SOS. Please call your doctor directly.');
    }
    setSending(false);
  };

  return (
    <>
      {/* Floating SOS Button */}
      <button
        onClick={openSOS}
        style={{
          position: 'fixed', bottom: '90px', left: '20px', width: '56px', height: '56px',
          borderRadius: '50%', border: 'none', cursor: 'pointer', zIndex: 1000,
          background: 'linear-gradient(135deg, #D64545, #B83030)',
          color: '#fff', fontSize: '13px', fontWeight: 900, letterSpacing: '1px',
          boxShadow: '0 4px 20px rgba(214,69,69,0.5)',
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          animation: 'sosPulse 2s infinite'
        }}
      >
        SOS
      </button>

      {/* Pulse Animation */}
      <style>{`
        @keyframes sosPulse {
          0% { box-shadow: 0 0 0 0 rgba(214,69,69,0.5); }
          70% { box-shadow: 0 0 0 12px rgba(214,69,69,0); }
          100% { box-shadow: 0 0 0 0 rgba(214,69,69,0); }
        }
      `}</style>

      {/* SOS Modal */}
      {showModal && (
        <div style={{
          position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.6)', zIndex: 2000,
          display: 'flex', alignItems: 'flex-end', justifyContent: 'center'
        }}>
          <div style={{
            background: '#fff', borderRadius: '24px 24px 0 0', padding: '24px', width: '100%',
            maxWidth: '480px', maxHeight: '85vh', overflowY: 'auto',
            animation: 'slideUp 0.3s ease-out'
          }}>
            <style>{`@keyframes slideUp { from { transform: translateY(100%); } to { transform: translateY(0); } }`}</style>

            {sent ? (
              /* Success State */
              <div style={{ textAlign: 'center', padding: '30px 0' }}>
                <div style={{ fontSize: '56px', marginBottom: '12px' }}>✅</div>
                <p style={{ fontSize: '20px', fontWeight: 800, color: '#2BA84A' }}>SOS Sent!</p>
                <p style={{ fontSize: '13px', color: '#8C8AAE', marginTop: '8px' }}>
                  Your doctor has been alerted. They will respond shortly.
                </p>
                <p style={{ fontSize: '12px', color: '#2F2B6E', marginTop: '8px', fontWeight: 600 }}>
                  {locationSaved
                    ? '📍 Your location was shared with your doctor'
                    : '📍 Location was not shared'}
                </p>
                <p style={{ fontSize: '12px', color: '#D64545', marginTop: '12px', fontWeight: 600 }}>
                  If this is life-threatening, call 112 immediately.
                </p>
              </div>
            ) : (
              /* SOS Form */
              <>
                <div style={{ textAlign: 'center', marginBottom: '20px' }}>
                  <div style={{ fontSize: '40px', marginBottom: '8px' }}>🚨</div>
                  <p style={{ fontSize: '20px', fontWeight: 800, color: '#D64545' }}>Emergency SOS</p>
                  <p style={{ fontSize: '13px', color: '#8C8AAE', marginTop: '4px' }}>
                    Alert your doctor immediately
                  </p>
                </div>

                {/* Quick Message Buttons */}
                <p style={{ fontSize: '12px', fontWeight: 600, color: '#2F2B6E', marginBottom: '8px' }}>
                  Quick select your concern:
                </p>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', marginBottom: '16px' }}>
                  {quickMessages.map(qm => (
                    <button key={qm} onClick={() => setMessage(qm)} style={{
                      padding: '12px 14px', borderRadius: '10px', border: '2px solid',
                      borderColor: message === qm ? '#D64545' : '#E8E7F0',
                      background: message === qm ? '#FEF2F2' : '#fff',
                      color: message === qm ? '#D64545' : '#333',
                      fontSize: '13px', fontWeight: 600, cursor: 'pointer', textAlign: 'left'
                    }}>{qm}</button>
                  ))}
                </div>

                {/* Custom Message */}
                <textarea
                  placeholder="Or type your own message..."
                  value={quickMessages.includes(message) ? '' : message}
                  onChange={(e) => setMessage(e.target.value)}
                  style={{
                    width: '100%', height: '70px', borderRadius: '10px', border: '2px solid #E8E7F0',
                    padding: '12px', fontSize: '13px', resize: 'none', outline: 'none',
                    fontFamily: 'inherit', boxSizing: 'border-box'
                  }}
                />

                {/* GPS status */}
                <div style={{
                  marginTop: '12px', padding: '10px 12px', borderRadius: '10px', fontSize: '12px', fontWeight: 600,
                  display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '8px',
                  background: location && location.lat != null ? '#E8F8EC' : location === 'loading' ? '#F5F4FA' : '#FFF5E5',
                  color: location && location.lat != null ? '#2BA84A' : location === 'loading' ? '#7F79B6' : '#B9771B'
                }}>
                  <span>
                    {location === 'loading' && '📍 Getting your location…'}
                    {location && location.lat != null &&
                      `📍 Location ready${location.accuracy ? ` (±${Math.round(location.accuracy)} m)` : ''} — will be sent to doctor`}
                    {location && location.error === 'denied' && '📍 Location blocked. Allow location for this site to share it. SOS will still be sent.'}
                    {location && (location.error === 'unavailable' || location.error === 'unsupported') &&
                      '📍 Could not get location. SOS will still be sent.'}
                  </span>
                  {location && location.error && (
                    <button onClick={requestLocation} style={{
                      flexShrink: 0, padding: '5px 10px', borderRadius: '8px', border: 'none', cursor: 'pointer',
                      background: '#fff', color: '#B9771B', fontSize: '11px', fontWeight: 700
                    }}>Retry</button>
                  )}
                </div>

                {/* Action Buttons */}
                <div style={{ display: 'flex', gap: '10px', marginTop: '16px' }}>
                  <button onClick={() => { setShowModal(false); setMessage(''); }} style={{
                    flex: 1, padding: '14px', borderRadius: '12px', border: 'none', cursor: 'pointer',
                    background: '#F5F4F8', color: '#2F2B6E', fontSize: '14px', fontWeight: 700
                  }}>Cancel</button>
                  <button onClick={() => sendSOS(message)} disabled={sending} style={{
                    flex: 2, padding: '14px', borderRadius: '12px', border: 'none', cursor: 'pointer',
                    background: sending ? '#ccc' : 'linear-gradient(135deg, #D64545, #B83030)',
                    color: '#fff', fontSize: '14px', fontWeight: 700
                  }}>
                    {sending ? (location === 'loading' ? 'Getting location…' : 'Sending...') : '🚨 Send SOS Now'}
                  </button>
                </div>

                <p style={{ fontSize: '11px', color: '#8C8AAE', textAlign: 'center', marginTop: '12px' }}>
                  For life-threatening emergencies, call <b style={{ color: '#D64545' }}>112</b> immediately
                </p>
              </>
            )}
          </div>
        </div>
      )}
    </>
  );
}

export default SOSButton;
