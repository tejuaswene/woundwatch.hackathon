import React, { useState, useEffect } from 'react';
import { getHistory, downloadReviewReport } from '../api';
import RiskBadge from '../components/RiskBadge';

const doctorVerdict = {
  GREEN: { text: 'Healing well', color: '#2BA84A', bg: '#E8F8EC', icon: '✅' },
  YELLOW: { text: 'Monitor closely', color: '#E89B2C', bg: '#FFF5E5', icon: '⚠️' },
  RED: { text: 'Visit hospital', color: '#D64545', bg: '#FDEAEA', icon: '🏥' },
};

// Doctor review strip shown under each scan
function DoctorReview({ p, phone, compact }) {
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState('');

  if (!p.report_available) {
    return (
      <div style={{
        marginTop: '10px', padding: '8px 10px', borderRadius: '10px', background: '#F7F6FB',
        fontSize: '11px', color: '#8C8AAE', fontWeight: 600, display: 'flex', alignItems: 'center', gap: '6px'
      }}>
        ⏳ Waiting for doctor review — your report will appear here
      </div>
    );
  }

  const v = doctorVerdict[p.doctor_assessment] || doctorVerdict.YELLOW;
  const download = async () => {
    setBusy(true); setErr('');
    try { await downloadReviewReport(p.id, phone); }
    catch { setErr('Download failed. Check your connection and try again.'); }
    setBusy(false);
  };

  return (
    <div style={{ marginTop: '10px', padding: '10px 12px', borderRadius: '12px', background: v.bg, border: `1px solid ${v.color}33` }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: '8px' }}>
        <div style={{ minWidth: 0 }}>
          <p style={{ fontSize: '12px', fontWeight: 800, color: v.color }}>{v.icon} Doctor: {v.text}</p>
          {!compact && p.doctor_advice && (
            <p style={{ fontSize: '11px', color: '#55537A', marginTop: '3px', lineHeight: 1.4 }}>{p.doctor_advice}</p>
          )}
          {!compact && p.followup_date && (
            <p style={{ fontSize: '11px', color: '#55537A', marginTop: '3px' }}>
              📅 Follow-up: {new Date(p.followup_date).toLocaleDateString('en-IN', { day: 'numeric', month: 'short', year: 'numeric' })}
            </p>
          )}
        </div>
        <button onClick={download} disabled={busy} style={{
          flexShrink: 0, padding: '8px 12px', borderRadius: '10px', border: 'none', cursor: 'pointer',
          background: '#2F2B6E', color: '#fff', fontSize: '11px', fontWeight: 700, whiteSpace: 'nowrap'
        }}>
          {busy ? '…' : '⬇ PDF'}
        </button>
      </div>
      {err && <p style={{ fontSize: '11px', color: '#D64545', marginTop: '6px' }}>{err}</p>}
    </div>
  );
}

