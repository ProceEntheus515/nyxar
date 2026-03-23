import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import * as d3 from 'd3'
import { useStore } from '../store'
import { scoreToColor } from '../lib/colors'
import { readCssVar } from '../styles/cssVar'
import MetricCard from '../components/data/MetricCard'
import NetworkMapToolbar from '../components/network-map/NetworkMapToolbar'
import {
  clusterPixelCenter,
  clusterLabel,
  allClusterKeys,
} from '../lib/networkMap/clusterAnchors'
import {
  buildIdentityNodes,
  buildInternalLinksFromEvents,
  activeNodeIdsInWindow,
  internoNodeId,
  resolveAlertNodeId,
} from '../lib/networkMap/internalGraph'
import { NetworkMapLensRenderer } from '../lib/networkMap/networkMapLensRenderer'

const PARTICLE_MS = 600
const PICK_RADIUS_WORLD = 18

/** Borde claro fijo para leer el marcador sobre --bg-* y dentro del hueco de la lente. */
const NODE_RIM = 'rgba(237, 243, 250, 0.5)'
const INTERNAL_NODE_PX = 8
const EXTERNAL_NODE_PX = 10

function drawInternalNodeMarker(ctx, x, y, fill, lineWidth) {
  const s = INTERNAL_NODE_PX
  ctx.fillStyle = fill
  ctx.globalAlpha = 1
  ctx.fillRect(x - s / 2, y - s / 2, s, s)
  ctx.strokeStyle = NODE_RIM
  ctx.lineWidth = lineWidth
  ctx.strokeRect(x - s / 2, y - s / 2, s, s)
}

function drawExternalNodeMarker(ctx, x, y, fill, lineWidth) {
  const s = EXTERNAL_NODE_PX
  ctx.save()
  ctx.translate(x, y)
  ctx.rotate(Math.PI / 4)
  ctx.fillStyle = fill
  ctx.globalAlpha = 1
  ctx.fillRect(-s / 2, -s / 2, s, s)
  ctx.strokeStyle = NODE_RIM
  ctx.lineWidth = lineWidth
  ctx.strokeRect(-s / 2, -s / 2, s, s)
  ctx.restore()
}

function isCriticalSeverity(sev) {
  const s = String(sev || '').toLowerCase()
  return s === 'critica' || s === 'crítica'
}

function resolveLensContext(selectedId, alerts, baseNodes, visibleNodeIds, pos) {
  if (selectedId) {
    for (const id of visibleNodeIds) {
      const meta = baseNodes.get(id)
      if (!meta) continue
      if (
        selectedId === id ||
        selectedId === String(meta.identity?.ip_asociada || '')
      ) {
        const p = pos.get(id)
        if (p) return { nid: id, meta, p, source: 'selection' }
      }
    }
  }
  const criticalInFeed = (alerts || []).find((a) => isCriticalSeverity(a.severidad))
  if (criticalInFeed) {
    const nid = resolveAlertNodeId(criticalInFeed, baseNodes)
    if (nid && visibleNodeIds.has(nid)) {
      const p = pos.get(nid)
      const meta = baseNodes.get(nid)
      if (p && meta) return { nid, meta, p, source: 'alert' }
    }
  }
  return null
}

function canvasColorFromToken(token) {
  const t = String(token || '').trim()
  const m = /^var\(\s*(--[^)]+)\s*\)/.exec(t)
  if (m) {
    const v = readCssVar(m[1])
    return v || '#6b7fa0'
  }
  if (t.startsWith('#')) return t
  const v = readCssVar(t)
  return v || '#6b7fa0'
}

function quadControl(x1, y1, x2, y2, sign) {
  const mx = (x1 + x2) / 2
  const my = (y1 + y2) / 2
  const dx = x2 - x1
  const dy = y2 - y1
  const len = Math.hypot(dx, dy) || 1
  const k = sign * 36
  return { cx: mx + (-dy / len) * k, cy: my + (dx / len) * k }
}

function quadPoint(x0, y0, cx, cy, x1, y1, t) {
  const u = 1 - t
  return {
    x: u * u * x0 + 2 * u * t * cx + t * t * x1,
    y: u * u * y0 + 2 * u * t * cy + t * t * y1,
  }
}

