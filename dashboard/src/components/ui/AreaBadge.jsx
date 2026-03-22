import React, { useMemo } from 'react';
import { areaToColor } from '../../lib/colors';
import styles from './AreaBadge.module.css';

export default function AreaBadge({ area, className = '' }) {
  const safeArea = area || 'Unknown';

  const backgroundColor = useMemo(() => areaToColor(safeArea), [safeArea]);

  return (
    <span
      className={`${styles.badge} ${className}`.trim()}
      style={{ backgroundColor }}
    >
      {safeArea}
    </span>
  );
}
