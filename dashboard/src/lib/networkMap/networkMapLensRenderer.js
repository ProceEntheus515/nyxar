import { readCssVar } from '../../styles/cssVar'

const DEFAULT_BASE_RADIUS = 120
const OVERLAY_ALPHA = 0.72

function cssColor(varName, fallback) {
  const v = readCssVar(varName)
  return v || fallback
}

/**
 * Lente circular estilo spotlight: overlay en px de pantalla (post-zoom D3).
 * El centro sigue al nodo vía transform.apply([worldX, worldY]).
 */
export class NetworkMapLensRenderer {
  constructor() {
    /** @type {{ id: string, label: string, risk_score: number } | null} */
    this.targetMeta = null
    this.worldX = 0
    this.worldY = 0
    this._renderX = 0
    this._renderY = 0
    this._posInited = false
    this.lensBaseRadius = DEFAULT_BASE_RADIUS
    this.lensRadiusScreen = DEFAULT_BASE_RADIUS
    this.lensOpacity = 0
    this.lensAnimating = false
    /** @type {'idle' | 'open' | 'close' | 'pulse' | null} */
    this._mode = 'idle'
    this._animRaf = null
  }

  _cancelAnim() {
    if (this._animRaf != null) {
      cancelAnimationFrame(this._animRaf)
      this._animRaf = null
    }
  }

  /**
   * @param {{ id: string, label: string, risk_score: number } | null} meta
   */
  setTargetMeta(meta) {
    this.targetMeta = meta
  }

  setWorldPos(x, y) {
    this.worldX = x
    this.worldY = y
    if (!this._posInited) {
      this._renderX = x
      this._renderY = y
      this._posInited = true
    }
  }

  activateLens() {
    this._cancelAnim()
    this.lensAnimating = true
    this._mode = 'open'
    const startOpacity = this.lensOpacity
    const startTime = performance.now()
    const duration = 300
    const animate = (now) => {
      const progress = Math.min((now - startTime) / duration, 1)
      const eased = 1 - (1 - progress) ** 3
      this.lensOpacity = startOpacity + (1 - startOpacity) * eased
      if (progress < 1) {
        this._animRaf = requestAnimationFrame(animate)
      } else {
        this.lensAnimating = false
        this._mode = 'idle'
        this._animRaf = null
        this.lensOpacity = 1
      }
    }
    this._animRaf = requestAnimationFrame(animate)
  }

  deactivateLens() {
    this._cancelAnim()
    if (this.lensOpacity <= 0) {
      this.targetMeta = null
      this.lensRadiusScreen = this.lensBaseRadius
      this._posInited = false
      return
    }
    this.lensAnimating = true
    this._mode = 'close'
    const startOpacity = this.lensOpacity
    const startTime = performance.now()
    const duration = 200
    const animate = (now) => {
      const progress = Math.min((now - startTime) / duration, 1)
      this.lensOpacity = startOpacity * (1 - progress)
      if (progress < 1) {
        this._animRaf = requestAnimationFrame(animate)
      } else {
        this.lensAnimating = false
        this._mode = 'idle'
        this._animRaf = null
        this.lensOpacity = 0
        this.targetMeta = null
        this.lensRadiusScreen = this.lensBaseRadius
      }
    }
    this._animRaf = requestAnimationFrame(animate)
  }

