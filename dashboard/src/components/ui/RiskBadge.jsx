import React from 'react';
import { RISK_COLORS } from '../../lib/utils';

export default function RiskBadge({ score, severidad }) {
  const defaultSev = 'info';
  const config = RISK_COLORS[severidad?.toLowerCase()] || RISK_COLORS[defaultSev];
  
  const isCritical = severidad?.toLowerCase() === 'critica' || severidad?.toLowerCase() === 'crítica';
  const isAlta = severidad?.toLowerCase() === 'alta';
  
  let animationClass = '';
  if (isCritical) {
    animationClass = 'animate-pulse-critical';
  } else if (isAlta) {
    animationClass = 'animate-pulse-warning';
  }

  return (
    <div
      aria-label={`Riesgo Nivel ${config.label} Score ${score}`}
      className={`inline-flex items-center gap-2 px-2.5 py-1 rounded-full font-bold text-[11px] uppercase tracking-wider ${animationClass}`}
      style={{
        backgroundColor: config.bg,
        color: config.text,
      }}
    >
      <span>{config.label}</span>
      {score !== undefined && (
        <span className="bg-black/20 px-1.5 py-0.5 rounded">
          {score}
        </span>
      )}
    </div>
  );
}
