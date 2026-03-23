import { useState, useCallback } from 'react'
import { normalizeSourceKey } from '../../lib/colors'
import styles from './TargetList.module.css'

/**
 * TargetList — lista densa estilo operacional (F08).
 * TargetListRow se usa también en Timeline virtualizado (sin hijos expandibles).
 */

export const TIMELINE_TARGET_COLUMNS = {
  main: { label: 'EVENTO' },
  right: [
    { key: 'source_code', label: 'SRC', semantic: null },
    { key: 'area_code', label: 'AREA', semantic: null },
    { key: 'score_display', label: 'RISK', semantic: 'auto' },
  ],
}

export function getAlertLevel(item) {
  const score = Number(item?.risk_score ?? item?.riskScore ?? 0)
  if (!Number.isFinite(score)) return 'nominal'
  if (score >= 80) return 'critical'
  if (score >= 60) return 'high'
  if (score >= 40) return 'medium'
  if (score >= 20) return 'low'
  return 'nominal'
}

function semanticForScore(score) {
  const n = Number(score)
  if (!Number.isFinite(n)) return null
  if (n >= 80) return 'critical'
  if (n >= 60) return 'high'
  if (n >= 40) return 'medium'
  return null
}

function resolveSemantic(col, item) {
  if (col.semantic === 'auto') return semanticForScore(item.risk_score ?? item.riskScore)
  return col.semantic || null
}

/**
 * Convierte un evento del store a ítem de fila TargetList (Timeline).
 */
export function eventToTimelineTargetItem(ev) {
  if (!ev) return null
  const risk = Number(ev.enrichment?.risk_score)
  const srcKey = normalizeSourceKey(ev.source || '')
  const areaRaw = String(ev.interno?.area || '').trim()
  const areaCode = areaRaw ? areaRaw.slice(0, 4).toUpperCase() : '—'
  const ts = ev.timestamp
    ? new Date(ev.timestamp).toLocaleString('es', {
        day: '2-digit',
        month: 'short',
        hour: '2-digit',
        minute: '2-digit',
      })
    : '—'
  const user = ev.interno?.id_usuario || ev.interno?.ip || '—'
  const srcCode = srcKey ? String(srcKey).slice(0, 3).toUpperCase() : '—'
  return {
    id: ev.id,
    label: String(ev.externo?.valor || ev.source || 'Evento'),
    subtitle: `${user} · ${ts}`,
    source_code: srcCode,
    area_code: areaCode,
    score_display: Number.isFinite(risk) ? String(Math.round(risk)) : '—',
    risk_score: Number.isFinite(risk) ? risk : undefined,
    children: Array.isArray(ev.children) ? ev.children : [],
  }
}

function StatusDot({ level }) {
  return (
    <div
      className={styles.statusDot}
      data-level={level}
      aria-label={`Estado: ${level}`}
    />
  )
}

export function TargetListHeader({ columns = TIMELINE_TARGET_COLUMNS, className = '' }) {
  const right = columns.right || []
  return (
    <div className={`${styles.header} ${className}`.trim()} role="row">
      <div className={styles.headerLeading} aria-hidden />
      <div className={styles.headerMain}>{columns.main?.label || 'TARGET'}</div>
      {right.map((col, i) => (
        <div key={col.key} className={styles.headerColWithDivider}>
          {i > 0 ? <div className={styles.colDivider} aria-hidden /> : null}
          <div className={styles.headerCol}>{col.label}</div>
        </div>
      ))}
      <div className={styles.headerExpandSpacer} aria-hidden />
    </div>
  )
}

export function TargetListRow({
  item,
  columns = TIMELINE_TARGET_COLUMNS,
  isSelected = false,
  onSelect,
  enableChildren = true,
  showSubtitle = true,
}) {
  const [expanded, setExpanded] = useState(false)
  const alertLevel = getAlertLevel(item)
  const hasChildren = enableChildren && Array.isArray(item.children) && item.children.length > 0

  const handleClick = useCallback(() => {
    onSelect?.(item)
    if (hasChildren) setExpanded((e) => !e)
  }, [item, onSelect, hasChildren])

  const handleKeyDown = useCallback(
    (ev) => {
      if (ev.key === 'Enter' || ev.key === ' ') {
        ev.preventDefault()
        handleClick()
      }
    },
    [handleClick],
  )

  const right = columns.right || []

  return (
    <>
      <div
        className={[
          styles.row,
          isSelected ? styles.selected : '',
          alertLevel === 'critical' ? styles.alertRow : '',
          expanded && hasChildren ? styles.rowExpanded : '',
        ]
          .filter(Boolean)
          .join(' ')}
        onClick={handleClick}
        onKeyDown={onSelect ? handleKeyDown : undefined}
        role="listitem"
        tabIndex={onSelect ? 0 : undefined}
        aria-selected={isSelected}
      >
        <StatusDot level={alertLevel} />
        <div className={styles.main}>
          <span className={styles.mainText}>{item.label ?? '—'}</span>
          {showSubtitle && item.subtitle ? (
            <span className={styles.subtitle}>{item.subtitle}</span>
          ) : null}
        </div>
        {right.map((col, i) => {
          const semantic = resolveSemantic(col, item)
          const raw = item[col.key]
          const display =
            raw == null || raw === ''
              ? '—'
              : col.key === 'score_display'
                ? String(raw).toUpperCase()
                : String(raw)
          return (
            <div key={col.key} className={styles.colRight}>
              {i > 0 ? <div className={styles.colDivider} aria-hidden /> : null}
              <span
                className={styles.colValue}
                data-semantic={semantic || undefined}
              >
                {display}
              </span>
            </div>
          )
        })}
        {hasChildren ? (
          <div className={styles.expandIndicator} aria-hidden>
            {expanded ? '▾' : '▸'}
          </div>
        ) : (
          <div className={styles.headerExpandSpacer} aria-hidden />
        )}
      </div>
      {expanded && hasChildren
        ? item.children.map((child) => (
            <div key={child.id ?? child.label} className={styles.childRow} role="listitem">
              <div className={styles.childIndent} aria-hidden />
              <div className={styles.main}>
                <span className={`${styles.mainText} ${styles.childText}`.trim()}>
                  {child.label ?? '—'}
                </span>
              </div>
              {right.map((col, i) => (
                <div key={col.key} className={styles.colRight}>
                  {i > 0 ? <div className={styles.colDivider} aria-hidden /> : null}
                  <span className={styles.colValue}>
                    {child[col.key] == null || child[col.key] === ''
                      ? '—'
                      : String(child[col.key])}
                  </span>
                </div>
              ))}
              <div className={styles.headerExpandSpacer} aria-hidden />
            </div>
          ))
        : null}
    </>
  )
}

export default function TargetList({ items = [], columns = TIMELINE_TARGET_COLUMNS, onSelect, selectedId }) {
  return (
    <div className={styles.list} role="list">
      <TargetListHeader columns={columns} />
      {items.map((item) => (
        <TargetListRow
          key={item.id}
          item={item}
          columns={columns}
          isSelected={selectedId != null && String(selectedId) === String(item.id)}
          onSelect={onSelect}
          enableChildren
        />
      ))}
    </div>
  )
}
