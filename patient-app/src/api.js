import axios from 'axios';

const BASE = process.env.REACT_APP_API_URL || window.API_BASE || 'http://localhost:8000';

const API = axios.create({ baseURL: BASE });

// Auth — backend expects Form data
export const sendOTP = (phone) => {
  const fd = new FormData();
  fd.append('phone', phone);
  return API.post('/auth/send-otp', fd);
};

export const verifyOTP = (phone, otp) => {
  const fd = new FormData();
  fd.append('phone', phone);
  fd.append('otp', otp);
  return API.post('/auth/verify-otp', fd);
};

// Upload wound photo
export const uploadPhoto = (phone, file) => {
  const fd = new FormData();
  fd.append('phone', phone);
  fd.append('file', file);
  return API.post('/api/upload-wound-photo', fd, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });
};

// History
export const getHistory = (phone) => API.get(`/api/patient-history/${phone}`);

// Download the doctor's PDF report for one reviewed photo
export const downloadReviewReport = async (photoId, phone) => {
  const res = await API.get(`/api/review-report/${photoId}`, {
    params: { phone }, responseType: 'blob'
  });
  const cd = res.headers['content-disposition'] || '';
  const match = cd.match(/filename="?([^"]+)"?/);
  const filename = match ? match[1] : `WoundWatch_Report_${photoId}.pdf`;
  const url = window.URL.createObjectURL(new Blob([res.data], { type: 'application/pdf' }));
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  setTimeout(() => window.URL.revokeObjectURL(url), 2000);
};

// Notifications
export const getNotifications = (phone) => API.get(`/api/notifications/${phone}`);

// Mark read — backend uses POST not PUT
export const markRead = (id) => API.post(`/api/notifications/read/${id}`);

// Chat
export const sendChat = (phone, message, lang = 'en') => {
  const fd = new FormData();
  fd.append('phone', phone);
  fd.append('message', message);
  fd.append('lang', lang);
  return API.post('/api/chat', fd);
};

// Profile
export const getProfile = (phone) => API.get(`/api/patient-profile/${phone}`);

export const updateProfile = (phone, data) => {
  const fd = new FormData();
  fd.append('phone', phone);
  Object.entries(data).forEach(([k, v]) => { if (v) fd.append(k, v); });
  return API.post('/api/patient-profile', fd);
};

export default API;
