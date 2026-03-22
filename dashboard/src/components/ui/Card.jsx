import React from 'react';

export default function Card({ children, className = '', glow = false, glowColor = 'var(--color-primary)' }) {
  const glowStyle = glow
    ? { boxShadow: `0 0 15px -5px ${glowColor}` }
    : {};

  return (
    <div
      className={`bg-[#161B22] border border-[#21262D] rounded-[8px] hover:bg-[#1A2030] transition-colors duration-200 overflow-hidden ${className}`}
      style={glowStyle}
    >
      {children}
    </div>
  );
}
