import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { getPatientDetail, addDoctorNotes, reviewReportUrl } from '../api';
import ReviewModal from '../components/ReviewModal';
import CompareSlider from '../components/CompareSlider';

function PatientDetailPage({ doctor }) {
  const { phone } = useParams();
  const nav = useNavigate();
  const [patient, setPatient] = useState(null);
  const [loading, setLoading] = useState(true);
  const [note, setNote] = useState('');
  const [saving, setSaving] = useState(false);
  const [reviewIndex, setReviewIndex] = useState(null);

  const handleReviewSaved = (updated) => {
    setPatient(prev => ({
      ...prev,
      photos: prev.photos.map(p => (p.id === updated.id ? updated : p))
    }));
  };

  useEffect(() => {
    getPatientDetail(phone).then(res => {
      setPatient(res.data);
      setLoading(false);
    }).catch(() => setLoading(false));
  }, [phone]);

  const riskColor = { GREEN: '#2BA84A', YELLOW: '#E89B2C', RED: '#D64545' };
  const riskBg = { GREEN: '#E8F8EC', YELLOW: '#FFF5E5', RED: '#FDEAEA' };
  const riskLabel = { GREEN: 'Healing Well', YELLOW: 'Monitor Closely', RED: 'High Risk' };

  const handleNote = async () => {
    if (!note.trim()) return;
    setSaving(true);
    try {
      await addDoctorNotes(phone, doctor.doctor_id, note);
      setNote('');
      // Refresh
      const res = await getPatientDetail(phone);
      setPatient(res.data);
    } catch {}
    setSaving(false);
  };

  // SVG chart
  const renderTrendChart = (photos) => {
    if (!photos || photos.length < 2) return null;
    const data = [...photos].reverse().slice(-12);
    const w = 500, h = 160, pad = 30;
    const stepX = (w - pad * 2) / (data.length - 1);
    const points = data.map((p, i) => ({
      x: pad + i * stepX,
      y: pad + (1 - p.risk_score) * (h - pad * 2),
      level: p.risk_level,
      score: p.risk_score,
      date: new Date(p.uploaded_at).toLocaleDateString('en-IN', { day: 'numeric', month: 'short' })
    }));
    const path = points.map((p, i) => (i === 0 ? `M${p.x},${p.y}` : `L${p.x},${p.y}`)).join(' ');
    const area = path + ` L${points[points.length-1].x},${h - pad} L${points[0].x},${h - pad} Z`;

    return (
      <svg viewBox={`0 0 ${w} ${h + 15}`} style={{ width: '100%', height: 'auto' }}>
        <defs>
          <linearGradient id="trendGrad" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="#7F79B6" stopOpacity="0.15" />
            <stop offset="100%" stopColor="#7F79B6" stopOpacity="0" />
          </linearGradient>
        </defs>
        {[0, 0.25, 0.5, 0.75, 1].map(v => {
          const y = pad + (1 - v) * (h - pad * 2);
          return <line key={v} x1={pad} y1={y} x2={w-pad} y2={y} stroke="#E8E7F0" strokeWidth="1" strokeDasharray="3,3" />;
        })}
        <path d={area} fill="url(#trendGrad)" />
        <path d={path} fill="none" stroke="#7F79B6" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" />
        {points.map((p, i) => (
          <g key={i}>
            <circle cx={p.x} cy={p.y} r="5" fill={riskColor[p.level] || '#7F79B6'} stroke="#fff" strokeWidth="2" />
            <text x={p.x} y={h + 10} fontSize="8" fill="#8C8AAE" textAnchor="middle">{p.date}</text>
          </g>
        ))}
      </svg>
    );
  };

  if (loading) return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
      {[1,2,3].map(i => <div key={i} style={{ height: '120px', borderRadius: '20px' }} className="skeleton" />)}
    </div>
  );

  if (!patient) return (
    <div style={{ textAlign: 'center', padding: '60px', color: '#8C8AAE' }}>
      <p style={{ fontSize: '40px', marginBottom: '12px' }}>❌</p>
      <p style={{ fontWeight: 700 }}>Patient not found</p>
      <button onClick={() => nav('/patients')} style={{
        marginTop: '16px', background: '#F5F4FA', color: '#2F2B6E', borderRadius: '10px'
      }}>← Back to Patients</button>
    </div>
  );

  const info = patient.patient || {};
  const photos = patient.photos || [];
  const notes = patient.notes || [];
  const latest = photos[0];
  const pendingCount = photos.filter(p => !p.report_available).length;
  const firstPending = photos.findIndex(p => !p.report_available);

  return (
    <div>
      {reviewIndex !== null && (
        <ReviewModal
          photos={photos}
          index={reviewIndex}
          doctor={doctor}
          onClose={() => setReviewIndex(null)}
          onNavigate={setReviewIndex}
          onSaved={handleReviewSaved}
        />
      )}

      {/* Back + Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
        <button onClick={() => nav('/patients')} style={{
          background: '#F5F4FA', color: '#7F79B6', borderRadius: '10px',
          padding: '8px 16px', fontSize: '13px', fontWeight: 600
        }}>← Back</button>
        <button
          onClick={() => {
            const base = window.API_BASE || 'http://localhost:8000';
            window.open(`${base}/api/report/${phone}`, '_blank');
          }}
          style={{
            display: 'flex', alignItems: 'center', gap: '6px',
            padding: '8px 16px', borderRadius: '12px', border: 'none', cursor: 'pointer',
            background: 'linear-gradient(135deg, #2F2B6E, #7F79B6)',
            color: '#fff', fontSize: '13px', fontWeight: 700,
            boxShadow: '0 4px 14px rgba(47,43,110,0.25)',
            transition: 'all 0.2s ease'
          }}
        >
          📄 Download PDF Report
        </button>
      </div>

      <div style={{
        display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '20px',
        animation: 'fadeInUp 0.4s ease forwards'
      }}>
        {/* Patient Info Card */}
        <div style={{
          background: '#fff', borderRadius: '20px', padding: '24px',
          boxShadow: '0 2px 12px rgba(47,43,110,0.05)', gridColumn: latest ? 'span 1' : 'span 2'
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '14px', marginBottom: '18px' }}>
            <div style={{
              width: '52px', height: '52px', borderRadius: '16px',
              background: `linear-gradient(135deg, ${riskColor[latest?.risk_level] || '#7F79B6'}22, ${riskColor[latest?.risk_level] || '#7F79B6'}11)`,
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              fontSize: '22px', fontWeight: 700, color: riskColor[latest?.risk_level] || '#7F79B6'
            }}>
              {(info.name || info.phone || '?')[0].toUpperCase()}
            </div>
            <div>
              <h2 style={{ fontSize: '20px', fontWeight: 800 }}>{info.name || 'Patient'}</h2>
              <p style={{ color: '#8C8AAE', fontSize: '13px' }}>{info.phone}</p>
            </div>
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px' }}>
            <div style={{ background: '#F7F6FB', borderRadius: '12px', padding: '12px' }}>
              <p style={{ fontSize: '11px', color: '#8C8AAE', fontWeight: 600 }}>Age</p>
              <p style={{ fontSize: '16px', fontWeight: 700, color: '#2F2B6E' }}>{info.age || '--'}</p>
            </div>
            <div style={{ background: '#F7F6FB', borderRadius: '12px', padding: '12px' }}>
              <p style={{ fontSize: '11px', color: '#8C8AAE', fontWeight: 600 }}>Total Scans</p>
              <p style={{ fontSize: '16px', fontWeight: 700, color: '#2F2B6E' }}>{photos.length}</p>
            </div>
          </div>
        </div>

        {/* Current Risk Card */}
        {latest && (
          <div style={{
            background: riskBg[latest.risk_level] || '#F5F4FA',
            borderRadius: '20px', padding: '24px',
            border: `2px solid ${riskColor[latest.risk_level] || '#E8E7F0'}`,
            display: 'flex', flexDirection: 'column', justifyContent: 'center',
            textAlign: 'center'
          }}>
            <p style={{ fontSize: '12px', fontWeight: 600, color: '#8C8AAE', textTransform: 'uppercase', letterSpacing: '0.5px' }}>
              Current Status
            </p>
            <p style={{ fontSize: '40px', fontWeight: 900, color: riskColor[latest.risk_level], marginTop: '8px' }}>
              {(latest.risk_score * 100).toFixed(0)}%
            </p>
            <span style={{
              display: 'inline-block', padding: '4px 14px', borderRadius: '8px',
              background: `${riskColor[latest.risk_level]}20`,
              color: riskColor[latest.risk_level],
              fontSize: '13px', fontWeight: 700, marginTop: '8px', alignSelf: 'center'
            }}>
              {riskLabel[latest.risk_level] || latest.risk_level}
            </span>
          </div>
        )}
      </div>

      {/* Trend Chart */}
      {photos.length >= 2 && (
        <div style={{
          background: '#fff', borderRadius: '20px', padding: '24px', marginTop: '20px',
          boxShadow: '0 2px 12px rgba(47,43,110,0.05)',
          animation: 'fadeInUp 0.4s 0.1s ease forwards', opacity: 0
        }}>
          <p style={{ fontWeight: 700, fontSize: '15px', color: '#2F2B6E', marginBottom: '12px' }}>
            📈 Risk Score Trend
          </p>
          {renderTrendChart(photos)}
        </div>
      )}

      {/* Before / After comparison */}
      {photos.length >= 2 ? (
        <div style={{
          background: '#fff', borderRadius: '20px', padding: '24px', marginTop: '20px',
          boxShadow: '0 2px 12px rgba(47,43,110,0.05)',
          animation: 'fadeInUp 0.4s 0.14s ease forwards', opacity: 0
        }}>
          <div style={{ marginBottom: '14px' }}>
            <p style={{ fontWeight: 700, fontSize: '15px', color: '#2F2B6E' }}>🔍 Wound Comparison — colour drift over time</p>
            <p style={{ fontSize: '12px', color: '#8C8AAE', marginTop: '2px' }}>
              Drag the handle to compare two days. Changes in every AI metric are shown below.
            </p>
          </div>
          <CompareSlider photos={photos} />
        </div>
      ) : photos.length === 1 ? (
        <div style={{
          background: '#fff', borderRadius: '20px', padding: '18px 24px', marginTop: '20px',
          boxShadow: '0 2px 12px rgba(47,43,110,0.05)', color: '#8C8AAE', fontSize: '13px'
        }}>
          🔍 Wound comparison appears once the patient has uploaded 2 or more photos.
        </div>
      ) : null}

      {/* Photo Timeline */}
      {photos.length > 0 && (
        <div style={{
          background: '#fff', borderRadius: '20px', padding: '24px', marginTop: '20px',
          boxShadow: '0 2px 12px rgba(47,43,110,0.05)',
          animation: 'fadeInUp 0.4s 0.18s ease forwards', opacity: 0
        }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '14px' }}>
            <div>
              <p style={{ fontWeight: 700, fontSize: '15px', color: '#2F2B6E' }}>📷 Wound Photos</p>
              <p style={{ fontSize: '12px', color: '#8C8AAE', marginTop: '2px' }}>
                Click a photo to review it. The patient gets a PDF report for each reviewed photo.
              </p>
            </div>
            {pendingCount > 0 ? (
              <button onClick={() => setReviewIndex(firstPending)} style={{
                background: 'linear-gradient(135deg, #D64545, #E89B2C)', padding: '9px 16px', fontSize: '13px'
              }}>
                Review {pendingCount} pending →
              </button>
            ) : (
              <span style={{ fontSize: '12px', fontWeight: 700, color: '#2BA84A', background: '#E8F8EC', padding: '6px 12px', borderRadius: '8px' }}>
                ✓ All photos reviewed
              </span>
            )}
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(140px, 1fr))', gap: '10px' }}>
            {photos.map((p, i) => (
              <div key={p.id || i}
                onClick={() => setReviewIndex(i)}
                title={p.report_available ? 'Reviewed — click to view or edit' : 'Click to review'}
                style={{
                  position: 'relative', borderRadius: '14px', overflow: 'hidden', cursor: 'pointer',
                  outline: p.report_available ? 'none' : '2px dashed #E89B2C', outlineOffset: '-2px',
                  transition: 'transform 0.2s ease, box-shadow 0.2s ease'
                }}
                onMouseEnter={e => { e.currentTarget.style.transform = 'translateY(-3px)'; e.currentTarget.style.boxShadow = '0 8px 24px rgba(47,43,110,0.18)'; }}
                onMouseLeave={e => { e.currentTarget.style.transform = 'none'; e.currentTarget.style.boxShadow = 'none'; }}
              >
                <img
                  src={`${window.API_BASE || 'http://localhost:8000'}/uploads/${p.filename}`}
                  alt="Wound"
                  style={{ width: '100%', height: '130px', objectFit: 'cover', display: 'block' }}
                />
                <div style={{
                  position: 'absolute', top: '6px', left: '6px', padding: '2px 7px', borderRadius: '6px',
                  fontSize: '10px', fontWeight: 700,
                  background: p.report_available ? (riskColor[p.doctor_assessment] || '#2BA84A') : 'rgba(255,255,255,0.92)',
                  color: p.report_available ? '#fff' : '#E89B2C'
                }}>
                  {p.report_available ? '✓ Reviewed' : 'Needs review'}
                </div>
                {p.report_available && (
                  <a href={reviewReportUrl(p.id, true)} target="_blank" rel="noreferrer"
                    onClick={e => e.stopPropagation()} title="Open PDF report"
                    style={{
                      position: 'absolute', top: '6px', right: '6px', padding: '2px 6px', borderRadius: '6px',
                      background: 'rgba(255,255,255,0.92)', fontSize: '11px', textDecoration: 'none'
                    }}>📄</a>
                )}
                <div style={{
                  position: 'absolute', bottom: '0', left: '0', right: '0',
                  background: 'linear-gradient(transparent, rgba(0,0,0,0.6))',
                  padding: '8px', color: '#fff'
                }}>
                  <div style={{
                    display: 'inline-flex', padding: '2px 6px', borderRadius: '4px',
                    background: riskColor[p.risk_level], fontSize: '10px', fontWeight: 700
                  }}>
                    {(p.risk_score * 100).toFixed(0)}%
                  </div>
                  <p style={{ fontSize: '9px', marginTop: '2px', opacity: 0.8 }}>
                    {new Date(p.uploaded_at).toLocaleDateString('en-IN', { day: 'numeric', month: 'short' })}
                  </p>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Doctor Notes */}
      <div style={{
        background: '#fff', borderRadius: '20px', padding: '24px', marginTop: '20px',
        boxShadow: '0 2px 12px rgba(47,43,110,0.05)',
        animation: 'fadeInUp 0.4s 0.25s ease forwards', opacity: 0
      }}>
        <p style={{ fontWeight: 700, fontSize: '15px', color: '#2F2B6E', marginBottom: '14px' }}>
          📝 Doctor Notes
        </p>

        {/* Add note */}
        <div style={{ display: 'flex', gap: '10px', marginBottom: '16px' }}>
          <textarea value={note} onChange={e => setNote(e.target.value)}
            placeholder="Add a clinical note..."
            rows={2}
            style={{ flex: 1, borderRadius: '12px', resize: 'none', fontSize: '13px' }}
          />
          <button onClick={handleNote} disabled={saving || !note.trim()} style={{
            padding: '12px 20px', borderRadius: '12px',
            background: note.trim() ? 'linear-gradient(135deg, #2F2B6E, #7F79B6)' : '#E8E7F0',
            color: note.trim() ? '#fff' : '#8C8AAE', alignSelf: 'flex-end'
          }}>
            {saving ? '...' : 'Add'}
          </button>
        </div>

        {/* Notes list */}
        {notes.length === 0 ? (
          <p style={{ color: '#8C8AAE', fontSize: '13px', textAlign: 'center', padding: '20px' }}>
            No notes yet. Add your observations above.
          </p>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
            {notes.map((n, i) => (
              <div key={i} style={{
                padding: '12px 16px', background: '#F7F6FB', borderRadius: '12px',
                borderLeft: '3px solid #7F79B6'
              }}>
                <p style={{ fontSize: '13px', color: '#333', lineHeight: '1.5' }}>{n.note}</p>
                <p style={{ fontSize: '11px', color: '#8C8AAE', marginTop: '6px' }}>
                  {n.doctor_id} · {new Date(n.created_at).toLocaleDateString('en-IN', {
                    day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit'
                  })}
                </p>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

export default PatientDetailPage;
