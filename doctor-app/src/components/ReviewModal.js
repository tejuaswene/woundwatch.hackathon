import React, { useState, useEffect, useCallback } from 'react';
import { reviewPhoto, reviewReportUrl, photoUrl } from '../api';

const riskColor = { GREEN: '#2BA84A', YELLOW: '#E89B2C', RED: '#D64545' };
const riskBg = { GREEN: '#E8F8EC', YELLOW: '#FFF5E5', RED: '#FDEAEA' };
const aiLabel = { GREEN: 'Low risk', YELLOW: 'Moderate risk', RED: 'High risk' };

const ASSESSMENTS = [
  { key: 'GREEN', icon: '✅', title: 'Healing well', sub: 'Continue routine care' },
  { key: 'YELLOW', icon: '⚠️', title: 'Monitor', sub: 'Needs closer watch' },
  { key: 'RED', icon: '🏥', title: 'Visit hospital', sub: 'In-person check needed' },
];

const QUICK_FINDINGS = {
  GREEN: ['Wound clean and dry', 'Edges well apposed', 'No signs of infection'],
  YELLOW: ['Mild erythema around incision', 'Slight serous discharge', 'Mild swelling at wound edge'],
  RED: ['Spreading redness beyond wound margin', 'Purulent discharge noted', 'Wound edges separating'],
};

const QUICK_ADVICE = {
  GREEN: 'Continue daily dressing. Keep the wound dry. Upload a photo every day.',
  YELLOW: 'Change dressing twice daily. Watch for fever or increasing pain. Upload a new photo tomorrow.',
  RED: 'Please visit the hospital within 24 hours for an in-person wound check. Do not apply any home remedies.',
};

const emptyReview = { assessment: '', findings: '', advice: '', medications: '', followup_date: '' };

