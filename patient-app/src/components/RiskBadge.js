import React from 'react';

const config = {
  GREEN: { label: 'Healing Well', icon: '✅', color: '#2BA84A', bg: '#E8F8EC', border: '#B8E8C4', glow: 'rgba(43,168,74,0.3)' },
  YELLOW: { label: 'Monitor Closely', icon: '⚠️', color: '#E89B2C', bg: '#FFF5E5', border: '#F5D79E', glow: 'rgba(232,155,44,0.3)' },
  RED: { label: 'Needs Attention', icon: '🔴', color: '#D64545', bg: '#FDEAEA', border: '#F5BBBB', glow: 'rgba(214,69,69,0.4)' },
};

const sizes = {
  sm: { padding: '3px 10px', fontSize: '11px', iconSize: '12px', gap: '4px' },
  md: { padding: '5px 14px', fontSize: '13px', iconSize: '14px', gap: '6px' },
  lg: { padding: '8px 18px', fontSize: '15px', iconSize: '16px', gap: '8px' },
};

function RiskBadge({ level, size = 'sm' }) {
  const c = config[level] || config.GREEN;
  const s = sizes[size] || sizes.sm;

  return (
    <span style={{
      display: 'inline-flex', alignItems: 'center', gap: s.gap,
      padding: s.padding, borderRadius: '10px',
      background: c.bg, border: `1.5px solid ${c.border}`,
      fontSize: s.fontSize, fontWeight: 700, color: c.color,
      animation: level === 'RED' ? 'sosPulse 2s infinite' : 'none',
      boxShadow: level === 'RED' ? `0 0 15px ${c.glow}` : `0 2px 8px ${c.glow}`,
      transition: 'all 0.3s ease',
    }}>
      <span style={{ fontSize: s.iconSize }}>{c.icon}</span>
      {c.label}
    </span>
  );
}

export default RiskBadge;