  /**
   * Pulso breve sobre el objetivo ya definido (alerta crítica).
   */
  pulseAlert() {
    this._cancelAnim()
    this.lensAnimating = true
    this._mode = 'pulse'
    const startRadius = this.lensBaseRadius
    const pulseSequence = [
      { radius: startRadius * 1.3, opacity: 0.9, duration: 150 },
      { radius: startRadius * 0.9, opacity: 0.7, duration: 100 },
      { radius: startRadius * 1.15, opacity: 0.95, duration: 120 },
      { radius: startRadius, opacity: 1.0, duration: 100 },
    ]
    let currentStep = 0
    let stepStart = performance.now()

    const animatePulse = (now) => {
      if (currentStep >= pulseSequence.length) {
        this.lensRadiusScreen = startRadius
        this.lensOpacity = 1
        this.lensAnimating = false
        this._mode = 'idle'
        this._animRaf = null
        return
      }
      const step = pulseSequence[currentStep]
      const progress = Math.min((now - stepStart) / step.duration, 1)
      const prevRadius =
        currentStep === 0 ? startRadius : pulseSequence[currentStep - 1].radius
      const prevOpacity = currentStep === 0 ? 0 : pulseSequence[currentStep - 1].opacity

      this.lensRadiusScreen = prevRadius + (step.radius - prevRadius) * progress
      this.lensOpacity = prevOpacity + (step.opacity - prevOpacity) * progress

      if (progress >= 1) {
        currentStep += 1
        stepStart = now
      }
      this._animRaf = requestAnimationFrame(animatePulse)
    }
    this._animRaf = requestAnimationFrame(animatePulse)
  }

  /**
   * @param {CanvasRenderingContext2D} ctx
   * @param {{ dpr: number, width: number, height: number, transform: { apply: (xy: [number, number]) => [number, number] } }} opts
   */
  renderLens(ctx, opts) {
    const { dpr, width: w, height: h, transform } = opts
    if (!this.targetMeta || this.lensOpacity <= 0) return

    const lerpSpeed = 0.12
    this._renderX += (this.worldX - this._renderX) * lerpSpeed
    this._renderY += (this.worldY - this._renderY) * lerpSpeed

    const [sx, sy] = transform.apply([this._renderX, this._renderY])
    if (!Number.isFinite(sx) || !Number.isFinite(sy)) return

    const bgDeep = cssColor('--bg-00', '#060810')
    const action = cssColor('--action', '#38b2cc')
    const alert = cssColor('--alert', '#c23b52')
    const txMuted = cssColor('--tx-01', '#b8c8d8')

    const isAlert = Number(this.targetMeta.risk_score) >= 80
    const borderColor = isAlert ? alert : action
    const glowColor = isAlert ? 'rgba(194, 59, 82, 0.3)' : 'rgba(56, 178, 204, 0.3)'

    const r = this.lensRadiusScreen
    const overlayRgb = parseRgbOrFallback(bgDeep, 6, 8, 16)

    ctx.save()
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0)

    // No usar destination-out: borra el bitmap del grafo y deja el hueco transparente
    // (ya no hay nodos debajo). Semitransparencia solo FUERA del disco con evenodd.
    const a = OVERLAY_ALPHA * this.lensOpacity
    ctx.fillStyle = `rgba(${overlayRgb.r}, ${overlayRgb.g}, ${overlayRgb.b}, ${a})`
    ctx.beginPath()
    ctx.rect(0, 0, w, h)
    ctx.moveTo(sx + r, sy)
    ctx.arc(sx, sy, r, 0, Math.PI * 2, true)
    ctx.fill('evenodd')

    ctx.restore()