function fmt(d, opts) {
  return new Date(d).toLocaleDateString('en-IN', opts || { day: 'numeric', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit' });
}

function ReviewModal({ photos, index, doctor, onClose, onSaved, onNavigate }) {
  const photo = photos[index];
  const [form, setForm] = useState(emptyReview);
  const [showHeatmap, setShowHeatmap] = useState(false);
  const [heatmapOk, setHeatmapOk] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');
  const [savedNow, setSavedNow] = useState(false);

  // Load existing review (if any) when photo changes
  useEffect(() => {
    if (!photo) return;
    setForm({
      assessment: photo.doctor_assessment || '',
      findings: photo.doctor_findings || photo.doctor_notes || '',
      advice: photo.doctor_advice || '',
      medications: photo.doctor_medications || '',
      followup_date: photo.followup_date || '',
    });
    setShowHeatmap(false);
    setHeatmapOk(true);
    setError('');
    setSavedNow(false);
    // reload only when switching to a different photo (not when this one is updated after save)
  }, [photo?.id]);

  const go = useCallback((dir) => {
    const next = index + dir;
    if (next >= 0 && next < photos.length) onNavigate(next);
  }, [index, photos.length, onNavigate]);

  useEffect(() => {
    const onKey = (e) => {
      if (['INPUT', 'TEXTAREA'].includes(e.target.tagName)) return;
      if (e.key === 'Escape') onClose();
      if (e.key === 'ArrowLeft') go(1);   // older
      if (e.key === 'ArrowRight') go(-1); // newer
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [go, onClose]);

  if (!photo) return null;

  const set = (k, v) => { setForm(f => ({ ...f, [k]: v })); setSavedNow(false); };

  const pickAssessment = (key) => {
    setForm(f => ({
      ...f,
      assessment: key,
      // pre-fill advice only if doctor hasn't written any yet (or it is one of our defaults)
      advice: !f.advice || Object.values(QUICK_ADVICE).includes(f.advice) ? QUICK_ADVICE[key] : f.advice,
    }));
    setSavedNow(false);
  };

  const addFinding = (txt) => {
    setForm(f => ({ ...f, findings: f.findings ? `${f.findings.replace(/\.?\s*$/, '')}. ${txt}.` : `${txt}.` }));
    setSavedNow(false);
  };

  const save = async () => {
    if (!form.assessment) return setError('Choose your assessment first.');
    if (!form.findings.trim()) return setError('Please write your findings.');
    setSaving(true); setError('');
    try {
      const res = await reviewPhoto(photo.id, doctor.doctor_id, form);
      setSavedNow(true);
      onSaved(res.data.photo);
    } catch (e) {
      setError(e?.response?.data?.detail || 'Could not save review. Is the backend running?');
    }
    setSaving(false);
  };

  const imgSrc = showHeatmap ? photoUrl(`heatmap_${photo.filename}`) : photoUrl(photo.filename);
  const reviewed = photo.report_available;

  const label = { fontSize: '12px', fontWeight: 700, color: '#2F2B6E', marginBottom: '6px', display: 'block' };
  const chip = {
    padding: '5px 10px', fontSize: '11px', fontWeight: 600, borderRadius: '8px',
    background: '#F5F4FA', color: '#7F79B6', border: '1px solid #E8E7F0'
  };

  return (
    <div onClick={onClose} style={{
      position: 'fixed', inset: 0, zIndex: 1000, background: 'rgba(29,26,78,0.55)',
      backdropFilter: 'blur(4px)', display: 'flex', alignItems: 'center', justifyContent: 'center',
      padding: '24px', animation: 'fadeIn 0.2s ease'
    }}>
      <div onClick={e => e.stopPropagation()} style={{
        background: '#fff', borderRadius: '24px', width: '100%', maxWidth: '1100px',
        maxHeight: '92vh', overflow: 'hidden', display: 'flex', flexDirection: 'column',
        boxShadow: '0 24px 64px rgba(29,26,78,0.35)', animation: 'scaleIn 0.25s ease'
      }}>
        {/* Header */}
        <div style={{
          display: 'flex', alignItems: 'center', justifyContent: 'space-between',
          padding: '16px 24px', borderBottom: '1px solid #E8E7F0'
        }}>
          <div>
            <p style={{ fontSize: '17px', fontWeight: 800, color: '#2F2B6E' }}>Review wound photo</p>
            <p style={{ fontSize: '12px', color: '#8C8AAE' }}>
              Photo {photos.length - index} of {photos.length} · {fmt(photo.uploaded_at)}
              {reviewed && <span style={{ color: '#2BA84A', fontWeight: 700 }}> · ✓ Reviewed</span>}
            </p>
          </div>
          <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
            <button onClick={() => go(1)} disabled={index >= photos.length - 1} title="Older photo (←/→ keys)"
              style={{ background: '#F5F4FA', color: '#2F2B6E', padding: '8px 12px', fontSize: '13px' }}>← Older</button>
            <button onClick={() => go(-1)} disabled={index <= 0} title="Newer photo"
              style={{ background: '#F5F4FA', color: '#2F2B6E', padding: '8px 12px', fontSize: '13px' }}>Newer →</button>
            <button onClick={onClose} title="Close (Esc)"
              style={{ background: '#F5F4FA', color: '#8C8AAE', padding: '8px 12px', fontSize: '14px' }}>✕</button>
          </div>
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: '1.1fr 1fr', overflow: 'auto', flex: 1 }}>
          {/* LEFT: image + AI */}
          <div style={{ padding: '20px 24px', background: '#FAFAFD', borderRight: '1px solid #E8E7F0' }}>
            <div style={{
              position: 'relative', borderRadius: '16px', overflow: 'hidden', background: '#1D1A4E',
              height: '380px', display: 'flex', alignItems: 'center', justifyContent: 'center'
            }}>
              <img
                src={imgSrc} alt="Wound"
                onError={() => { if (showHeatmap) { setHeatmapOk(false); setShowHeatmap(false); } }}
                style={{ maxWidth: '100%', maxHeight: '100%', objectFit: 'contain' }}
              />
              <a href={imgSrc} target="_blank" rel="noreferrer" style={{
                position: 'absolute', top: '10px', right: '10px', padding: '6px 10px', borderRadius: '8px',
                background: 'rgba(0,0,0,0.5)', color: '#fff', fontSize: '11px', fontWeight: 600, textDecoration: 'none'
              }}>⤢ Full size</a>
            </div>
            {heatmapOk && (
              <div style={{ display: 'flex', gap: '4px', background: '#EEEDFA', borderRadius: '10px', padding: '3px', marginTop: '10px' }}>
                {[{ k: false, l: 'Original' }, { k: true, l: 'AI heatmap' }].map(t => (
                  <button key={t.l} onClick={() => setShowHeatmap(t.k)} style={{
                    flex: 1, padding: '7px', fontSize: '12px', borderRadius: '8px',
                    background: showHeatmap === t.k ? '#fff' : 'transparent',
                    color: showHeatmap === t.k ? '#2F2B6E' : '#8C8AAE',
                    boxShadow: showHeatmap === t.k ? '0 2px 6px rgba(47,43,110,0.08)' : 'none'
                  }}>{t.l}</button>
                ))}
              </div>
            )}

            <p style={{ ...label, marginTop: '18px' }}>AI screening (not a diagnosis)</p>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '8px' }}>
              <div style={{ background: riskBg[photo.risk_level], borderRadius: '12px', padding: '10px', textAlign: 'center' }}>
                <p style={{ fontSize: '18px', fontWeight: 900, color: riskColor[photo.risk_level] }}>{(photo.risk_score * 100).toFixed(0)}%</p>
                <p style={{ fontSize: '10px', fontWeight: 700, color: riskColor[photo.risk_level] }}>{aiLabel[photo.risk_level]}</p>
              </div>
              {[
                { l: 'Redness', v: photo.redness_index },
                { l: 'Swelling', v: photo.swelling_score },
                { l: 'Colour drift', v: photo.color_deviation },
              ].map(m => (
                <div key={m.l} style={{ background: '#fff', border: '1px solid #E8E7F0', borderRadius: '12px', padding: '10px', textAlign: 'center' }}>
                  <p style={{ fontSize: '18px', fontWeight: 800, color: '#2F2B6E' }}>{m.v != null ? Number(m.v).toFixed(0) : '-'}</p>
                  <p style={{ fontSize: '10px', color: '#8C8AAE', fontWeight: 600 }}>{m.l}</p>
                </div>
              ))}
            </div>
            {photo.recommendation && (
              <p style={{ fontSize: '12px', color: '#6B6990', marginTop: '10px', lineHeight: 1.5 }}>
                <b>AI note:</b> {photo.recommendation}
              </p>
            )}
          </div>

          {/* RIGHT: review form */}
          <div style={{ padding: '20px 24px', display: 'flex', flexDirection: 'column', gap: '14px' }}>
            <div>
              <span style={label}>Your assessment *</span>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '8px' }}>
                {ASSESSMENTS.map(a => {
                  const on = form.assessment === a.key;
                  return (
                    <button key={a.key} onClick={() => pickAssessment(a.key)} style={{
                      padding: '10px 8px', textAlign: 'left', borderRadius: '12px',
                      background: on ? riskBg[a.key] : '#fff',
                      border: `2px solid ${on ? riskColor[a.key] : '#E8E7F0'}`,
                      color: on ? riskColor[a.key] : '#2F2B6E'
                    }}>
                      <div style={{ fontSize: '13px', fontWeight: 800 }}>{a.icon} {a.title}</div>
                      <div style={{ fontSize: '10px', fontWeight: 500, color: '#8C8AAE', marginTop: '2px' }}>{a.sub}</div>
                    </button>
                  );
                })}
              </div>
            </div>

            <div>
              <span style={label}>Findings *</span>
              <textarea rows={3} value={form.findings} onChange={e => set('findings', e.target.value)}
                placeholder="What do you see in this photo?" style={{ resize: 'vertical', fontSize: '13px', padding: '10px 12px' }} />
              {form.assessment && (
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px', marginTop: '6px' }}>
                  {QUICK_FINDINGS[form.assessment].map(q => (
                    <button key={q} onClick={() => addFinding(q)} style={chip}>+ {q}</button>
                  ))}
                </div>
              )}
            </div>

            <div>
              <span style={label}>Advice for patient</span>
              <textarea rows={2} value={form.advice} onChange={e => set('advice', e.target.value)}
                placeholder="Care instructions the patient will read in the report" style={{ resize: 'vertical', fontSize: '13px', padding: '10px 12px' }} />
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: '1.6fr 1fr', gap: '10px' }}>
              <div>
                <span style={label}>Medications</span>
                <textarea rows={2} value={form.medications} onChange={e => set('medications', e.target.value)}
                  placeholder="e.g. Amoxicillin 500 mg, 1 tab 3x/day, 5 days" style={{ resize: 'vertical', fontSize: '13px', padding: '10px 12px' }} />
              </div>
              <div>
                <span style={label}>Next follow-up</span>
                <input type="date" value={form.followup_date} onChange={e => set('followup_date', e.target.value)}
                  style={{ fontSize: '13px', padding: '10px 12px' }} />
              </div>
            </div>

            {error && (
              <p style={{ fontSize: '12px', color: '#D64545', fontWeight: 600, background: '#FDEAEA', padding: '8px 12px', borderRadius: '10px' }}>{error}</p>
            )}

            <div style={{ display: 'flex', gap: '10px', marginTop: 'auto', paddingTop: '6px' }}>
              <button onClick={save} disabled={saving} style={{
                flex: 1, background: 'linear-gradient(135deg, #2F2B6E, #7F79B6)', padding: '13px'
              }}>
                {saving ? 'Saving…' : savedNow ? '✓ Saved — patient notified' : reviewed ? 'Update review' : 'Save review & send report'}
              </button>
              {reviewed && (
                <button onClick={() => window.open(reviewReportUrl(photo.id, true), '_blank')} style={{
                  background: '#fff', color: '#2F2B6E', border: '2px solid #E8E7F0', padding: '13px 16px'
                }}>📄 Preview PDF</button>
              )}
            </div>
            <p style={{ fontSize: '11px', color: '#8C8AAE' }}>
              Saving makes a PDF report available for the patient to download from their History page.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}

export default ReviewModal;
