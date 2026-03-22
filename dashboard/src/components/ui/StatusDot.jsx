import React from 'react';

export default function StatusDot({ status = 'online' }) {
  let bg = 'bg-[#8B949E]'; // default / offline
  let animate = '';

  if (status === 'online') {
    bg = 'bg-[var(--color-success)]';
  } else if (status === 'warning') {
    bg = 'bg-[var(--color-warning)]';
    animate = 'animate-pulse-warning';
  } else if (status === 'critical') {
    bg = 'bg-[var(--color-critical)]';
    animate = 'animate-pulse-critical';
  }

  return (
    <div
      aria-label={`Estado actual: ${status}`}
      className={`w-2.5 h-2.5 rounded-full inline-block ${bg} ${animate}`}
    />
  );
}