    ctx.save()
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0)

    ctx.beginPath()
    ctx.arc(sx, sy, r + 8, 0, Math.PI * 2)
    ctx.strokeStyle = glowColor
    ctx.lineWidth = 12
    ctx.globalAlpha = this.lensOpacity * 0.4
    ctx.stroke()

    ctx.beginPath()
    ctx.arc(sx, sy, r, 0, Math.PI * 2)
    ctx.strokeStyle = borderColor
    ctx.lineWidth = 1.5
    ctx.globalAlpha = this.lensOpacity * 0.8
    ctx.stroke()

    const crosshairLen = 16
    const crosshairGap = 18
    ctx.strokeStyle = borderColor
    ctx.lineWidth = 1
    ctx.globalAlpha = this.lensOpacity * 0.5
    ctx.beginPath()
    ctx.moveTo(sx - r - crosshairLen, sy)
    ctx.lineTo(sx - crosshairGap, sy)
    ctx.moveTo(sx + crosshairGap, sy)
    ctx.lineTo(sx + r + crosshairLen, sy)
    ctx.stroke()
    ctx.beginPath()
    ctx.moveTo(sx, sy - r - crosshairLen)
    ctx.lineTo(sx, sy - crosshairGap)
    ctx.moveTo(sx, sy + crosshairGap)
    ctx.lineTo(sx, sy + r + crosshairLen)
    ctx.stroke()

    // Nodo objetivo: dibujado ÚLTIMO para que nada lo tape
    const nodePx = 10
    const halfN = nodePx / 2

    // Halo suave
    ctx.globalAlpha = this.lensOpacity * 0.35
    ctx.fillStyle = borderColor
    ctx.beginPath()
    ctx.arc(sx, sy, nodePx + 6, 0, Math.PI * 2)
    ctx.fill()

    // Marcador central brillante
    ctx.globalAlpha = this.lensOpacity
    ctx.fillStyle = '#edf3fa'
    ctx.strokeStyle = borderColor
    ctx.lineWidth = 2
    if (this.targetMeta.graphKind === 'external') {
      ctx.save()
      ctx.translate(sx, sy)
      ctx.rotate(Math.PI / 4)
      ctx.fillRect(-halfN, -halfN, nodePx, nodePx)
      ctx.strokeRect(-halfN, -halfN, nodePx, nodePx)
      ctx.restore()
    } else {
      ctx.fillRect(sx - halfN, sy - halfN, nodePx, nodePx)
      ctx.strokeRect(sx - halfN, sy - halfN, nodePx, nodePx)
    }

    ctx.globalAlpha = this.lensOpacity
    const fontData = readCssVar('--font-data').trim()
    const fontStack = fontData || "'IBM Plex Mono', ui-monospace, monospace"
    ctx.font = `500 11px ${fontStack}`
    ctx.fillStyle = borderColor
    ctx.textAlign = 'center'
    ctx.fillText(this.targetMeta.label || this.targetMeta.id, sx, sy + r + 24)

    if (Number.isFinite(this.targetMeta.risk_score)) {
      ctx.font = `400 10px ${fontStack}`
      ctx.fillStyle = hexToRgba(txMuted, 0.7) || 'rgba(184, 200, 216, 0.7)'
      ctx.fillText(`SCORE ${Math.round(this.targetMeta.risk_score)}`, sx, sy + r + 36)
    }

    ctx.restore()
  }

  _isMoving() {
    const dx = this.worldX - this._renderX
    const dy = this.worldY - this._renderY
    return Math.abs(dx) > 0.5 || Math.abs(dy) > 0.5
  }

  shouldKeepAnimationLoop() {
    return (
      this.lensAnimating ||
      (this.lensOpacity > 0 && this.lensOpacity < 1) ||
      this._mode === 'pulse' ||
      (this.lensOpacity > 0 && this._isMoving())
    )
  }
}

function parseRgbOrFallback(hex, fr, fg, fb) {
  const h = String(hex || '').trim()
  if (h.startsWith('#') && (h.length === 7 || h.length === 4)) {
    if (h.length === 7) {
      return {
        r: parseInt(h.slice(1, 3), 16),
        g: parseInt(h.slice(3, 5), 16),
        b: parseInt(h.slice(5, 7), 16),
      }
    }
    const r = h[1]
    const g = h[2]
    const b = h[3]
    return {
      r: parseInt(r + r, 16),
      g: parseInt(g + g, 16),
      b: parseInt(b + b, 16),
    }
  }
  return { r: fr, g: fg, b: fb }
}

function hexToRgba(hex, alpha) {
  const rgb = parseRgbOrFallback(hex, 184, 200, 216)
  return `rgba(${rgb.r}, ${rgb.g}, ${rgb.b}, ${alpha})`
}
