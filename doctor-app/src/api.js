import axios from 'axios';

const BASE = process.env.REACT_APP_API_URL || window.API_BASE || 'http://localhost:8000';

const API = axios.create({ baseURL: BASE });

// Doctor login — backend expects Form data
export const doctorLogin = (doctor_id, password) => {
  const fd = new FormData();
  fd.append('doctor_id', doctor_id);
  fd.append('password', password);
  return API.post('/auth/doctor-login', fd);
};

// Get all patients (no doctor_id filter in backend)
export const getPatients = () => API.get('/api/patients');

// Get patient detail
export const getPatientDetail = (phone) => API.get(`/api/patient-detail/${phone}`);

// Get dashboard stats
export const getStats = () => API.get('/api/stats');

// Add doctor notes — backend expects Form data with field "notes"
export const addDoctorNotes = (phone, doctor_id, note) => {
  const fd = new FormData();
  fd.append('phone', phone);
  fd.append('doctor_id', doctor_id);
  fd.append('notes', note);
  return API.post('/api/doctor-notes', fd);
};

// Review one wound photo — assessment is GREEN / YELLOW / RED
export const reviewPhoto = (photo_id, doctor_id, review) => {
  const fd = new FormData();
  fd.append('photo_id', photo_id);
  fd.append('doctor_id', doctor_id);
  fd.append('assessment', review.assessment);
  fd.append('findings', review.findings || '');
  fd.append('advice', review.advice || '');
  fd.append('medications', review.medications || '');
  fd.append('followup_date', review.followup_date || '');
  return API.post('/api/review-photo', fd);
};

// PDF for one reviewed photo (inline = open in browser tab instead of download)
export const reviewReportUrl = (photo_id, inline = true) =>
  `${BASE}/api/review-report/${photo_id}${inline ? '?inline=true' : ''}`;

export const photoUrl = (filename) => `${BASE}/uploads/${filename}`;

// Get notifications for doctor
export const getNotifications = (doctor_id) =>
  API.get(`/api/notifications/${doctor_id}`, { params: { target_type: 'doctor' } });

// Mark notification as read — backend uses POST not PUT
export const markRead = (id) => API.post(`/api/notifications/read/${id}`);

export default API;
