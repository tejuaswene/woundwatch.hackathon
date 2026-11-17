import React, { useState } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import LoginPage from './pages/LoginPage';
import DashboardPage from './pages/DashboardPage';
import PatientsPage from './pages/PatientsPage';
import PatientDetailPage from './pages/PatientDetailPage';
import AlertsPage from './pages/AlertsPage';
import Sidebar from './components/Sidebar';

function App() {
  const [doctor, setDoctor] = useState(null);

  const handleLogin = (data) => {
    setDoctor(data);
  };

  const handleLogout = () => {
    setDoctor(null);
  };

  if (!doctor) return <LoginPage onLogin={handleLogin} />;

  return (
    <Router>
      <div style={{ display: 'flex', minHeight: '100vh', background: '#F5F4FA' }}>
        <Sidebar doctor={doctor} onLogout={handleLogout} />
        <main style={{
          marginLeft: '260px', flex: 1, padding: '32px',
          maxWidth: 'calc(100vw - 260px)'
        }}>
          <Routes>
            <Route path="/" element={<DashboardPage doctor={doctor} />} />
            <Route path="/patients" element={<PatientsPage doctor={doctor} />} />
            <Route path="/patient/:phone" element={<PatientDetailPage doctor={doctor} />} />
            <Route path="/alerts" element={<AlertsPage doctor={doctor} />} />
            <Route path="*" element={<Navigate to="/" />} />
          </Routes>
        </main>
      </div>
    </Router>
  );
}

export default App;
