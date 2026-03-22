import React from 'react';

export default function Skeleton({ width = '100%', height = '20px', className = '', circle = false }) {
  const borderRadius = circle ? '50%' : '4px';
  
  return (
    <div
      className={`shimmer-effect bg-[#21262D] ${className}`}
      style={{
        width,
        height,
        borderRadius
      }}
      role="status"
      aria-label="Cargando componente de interfaz"
      aria-busy="true"
    />
  );
}