/** Distancia mínima punto–segmento cuadrático (muestreo). */
function distToQuad(px, py, x0, y0, cx, cy, x1, y1, steps = 24) {
  let min = Infinity
  for (let i = 0; i <= steps; i += 1) {
    const t = i / steps
    const p = quadPoint(x0, y0, cx, cy, x1, y1, t)
    const d = Math.hypot(px - p.x, py - p.y)
    if (d < min) min = d
  }
  return min
}

function linkStrokeColors() {
  const border = canvasColorFromToken('var(--base-border)')
  const medium = canvasColorFromToken('var(--medium-muted)')
  const critical = canvasColorFromToken('var(--critical-muted)')
  return { border, medium, critical }
}

export default function NetworkMap() {
  const containerRef = useRef(null)
  const canvasRef = useRef(null)
  const svgLabelsRef = useRef(null)
  const svgLabelsGRef = useRef(null)
  const zoomBehaviorRef = useRef(null)
  const transformRef = useRef(d3.zoomIdentity)
  const positionsRef = useRef(new Map())
  const layoutSizeRef = useRef({ w: 0, h: 0 })
  const identityLayoutKeyRef = useRef('')
  const particlesRef = useRef([])
  const lastHeadEventIdRef = useRef(null)
  const rafRef = useRef(0)
  const drawFrameRef = useRef(() => {})
  const hoverRef = useRef({ nodeId: null, linkKey: null })
  const lensRef = useRef(null)
  const prevResolvedLensIdRef = useRef(null)
  const lastCriticalPulseAlertIdRef = useRef(null)

  const {
    identities,
    events,
    alerts,
    openDetailPanel,
    detailPanel,
    mapFocusNodeId,
    clearMapFocusRequest,
  } = useStore()

  const [chartSize, setChartSize] = useState({ width: 0, height: 0 })
  const [hoverTip, setHoverTip] = useState(null)
  const [showConnections, setShowConnections] = useState(true)
  const [minSeverityRaw, setMinSeverityRaw] = useState(0)
  const [activeOnly, setActiveOnly] = useState(false)

  const setMinSeverity = useCallback((n) => {
    const v = Math.max(0, Math.min(99, Number(n) || 0))
    setMinSeverityRaw(v)
  }, [])

  const minSeverityClamped = Math.min(99, minSeverityRaw)

  const identityKey = useMemo(
    () =>
      Object.keys(identities || {})
        .sort()
        .join('\u0001'),
    [identities],
  )

  const baseNodes = useMemo(() => buildIdentityNodes(identities || {}), [identities])

  const validIds = useMemo(() => new Set(baseNodes.keys()), [baseNodes])

  const activeIds = useMemo(
    () => activeNodeIdsInWindow(events || [], validIds),
    [events, validIds],
  )

  const internalLinks = useMemo(
    () => buildInternalLinksFromEvents(events || [], validIds),
    [events, validIds],
  )

  const visibleNodeIds = useMemo(() => {
    const out = new Set()
    for (const [id, meta] of baseNodes) {
      if ((meta.score || 0) < minSeverityClamped) continue
      if (activeOnly && !activeIds.has(id)) continue
      out.add(id)
    }
    return out
  }, [baseNodes, minSeverityClamped, activeOnly, activeIds])

  const visibleLinks = useMemo(
    () =>
      internalLinks.filter(
        (l) => visibleNodeIds.has(l.source) && visibleNodeIds.has(l.target),
      ),
    [internalLinks, visibleNodeIds],
  )

  const degreeById = useMemo(() => {
    const m = new Map()
    for (const l of visibleLinks) {
      m.set(l.source, (m.get(l.source) || 0) + 1)
      m.set(l.target, (m.get(l.target) || 0) + 1)
    }
    return m
  }, [visibleLinks])

  const recentEvents5m = useMemo(() => {
    const now = Date.now()
    return (events || []).filter((ev) => {
      try {
        return now - new Date(ev.timestamp).getTime() <= 5 * 60 * 1000
      } catch {
        return false
      }
    }).length
  }, [events])

  const selectedId =
    detailPanel?.isOpen && detailPanel?.type === 'identity' && detailPanel?.id != null
      ? String(detailPanel.id)
      : null

  useEffect(() => {
    const el = containerRef.current
    if (!el) return undefined
    const measure = () => {
      const w = el.clientWidth
      const h = el.clientHeight
      setChartSize((prev) =>
        prev.width === w && prev.height === h ? prev : { width: w, height: h },
      )
    }
    measure()
    const ro = new ResizeObserver(measure)
    ro.observe(el)
    return () => ro.disconnect()
  }, [])

  /** Layout por cluster: simulación local, posiciones fijas después. */
  useEffect(() => {
    const w = chartSize.width
    const h = chartSize.height
    if (w < 48 || h < 48 || baseNodes.size === 0) return

    const prevW = layoutSizeRef.current.w
    const prevH = layoutSizeRef.current.h
    const sameIds = identityLayoutKeyRef.current === identityKey

    if (sameIds && prevW > 0 && prevH > 0 && (prevW !== w || prevH !== h)) {
      const map = positionsRef.current
      const sx = w / prevW
      const sy = h / prevH
      for (const p of map.values()) {
        p.x *= sx
        p.y *= sy
      }
      layoutSizeRef.current = { w, h }
      return
    }

    identityLayoutKeyRef.current = identityKey
    layoutSizeRef.current = { w, h }

    const centers = {}
    for (const key of allClusterKeys()) {
      centers[key] = clusterPixelCenter(key, w, h)
    }

    const simNodes = []
    for (const meta of baseNodes.values()) {
      const c = centers[meta.clusterKey] || centers.OTROS
      const jitter = 48
      simNodes.push({
        id: meta.id,
        clusterKey: meta.clusterKey,
        radius: meta.radius,
        x: c.cx + (Math.random() - 0.5) * jitter,
        y: c.cy + (Math.random() - 0.5) * jitter,
      })
    }

    const simulation = d3
      .forceSimulation(simNodes)
      .force(
        'fx',
        d3
          .forceX((d) => centers[d.clusterKey]?.cx ?? w * 0.5)
          .strength(0.18),
      )
      .force(
        'fy',
        d3
          .forceY((d) => centers[d.clusterKey]?.cy ?? h * 0.5)
          .strength(0.18),
      )
      .force(
        'collide',
        d3.forceCollide((d) => d.radius + 6).strength(0.95),
      )
      .alphaDecay(0.22)
      .stop()

    for (let i = 0; i < 400; i += 1) simulation.tick()

    const pad = 24
    const map = new Map()
    for (const d of simNodes) {
      const r = (baseNodes.get(d.id)?.radius || 12) + pad
      map.set(d.id, {
        x: Math.max(r, Math.min(w - r, d.x)),
        y: Math.max(r, Math.min(h - r, d.y)),
      })
    }
    positionsRef.current = map
  }, [identityKey, chartSize.width, chartSize.height, baseNodes])

  /** Partícula al llegar evento nuevo por WebSocket (cadena interna). */
  useEffect(() => {
    const list = events || []
    if (list.length < 2) return
    const head = list[0]
    const prev = list[1]
    if (!head?.id || head.id === lastHeadEventIdRef.current) return
    lastHeadEventIdRef.current = head.id

    const a = internoNodeId(prev)
    const b = internoNodeId(head)
    if (!a || !b || a === b) return
    const pos = positionsRef.current
    if (!pos.has(a) || !pos.has(b)) return

    try {
      if (Date.now() - new Date(head.timestamp).getTime() > 5 * 60 * 1000) return
    } catch {
      return
    }

    const pa = pos.get(a)
    const pb = pos.get(b)
    const sign = (a.charCodeAt(0) + b.charCodeAt(0)) % 2 === 0 ? 1 : -1
    const { cx, cy } = quadControl(pa.x, pa.y, pb.x, pb.y, sign)
    const enr = head.enrichment || {}
    const level =
      Number(enr.risk_score) >= 85 || enr.malicioso
        ? 'malicious'
        : enr.sospechoso
          ? 'suspicious'
          : 'normal'
    const { border, medium, critical } = linkStrokeColors()
    const color =
      level === 'malicious' ? critical : level === 'suspicious' ? medium : border

    particlesRef.current.push({
      x0: pa.x,
      y0: pa.y,
      cx,
      cy,
      x1: pb.x,
      y1: pb.y,
      t0: Date.now(),
      color,
    })
  }, [events])

  const requestRedraw = useCallback(() => {
    if (rafRef.current) return
    rafRef.current = requestAnimationFrame(() => {
      rafRef.current = 0
      drawFrameRef.current()
    })
  }, [])

  useEffect(() => {
    if (selectedId) return
    if (!lensRef.current) lensRef.current = new NetworkMapLensRenderer()
    const criticalAlert = (alerts || []).find((a) => isCriticalSeverity(a.severidad))
    if (!criticalAlert) return
    const aid = criticalAlert.id
    if (!aid || aid === lastCriticalPulseAlertIdRef.current) return
    const nid = resolveAlertNodeId(criticalAlert, baseNodes)
    if (!nid) return
    const p = positionsRef.current.get(nid)
    const meta = baseNodes.get(nid)
    if (!p || !meta) return
    lastCriticalPulseAlertIdRef.current = aid
    const lens = lensRef.current
    lens.setTargetMeta({
      id: meta.id,
      label: meta.nombre,
      risk_score: meta.score,
      graphKind: meta.graphKind,
    })
    lens.setWorldPos(p.x, p.y)
    lens.pulseAlert()
    requestRedraw()
  }, [selectedId, alerts, baseNodes, identityKey, requestRedraw])

  const drawFrame = useCallback(() => {
    const canvas = canvasRef.current
    const container = containerRef.current
    if (!canvas || !container) return

    const w = chartSize.width
    const h = chartSize.height
    if (w < 48 || h < 48) return

    const dpr = typeof window !== 'undefined' ? window.devicePixelRatio || 1 : 1
    canvas.width = Math.floor(w * dpr)
    canvas.height = Math.floor(h * dpr)
    canvas.style.width = `${w}px`
    canvas.style.height = `${h}px`

    const ctx = canvas.getContext('2d')
    if (!ctx) return

    if (!lensRef.current || !(lensRef.current instanceof NetworkMapLensRenderer)) {
      lensRef.current = new NetworkMapLensRenderer()
    }

    const t = transformRef.current
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0)
    ctx.clearRect(0, 0, w, h)

    ctx.save()
    ctx.translate(t.x, t.y)
    ctx.scale(t.k, t.k)

    const pos = positionsRef.current
    const palette = linkStrokeColors()
    const now = performance.now()
    const pulseT = now * 0.002

    const linkGeoms = []

    if (showConnections) {
      visibleLinks.forEach((link, i) => {
        const p0 = pos.get(link.source)
        const p1 = pos.get(link.target)
        if (!p0 || !p1) return
        const sign = i % 2 === 0 ? 1 : -1
        const { cx, cy } = quadControl(p0.x, p0.y, p1.x, p1.y, sign)
        linkGeoms.push({ link, p0, p1, cx, cy })

        let stroke = palette.border
        let opacity = 0.4
        if (link.level === 'suspicious') {
          stroke = palette.medium
          opacity = 0.65
        }
        if (link.level === 'malicious') {
          stroke = palette.critical
          opacity = 0.4 + Math.sin(pulseT) * 0.2 + 0.2
        }

        ctx.beginPath()
        ctx.moveTo(p0.x, p0.y)
        ctx.quadraticCurveTo(cx, cy, p1.x, p1.y)
        ctx.strokeStyle = stroke
        ctx.globalAlpha = opacity
        ctx.lineWidth = 1 + Math.min(2, link.volume * 0.15)
        ctx.stroke()
        ctx.globalAlpha = 1
      })
    }

    ;(hoverRef.current._linkGeoms = linkGeoms)

    const particles = particlesRef.current
    const kept = []
    const wallNow = Date.now()
    for (const p of particles) {
      const wall = wallNow - p.t0
      const u = Math.min(1, wall / PARTICLE_MS)
      if (u >= 1) continue
      const pt = quadPoint(p.x0, p.y0, p.cx, p.cy, p.x1, p.y1, u)
      ctx.beginPath()
      ctx.fillStyle = p.color
      ctx.globalAlpha = 0.95
      const pr = 2 / (t.k || 1)
      ctx.arc(pt.x, pt.y, pr, 0, Math.PI * 2)
      ctx.fill()
      ctx.globalAlpha = 1
      kept.push(p)
    }
    particlesRef.current = kept

    const sortedIds = [...visibleNodeIds].sort(
      (a, b) => (baseNodes.get(b)?.score || 0) - (baseNodes.get(a)?.score || 0),
    )

    for (const id of sortedIds) {
      const meta = baseNodes.get(id)
      const p = pos.get(id)
      if (!meta || !p) continue

      const bucket = scoreToColor(meta.score)
      const fill = canvasColorFromToken(bucket.color)
      const lineW = 1.25
      const isExternal = meta.graphKind === 'external'
      const outerGlow = isExternal ? EXTERNAL_NODE_PX + 4 : INTERNAL_NODE_PX + 4

      if (meta.score > 80) {
        const pulse = 0.65 + Math.sin(pulseT * 1.4) * 0.28
        ctx.strokeStyle = canvasColorFromToken('var(--critical-muted)')
        ctx.globalAlpha = Math.min(1, pulse * 0.95)
        ctx.lineWidth = 2
        if (isExternal) {
          ctx.save()
          ctx.translate(p.x, p.y)
          ctx.rotate(Math.PI / 4)
          ctx.strokeRect(-outerGlow / 2, -outerGlow / 2, outerGlow, outerGlow)
          ctx.restore()
        } else {
          ctx.strokeRect(
            p.x - outerGlow / 2,
            p.y - outerGlow / 2,
            outerGlow,
            outerGlow,
          )
        }
        ctx.globalAlpha = 1
      }

      if (isExternal) {
        drawExternalNodeMarker(ctx, p.x, p.y, fill, lineW)
      } else {
        drawInternalNodeMarker(ctx, p.x, p.y, fill, lineW)
      }
    }

    ctx.restore()

    const lens = lensRef.current
    const lensCtx = resolveLensContext(
      selectedId,
      alerts,
      baseNodes,
      visibleNodeIds,
      pos,
    )
    const prevLensId = prevResolvedLensIdRef.current
    if (lensCtx) {
      lens.setTargetMeta({
        id: lensCtx.meta.id,
        label: lensCtx.meta.nombre,
        risk_score: lensCtx.meta.score,
        graphKind: lensCtx.meta.graphKind,
      })
      lens.setWorldPos(lensCtx.p.x, lensCtx.p.y)
      if (prevLensId !== lensCtx.nid) {
        prevResolvedLensIdRef.current = lensCtx.nid
        if (lensCtx.source === 'selection') {
          lens.activateLens()
        }
      }
      lens.renderLens(ctx, { dpr, width: w, height: h, transform: t })
    } else {
      if (prevLensId != null) {
        prevResolvedLensIdRef.current = null
        lens.deactivateLens()
      }
      lens.renderLens(ctx, { dpr, width: w, height: h, transform: t })
    }

    const needLoop =
      particlesRef.current.length > 0 ||
      visibleLinks.some((l) => l.level === 'malicious') ||
      [...visibleNodeIds].some((id) => (baseNodes.get(id)?.score || 0) > 80) ||
      lens.shouldKeepAnimationLoop()

    if (needLoop) requestRedraw()
  }, [
    chartSize.width,
    chartSize.height,
    baseNodes,
    visibleLinks,
    visibleNodeIds,
    showConnections,
    selectedId,
    alerts,
    requestRedraw,
  ])

  drawFrameRef.current = drawFrame

  useEffect(() => {
    requestRedraw()
  }, [
    requestRedraw,
    chartSize.width,
    chartSize.height,
    internalLinks,
    visibleNodeIds,
    showConnections,
    selectedId,
    minSeverityClamped,
    activeOnly,
  ])

  useEffect(() => {
    const svg = svgLabelsRef.current
    const container = containerRef.current
    if (!svg || !container) return undefined

    const w = chartSize.width
    const h = chartSize.height
    if (w < 48 || h < 48) return undefined

    d3.select(svg).selectAll('*').remove()
    const root = d3
      .select(svg)
      .append('g')
      .attr('class', 'network-map-zoom-root')
      .attr('transform', transformRef.current.toString())

    svgLabelsGRef.current = root.node()

    const g = root.append('g').attr('class', 'cluster-labels')

    const seen = new Set()
    for (const id of visibleNodeIds) {
      const meta = baseNodes.get(id)
      if (!meta) continue
      const key = meta.clusterKey
      if (seen.has(key)) continue
      seen.add(key)
      const c = clusterPixelCenter(key, w, h)
      g.append('text')
        .attr('x', c.cx)
        .attr('y', c.cy - 52)
        .attr('text-anchor', 'middle')
        .attr('class', 'network-map-cluster-label')
        .text(clusterLabel(key))
    }

    const zoom = d3
      .zoom()
      .scaleExtent([0.35, 3])
      .on('zoom', (event) => {
        transformRef.current = event.transform
        const gNode = svgLabelsGRef.current
        if (gNode) d3.select(gNode).attr('transform', event.transform.toString())
        requestRedraw()
      })

    zoomBehaviorRef.current = zoom
    const z = d3.select(container).call(zoom)
    z.on('dblclick.zoom', null)

    return () => {
      z.on('zoom', null)
      zoomBehaviorRef.current = null
    }
  }, [chartSize.width, chartSize.height, baseNodes, visibleNodeIds, requestRedraw])

  const handleCenterView = useCallback(() => {
    const container = containerRef.current
    const zoom = zoomBehaviorRef.current
    if (!container || !zoom) return
    const w = chartSize.width
    const h = chartSize.height
    const pos = positionsRef.current
    if (visibleNodeIds.size === 0) {
      d3.select(container).call(zoom.transform, d3.zoomIdentity)
      transformRef.current = d3.zoomIdentity
      requestRedraw()
      return
    }
    let minX = Infinity
    let minY = Infinity
    let maxX = -Infinity
    let maxY = -Infinity
    for (const id of visibleNodeIds) {
      const p = pos.get(id)
      const meta = baseNodes.get(id)
      if (!p || !meta) continue
      const r = meta.radius + 8
      minX = Math.min(minX, p.x - r)
      minY = Math.min(minY, p.y - r)
      maxX = Math.max(maxX, p.x + r)
      maxY = Math.max(maxY, p.y + r)
    }
    if (!Number.isFinite(minX)) return
    const bw = maxX - minX || 1
    const bh = maxY - minY || 1
    const pad = 48
    const scale = Math.min((w - pad * 2) / bw, (h - pad * 2) / bh, 1.2)
    const tx = w / 2 - (scale * (minX + maxX)) / 2
    const ty = h / 2 - (scale * (minY + maxY)) / 2
    const next = d3.zoomIdentity.translate(tx, ty).scale(scale)
    d3.select(container).transition().duration(400).call(zoom.transform, next)
  }, [chartSize.width, chartSize.height, visibleNodeIds, baseNodes, requestRedraw])

  useEffect(() => {
    if (!mapFocusNodeId) return
    const container = containerRef.current
    const zoom = zoomBehaviorRef.current
    if (!container || !zoom) return
    if (!baseNodes.has(mapFocusNodeId)) {
      clearMapFocusRequest()
      return
    }
    const meta = baseNodes.get(mapFocusNodeId)
    const p = positionsRef.current.get(mapFocusNodeId)
    const w = chartSize.width
    const h = chartSize.height
    if (!meta || !p || w < 48 || h < 48) return

    const focusPad = 56
    const extent = Math.max((meta.radius + 24) * 2, 88)
    const scale = Math.min((w - focusPad * 2) / extent, (h - focusPad * 2) / extent, 2)
    const k = Math.max(0.45, scale)
    const tx = w / 2 - k * p.x
    const ty = h / 2 - k * p.y
    const next = d3.zoomIdentity.translate(tx, ty).scale(k)
    d3.select(container).transition().duration(450).call(zoom.transform, next)

    const t = window.setTimeout(() => clearMapFocusRequest(), 480)
    return () => window.clearTimeout(t)
  }, [
    mapFocusNodeId,
    identityKey,
    chartSize.width,
    chartSize.height,
    baseNodes,
    clearMapFocusRequest,
  ])

  const screenToWorld = useCallback(
    (clientX, clientY) => {
      const canvas = canvasRef.current
      if (!canvas) return null
      const rect = canvas.getBoundingClientRect()
      const x = clientX - rect.left
      const y = clientY - rect.top
      const t = transformRef.current
      return { x: (x - t.x) / t.k, y: (y - t.y) / t.k }
    },
    [],
  )

  const pickNode = useCallback(
    (wx, wy) => {
      const pos = positionsRef.current
      let hit = null
      let best = Infinity
      for (const id of visibleNodeIds) {
        const meta = baseNodes.get(id)
        const p = pos.get(id)
        if (!meta || !p) continue
        const r = PICK_RADIUS_WORLD
        const d = Math.hypot(wx - p.x, wy - p.y)
        if (d <= r && d < best) {
          best = d
          hit = id
        }
      }
      return hit
    },
    [visibleNodeIds, baseNodes],
  )

  const pickLink = useCallback((wx, wy) => {
    const geoms = hoverRef.current._linkGeoms
    if (!geoms?.length) return null
    let bestD = 12
    let best = null
    for (const g of geoms) {
      const d = distToQuad(wx, wy, g.p0.x, g.p0.y, g.cx, g.cy, g.p1.x, g.p1.y)
      if (d < bestD) {
        bestD = d
        best = { key: `${g.link.source}|${g.link.target}`, link: g.link }
      }
    }
    return best
  }, [])

  const onCanvasMove = useCallback(
    (ev) => {
      const wpt = screenToWorld(ev.clientX, ev.clientY)
      if (!wpt) return
      const nid = pickNode(wpt.x, wpt.y)
      if (nid) {
        if (hoverRef.current.nodeId !== nid) {
          hoverRef.current.nodeId = nid
          hoverRef.current.linkKey = null
          const meta = baseNodes.get(nid)
          const p = positionsRef.current.get(nid)
          setHoverTip({
            x: ev.clientX,
            y: ev.clientY,
            type: 'node',
            nombre: meta?.nombre,
            area: meta?.area,
            score: meta?.score,
            edges: degreeById.get(nid) || 0,
          })
        } else {
          setHoverTip((prev) =>
            prev ? { ...prev, x: ev.clientX, y: ev.clientY } : prev,
          )
        }
        requestRedraw()
        return
      }
      const lp = pickLink(wpt.x, wpt.y)
      if (lp?.link) {
        if (hoverRef.current.linkKey !== lp.key) {
          hoverRef.current.linkKey = lp.key
          hoverRef.current.nodeId = null
          setHoverTip({
            x: ev.clientX,
            y: ev.clientY,
            type: 'link',
            traffic: lp.link.lastSource || 'interno',
            volume: lp.link.volume,
            level: lp.link.level,
          })
        } else {
          setHoverTip((prev) =>
            prev ? { ...prev, x: ev.clientX, y: ev.clientY } : prev,
          )
        }
        requestRedraw()
        return
      }
      hoverRef.current.nodeId = null
      hoverRef.current.linkKey = null
      setHoverTip(null)
      requestRedraw()
    },
    [screenToWorld, pickNode, pickLink, baseNodes, degreeById, requestRedraw],
  )

  const onCanvasLeave = useCallback(() => {
    hoverRef.current.nodeId = null
    hoverRef.current.linkKey = null
    setHoverTip(null)
    requestRedraw()
  }, [requestRedraw])

  const onCanvasClick = useCallback(
    (ev) => {
      const wpt = screenToWorld(ev.clientX, ev.clientY)
      if (!wpt) return
      const nid = pickNode(wpt.x, wpt.y)
      if (nid) openDetailPanel('identity', nid)
    },
    [screenToWorld, pickNode, openDetailPanel],
  )

  return (
    <div className="relative flex min-h-0 w-full min-w-0 flex-1 flex-col">
      <h2 className="mb-3 shrink-0 text-xl font-semibold text-[var(--base-bright)]">
        Internal Topology & Connections
      </h2>

      <div className="mb-3 grid shrink-0 grid-cols-1 gap-3 sm:grid-cols-3">
        <MetricCard label="Nodos visibles" value={visibleNodeIds.size} />
        <MetricCard label="Conexiones internas (5 min)" value={visibleLinks.length} />
        <MetricCard label="Eventos (5 min)" value={recentEvents5m} />
      </div>

      <div className="mb-2 shrink-0">
        <NetworkMapToolbar
          variant="bar"
          showConnections={showConnections}
          onToggleConnections={setShowConnections}
          minSeverity={minSeverityClamped}
          onMinSeverityChange={setMinSeverity}
          activeOnly={activeOnly}
          onToggleActiveOnly={setActiveOnly}
          onCenterView={handleCenterView}
        />
      </div>

      <div
        ref={containerRef}
        className="relative min-h-[min(60vh,520px)] w-full flex-1 overflow-hidden rounded-lg border border-[var(--border-default)] bg-[var(--base-deep)]"
      >
        <canvas
          ref={canvasRef}
          className="absolute left-0 top-0 block h-full w-full cursor-grab active:cursor-grabbing"
          onMouseMove={onCanvasMove}
          onMouseLeave={onCanvasLeave}
          onClick={onCanvasClick}
          aria-label="Mapa de red interna"
        />
        <svg
          ref={svgLabelsRef}
          className="pointer-events-none absolute left-0 top-0 h-full w-full text-[length:var(--text-xs)]"
          aria-hidden
        />

        <div className="pointer-events-none absolute inset-0">
          <style>{`
            .network-map-cluster-label {
              fill: var(--base-muted);
              font-family: var(--font-ui, system-ui, sans-serif);
              font-size: var(--text-xs);
              font-weight: 500;
              letter-spacing: 0.06em;
              text-transform: uppercase;
            }
          `}</style>
        </div>

        {baseNodes.size > 0 && visibleNodeIds.size === 0 ? (
          <div
            className="pointer-events-auto absolute inset-0 z-20 flex items-center justify-center p-6"
            role="status"
            aria-live="polite"
          >
            <div className="max-w-md rounded-lg border border-[var(--base-border)] bg-[var(--base-surface)]/95 px-5 py-4 text-center shadow-lg backdrop-blur">
              <p className="text-sm font-medium text-[var(--base-bright)]">
                Ningún nodo visible con los filtros actuales
              </p>
              <p className="mt-2 text-xs text-[var(--base-subtle)]">
                Subí el umbral de score mínimo demasiado, o activaste &quot;Solo activos&quot; sin eventos recientes
                para esas identidades. Bajá el slider o desactivá el filtro de activos.
              </p>
              <button
                type="button"
                className="mt-4 rounded border border-[var(--cyan-border)] bg-[var(--base-raised)] px-4 py-2 text-xs font-medium text-[var(--cyan-bright)] hover:bg-[var(--base-overlay)]"
                onClick={() => {
                  setMinSeverity(0)
                  setActiveOnly(false)
                }}
              >
                Restablecer filtros
              </button>
            </div>
          </div>
        ) : null}

        {hoverTip ? (
          <div
            className="pointer-events-none fixed z-30 max-w-xs rounded border border-[var(--base-border)] bg-[var(--base-overlay)] px-3 py-2 text-xs text-[var(--base-text)] shadow-lg"
            style={{ left: hoverTip.x + 12, top: hoverTip.y + 12 }}
          >
            {hoverTip.type === 'node' ? (
              <>
                <p className="font-semibold text-[var(--base-bright)]">{hoverTip.nombre}</p>
                <p className="text-[var(--base-subtle)]">{hoverTip.area}</p>
                <p className="mt-1 font-mono text-[var(--cyan-soft)]">
                  Risk {Math.round(hoverTip.score || 0)} · {hoverTip.edges} enlaces activos
                </p>
              </>
            ) : (
              <>
                <p className="font-semibold text-[var(--base-bright)]">Tráfico</p>
                <p className="text-[var(--base-subtle)]">{String(hoverTip.traffic)}</p>
                <p className="mt-1 text-[var(--cyan-soft)]">
                  Volumen {hoverTip.volume} · {hoverTip.level}
                </p>
              </>
            )}
          </div>
        ) : null}
      </div>
    </div>
  )
}