function HistoryPage({ user }) {
  const [photos, setPhotos] = useState([]);
  const [loading, setLoading] = useState(true);
  const [view, setView] = useState('progress'); // progress | list | chart
  const reportsReady = photos.filter(p => p.report_available).length;

  useEffect(() => {
    getHistory(user.phone).then(res => {
      setPhotos(res.data);
      setLoading(false);
    }).catch(() => setLoading(false));
  }, [user.phone]);

  const riskColor = { GREEN: '#2BA84A', YELLOW: '#E89B2C', RED: '#D64545' };
  const riskBg = { GREEN: '#E8F8EC', YELLOW: '#FFF5E5', RED: '#FDEAEA' };
  const riskLabel = { GREEN: 'Healing', YELLOW: 'Monitor', RED: 'Alert' };

  // Calculate healing trend
  const getTrend = () => {
    if (photos.length < 2) return null;
    const latest = photos[0].risk_score;
    const prev = photos[1].risk_score;
    if (latest < prev - 0.05) return { dir: 'improving', icon: '📈', color: '#2BA84A', text: 'Improving' };
    if (latest > prev + 0.05) return { dir: 'worsening', icon: '📉', color: '#D64545', text: 'Worsening' };
    return { dir: 'stable', icon: '➡️', color: '#E89B2C', text: 'Stable' };
  };

  const trend = getTrend();

  // Chart rendering
  const renderChart = () => {
    if (photos.length < 2) return (
      <div style={{ textAlign: 'center', padding: '40px', color: '#8C8AAE' }}>
        <p style={{ fontSize: '14px', fontWeight: 600 }}>Need at least 2 scans for chart</p>
      </div>
    );

    const data = [...photos].reverse().slice(-10);
    const maxScore = 100;
    const w = 340, h = 180, pad = 30;
    const stepX = (w - pad * 2) / (data.length - 1);

    const points = data.map((p, i) => ({
      x: pad + i * stepX,
      y: pad + (1 - p.risk_score) * (h - pad * 2),
      score: p.risk_score,
      level: p.risk_level,
      date: new Date(p.uploaded_at).toLocaleDateString('en-IN', { day: 'numeric', month: 'short' })
    }));

    const linePath = points.map((p, i) =>
      i === 0 ? `M${p.x},${p.y}` : `L${p.x},${p.y}`
    ).join(' ');

    const areaPath = linePath + ` L${points[points.length-1].x},${h - pad} L${points[0].x},${h - pad} Z`;

    return (
      <div style={{ background: '#fff', borderRadius: '20px', padding: '20px', boxShadow: '0 2px 12px rgba(47,43,110,0.06)' }}>
        <p style={{ fontWeight: 700, fontSize: '14px', color: '#2F2B6E', marginBottom: '16px' }}>
          📈 Risk Score Trend
        </p>
        <svg viewBox={`0 0 ${w} ${h + 20}`} style={{ width: '100%', height: 'auto' }}>
          {/* Grid lines */}
          {[0, 0.25, 0.5, 0.75, 1].map(v => {
            const y = pad + (1 - v) * (h - pad * 2);
            return (
              <g key={v}>
                <line x1={pad} y1={y} x2={w - pad} y2={y}
                  stroke="#E8E7F0" strokeWidth="1" strokeDasharray="4,4" />
                <text x={pad - 6} y={y + 4} fontSize="9" fill="#8C8AAE" textAnchor="end">
                  {(v * 100).toFixed(0)}
                </text>
              </g>
            );
          })}

          {/* Area fill */}
          <defs>
            <linearGradient id="areaGrad" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#7F79B6" stopOpacity="0.2" />
              <stop offset="100%" stopColor="#7F79B6" stopOpacity="0" />
            </linearGradient>
          </defs>
          <path d={areaPath} fill="url(#areaGrad)" />

          {/* Line */}
          <path d={linePath} fill="none" stroke="#7F79B6" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" />

          {/* Data points */}
          {points.map((p, i) => (
            <g key={i}>
              <circle cx={p.x} cy={p.y} r="5" fill={riskColor[p.level] || '#7F79B6'} stroke="#fff" strokeWidth="2" />
              <text x={p.x} y={h + 10} fontSize="8" fill="#8C8AAE" textAnchor="middle">{p.date}</text>
            </g>
          ))}
        </svg>
      </div>
    );
  };

  return (
    <div style={{ padding: '20px', paddingTop: '16px', maxWidth: '480px', margin: '0 auto' }}>
      {/* Header */}
      <div style={{
        display: 'flex', justifyContent: 'space-between', alignItems: 'center',
        marginBottom: '16px', animation: 'fadeInUp 0.4s ease forwards'
      }}>
        <h2 style={{ fontSize: '24px', fontWeight: 900, letterSpacing: '-0.03em' }}>
          Wound History
        </h2>
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <button
            onClick={() => {
              const base = window.API_BASE || 'http://localhost:8000';
              window.open(`${base}/api/report/${user.phone}`, '_blank');
            }}
            style={{
              display: 'flex', alignItems: 'center', gap: '6px',
              padding: '8px 14px', borderRadius: '12px', border: 'none', cursor: 'pointer',
              background: 'linear-gradient(135deg, #2F2B6E, #7F79B6)',
              color: '#fff', fontSize: '12px', fontWeight: 700,
              boxShadow: '0 4px 14px rgba(47,43,110,0.25)',
              transition: 'all 0.2s ease'
            }}
          >
            📄 Full Report
          </button>
          <span style={{ fontSize: '12px', color: '#8C8AAE', fontWeight: 600 }}>
            {photos.length} scan{photos.length !== 1 ? 's' : ''}
          </span>
        </div>
      </div>

      {/* View Tabs */}
      <div style={{
        display: 'flex', gap: '4px', background: '#F5F4FA', borderRadius: '12px',
        padding: '3px', marginBottom: '16px', animation: 'fadeInUp 0.4s 0.05s ease forwards', opacity: 0
      }}>
        {[
          { key: 'progress', icon: '🏥', label: 'Progress' },
          { key: 'list', icon: '📋', label: 'All Scans' },
          { key: 'chart', icon: '📈', label: 'Chart' },
        ].map(t => (
          <button key={t.key} onClick={() => setView(t.key)} style={{
            flex: 1, padding: '10px', fontSize: '12px', fontWeight: 600,
            borderRadius: '10px', border: 'none', cursor: 'pointer',
            background: view === t.key ? '#fff' : 'transparent',
            color: view === t.key ? '#2F2B6E' : '#8C8AAE',
            boxShadow: view === t.key ? '0 2px 8px rgba(47,43,110,0.08)' : 'none',
            transition: 'all 0.2s ease',
            display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '4px'
          }}>
            <span style={{ fontSize: '14px' }}>{t.icon}</span> {t.label}
          </button>
        ))}
      </div>

      {loading ? (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
          {[1, 2, 3].map(i => (
            <div key={i} style={{ height: '80px', borderRadius: '16px' }} className="skeleton" />
          ))}
        </div>
      ) : photos.length === 0 ? (
        <div style={{
          textAlign: 'center', padding: '60px 20px',
          animation: 'fadeInUp 0.5s ease forwards'
        }}>
          <div style={{
            width: '72px', height: '72px', borderRadius: '22px', margin: '0 auto 16px',
            background: 'linear-gradient(135deg, #EEEDFA, #F5F4FA)',
            display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '32px'
          }}>📊</div>
          <p style={{ fontWeight: 700, color: '#2F2B6E' }}>No scans yet</p>
          <p style={{ color: '#8C8AAE', fontSize: '13px', marginTop: '6px' }}>
            Upload your first wound photo to start tracking
          </p>
        </div>
      ) : (
        <div style={{ animation: 'fadeInUp 0.4s 0.1s ease forwards', opacity: 0 }}>
          {/* Doctor reports summary */}
          {reportsReady > 0 && view !== 'chart' && (
            <div style={{
              background: 'linear-gradient(135deg, #2F2B6E, #7F79B6)', color: '#fff',
              borderRadius: '16px', padding: '14px 16px', marginBottom: '14px',
              display: 'flex', alignItems: 'center', gap: '12px'
            }}>
              <div style={{ fontSize: '26px' }}>🩺</div>
              <div>
                <p style={{ fontWeight: 800, fontSize: '14px' }}>
                  {reportsReady} doctor report{reportsReady !== 1 ? 's' : ''} ready
                </p>
                <p style={{ fontSize: '11px', opacity: 0.85, marginTop: '2px' }}>
                  Tap ⬇ PDF on a reviewed scan to download its report
                </p>
              </div>
            </div>
          )}

          {/* ===== PROGRESS VIEW ===== */}
          {view === 'progress' && (
            <>
              {/* Trend Banner */}
              {trend && (
                <div style={{
                  background: '#fff', borderRadius: '16px', padding: '18px',
                  marginBottom: '14px', boxShadow: '0 2px 10px rgba(47,43,110,0.06)',
                  display: 'flex', alignItems: 'center', gap: '14px'
                }}>
                  <div style={{
                    width: '48px', height: '48px', borderRadius: '14px',
                    background: `${trend.color}15`, display: 'flex',
                    alignItems: 'center', justifyContent: 'center', fontSize: '24px'
                  }}>{trend.icon}</div>
                  <div>
                    <p style={{ fontWeight: 700, color: trend.color, fontSize: '16px' }}>
                      {trend.text}
                    </p>
                    <p style={{ fontSize: '12px', color: '#8C8AAE', marginTop: '2px' }}>
                      Compared to previous scan
                    </p>
                  </div>
                </div>
              )}

              {/* Timeline */}
              <div style={{ position: 'relative', paddingLeft: '24px' }}>
                {/* Vertical line */}
                <div style={{
                  position: 'absolute', left: '8px', top: '8px', bottom: '8px',
                  width: '2px', background: 'linear-gradient(to bottom, #7F79B6, #E8E7F0)'
                }} />

                {photos.slice(0, 8).map((p, i) => (
                  <div key={p.id || i} style={{
                    position: 'relative', marginBottom: '16px',
                    animation: `fadeInUp 0.4s ${i * 0.08}s ease forwards`, opacity: 0
                  }}>
                    {/* Dot */}
                    <div style={{
                      position: 'absolute', left: '-20px', top: '14px',
                      width: '14px', height: '14px', borderRadius: '50%',
                      background: riskColor[p.risk_level] || '#7F79B6',
                      border: '3px solid #F5F4FA', zIndex: 1
                    }} />

                    <div style={{
                      background: '#fff', borderRadius: '16px', padding: '16px',
                      boxShadow: '0 2px 10px rgba(47,43,110,0.06)'
                    }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                          <div style={{
                            padding: '4px 10px', borderRadius: '8px',
                            background: riskBg[p.risk_level] || '#F0EEFF',
                            color: riskColor[p.risk_level] || '#7F79B6',
                            fontSize: '11px', fontWeight: 700
                          }}>{riskLabel[p.risk_level] || p.risk_level}</div>
                          <span style={{ fontSize: '20px', fontWeight: 800, color: riskColor[p.risk_level] }}>
                            {(p.risk_score * 100).toFixed(0)}%
                          </span>
                        </div>
                        <p style={{ fontSize: '11px', color: '#8C8AAE', fontWeight: 500 }}>
                          {new Date(p.uploaded_at).toLocaleDateString('en-IN', {
                            day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit'
                          })}
                        </p>
                      </div>

                      {/* Mini metrics */}
                      <div style={{
                        display: 'flex', gap: '8px', marginTop: '10px'
                      }}>
                        {[
                          { label: 'Red', val: p.redness_index?.toFixed(0), color: '#D64545' },
                          { label: 'Swell', val: p.swelling_score?.toFixed(0), color: '#E89B2C' },
                          { label: 'Dev', val: p.color_deviation?.toFixed(0), color: '#7F79B6' },
                        ].map(m => (
                          <div key={m.label} style={{
                            flex: 1, padding: '6px', borderRadius: '8px',
                            background: '#F7F6FB', textAlign: 'center'
                          }}>
                            <p style={{ fontSize: '14px', fontWeight: 700, color: m.color }}>{m.val || '-'}</p>
                            <p style={{ fontSize: '9px', color: '#8C8AAE', fontWeight: 500 }}>{m.label}</p>
                          </div>
                        ))}
                      </div>

                      <DoctorReview p={p} phone={user.phone} />
                    </div>
                  </div>
                ))}
              </div>
            </>
          )}

          {/* ===== LIST VIEW ===== */}
          {view === 'list' && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
              {photos.map((p, i) => (
                <div key={p.id || i} style={{
                  background: '#fff', borderRadius: '16px', padding: '14px',
                  boxShadow: '0 2px 8px rgba(47,43,110,0.05)',
                  display: 'flex', gap: '12px', alignItems: 'center',
                  borderLeft: `4px solid ${riskColor[p.risk_level] || '#7F79B6'}`,
                  animation: `fadeInUp 0.3s ${i * 0.04}s ease forwards`, opacity: 0
                }}>
                  {/* Thumbnail */}
                  {p.filename && (
                    <img
                      src={`${window.API_BASE || 'http://localhost:8000'}/uploads/${p.filename}`}
                      alt="Wound"
                      style={{
                        width: '52px', height: '52px', borderRadius: '12px',
                        objectFit: 'cover', flexShrink: 0
                      }}
                    />
                  )}
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                      <RiskBadge level={p.risk_level} />
                      <p style={{ fontSize: '18px', fontWeight: 800, color: riskColor[p.risk_level] }}>
                        {(p.risk_score * 100).toFixed(0)}%
                      </p>
                    </div>
                    <p style={{ fontSize: '11px', color: '#8C8AAE', marginTop: '4px' }}>
                      {new Date(p.uploaded_at).toLocaleDateString('en-IN', {
                        day: 'numeric', month: 'short', year: 'numeric',
                        hour: '2-digit', minute: '2-digit'
                      })}
                    </p>
                    <DoctorReview p={p} phone={user.phone} compact />
                  </div>
                </div>
              ))}
            </div>
          )}

          {/* ===== CHART VIEW ===== */}
          {view === 'chart' && renderChart()}
        </div>
      )}
    </div>
  );
}

export default HistoryPage;
