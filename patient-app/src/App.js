import React, { useState, useEffect } from 'react';
import { HashRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { getProfile } from './api';
import LoginPage from './pages/LoginPage';
import HomePage from './pages/HomePage';
import UploadPage from './pages/UploadPage';
import HistoryPage from './pages/HistoryPage';
import ChatPage from './pages/ChatPage';
import NotificationsPage from './pages/NotificationsPage';
import BottomNav from './components/BottomNav';
import SOSButton from './components/SOSButton';

function App() {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const phone = localStorage.getItem('ww_phone');
    if (phone) {
      getProfile(phone).then(res => {
        setUser(res.data);
        setLoading(false);
      }).catch(() => {
        localStorage.removeItem('ww_phone');
        setLoading(false);
      });
    } else {
      setLoading(false);
    }
  }, []);

  const handleLogin = (data) => {
    localStorage.setItem('ww_phone', data.phone);
    setUser(data);
  };

  const handleLogout = () => {
    localStorage.removeItem('ww_phone');
    setUser(null);
  };

  if (loading) return (
    <div style={{
      minHeight: '100vh', display: 'flex', flexDirection: 'column',
      alignItems: 'center', justifyContent: 'center',
      background: 'linear-gradient(135deg, #1D1A4E, #2F2B6E)'
    }}>
      <div style={{
        width: '64px', height: '64px', borderRadius: '20px',
        background: 'rgba(255,255,255,0.1)', backdropFilter: 'blur(10px)',
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        fontSize: '28px', marginBottom: '16px',
        border: '1px solid rgba(255,255,255,0.15)',
        animation: 'pulse 1.5s infinite'
      }}>🩹</div>
      <p style={{ color: 'rgba(255,255,255,0.6)', fontSize: '14px', fontWeight: 600 }}>
        Loading WoundWatch...
      </p>
    </div>
  );

  if (!user) return <LoginPage onLogin={handleLogin} />;

  return (
    <Router>
      <div style={{ background: '#F5F4FA', minHeight: '100vh' }}>
        <Routes>
          <Route path="/" element={<HomePage user={user} onLogout={handleLogout} />} />
          <Route path="/upload" element={<UploadPage user={user} />} />
          <Route path="/history" element={<HistoryPage user={user} />} />
          <Route path="/chat" element={<ChatPage user={user} />} />
          <Route path="/notifications" element={<NotificationsPage user={user} />} />
          <Route path="*" element={<Navigate to="/" />} />
        </Routes>
        <SOSButton user={user} />
        <BottomNav />
      </div>
    </Router>
  );
}

export default App;
