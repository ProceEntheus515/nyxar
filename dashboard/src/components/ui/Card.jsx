import React from 'react';

export default function Card({ children, className = '', glow = false, glowColor = 'var(--color-primary)' }) {
  const glowStyle = glow
    ? { boxShadow: `0 0 15px -5px ${glowColor}` }
    : {};

  return (
    <div
      className={`bg-[var(--base-surface)] border border-[var(--base-border)] rounded-[var(--radius-md)] hover:bg-[var(--base-raised)] transition-colors duration-200 overflow-hidden ${className}`}
      style={glowStyle}
    >
      {children}
    </div>
  );
}
