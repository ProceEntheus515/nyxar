import React, { useMemo } from 'react';

function getStringColor(str) {
  // Simple String Hashing para HSL Colors (Brillantes y Oscuros/Vivos)
  let hash = 0;
  for (let i = 0; i < str.length; i++) {
    hash = str.charCodeAt(i) + ((hash << 5) - hash);
  }
  // Hue 0-360, Saturation 65%, Lightness 45% (perfecto para dark theme readability)
  return `hsl(${Math.abs(hash) % 360}, 65%, 45%)`;
}

export default function AreaBadge({ area, className = '' }) {
  const safeArea = area || 'Unknown';
  
  const bgColor = useMemo(() => getStringColor(safeArea), [safeArea]);

  return (
    <span
      className={`px-2 py-0.5 text-[11px] font-bold uppercase rounded text-white tracking-widest inline-flex items-center justify-center ${className}`}
      style={{ backgroundColor: bgColor }}
    >
      {safeArea}
    </span>
  );
}
