import React from 'react';

const SIZE_MAP = {
  sm: 'w-2.5 h-2.5',
  lg: 'w-4 h-4 min-w-[1rem] min-h-[1rem]',
};

export default function StatusDot({ status = 'online', size = 'sm' }) {
  let bg = 'bg-[var(--base-subtle)]';
  let animate = '';

  if (status === 'online') {
    bg = 'bg-[var(--color-success)]';
  } else if (status === 'warning') {
    bg = 'bg-[var(--color-warning)]';
    animate = 'animate-pulse-warning';
  } else if (status === 'critical') {
    bg = 'bg-[var(--color-critical)]';
    animate = 'animate-pulse-critical';
  } else if (status === 'offline' || status === 'unknown') {
    bg = 'bg-[var(--base-subtle)]';
  }

  const dim = SIZE_MAP[size] || SIZE_MAP.sm;

  return (
    <div
      aria-label={`Estado actual: ${status}`}
      className={`${dim} rounded-full inline-block ${bg} ${animate}`}
    />
  );
}
