import React, { useState, useEffect } from 'react';

function getRelativeTime(dateString) {
  const date = new Date(dateString);
  const now = new Date();
  
  if (isNaN(date)) return 'fecha inválida';
  
  const diffInSeconds = Math.floor((now - date) / 1000);
  
  if (diffInSeconds < 30) return 'hace un momento';
  if (diffInSeconds < 60) return `hace ${diffInSeconds} segundos`;

  const diffInMinutes = Math.floor(diffInSeconds / 60);
  if (diffInMinutes === 1) return 'hace 1 minuto';
  if (diffInMinutes < 60) return `hace ${diffInMinutes} minutos`;

  const diffInHours = Math.floor(diffInMinutes / 60);
  if (diffInHours === 1) return 'hace 1 hora';
  if (diffInHours < 24) return `hace ${diffInHours} horas`;

  const diffInDays = Math.floor(diffInHours / 24);
  if (diffInDays === 1) return 'hace 1 día';
  return `hace ${diffInDays} días`;
}

export default function TimeAgo({ timestamp, className = '' }) {
  const [relativeTime, setRelativeTime] = useState(() => getRelativeTime(timestamp));

  useEffect(() => {
    setRelativeTime(getRelativeTime(timestamp)); // Actualiza al montar por si el prop cambio

    const interval = setInterval(() => {
      setRelativeTime(getRelativeTime(timestamp));
    }, 30000); // Se actualiza 30s

    return () => clearInterval(interval);
  }, [timestamp]);

  return (
    <span
      className={`text-[11px] text-[var(--text-sec)] font-medium ${className}`}
      title={new Date(timestamp).toLocaleString()}
    >
      {relativeTime}
    </span>
  );
}
