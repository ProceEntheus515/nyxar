import React from 'react';

export default function MonoText({ children, color, className = '' }) {
  return (
    <span
      className={`font-mono text-[13px] tracking-tight ${className}`}
      style={{ color: color || 'var(--text-sec)', fontFamily: 'var(--font-data)' }}
    >
      {children}
    </span>
  );
}
