import { useCallback, useEffect, useRef, type ReactNode } from 'react'
import { cn } from '../../lib/utils'

interface Point {
  x: number
  y: number
}

interface Ripple extends Point {
  radius: number
  opacity: number
  born: number
}

interface Color {
  r: number
  g: number
  b: number
  a: number
}

interface KineticGridProps {
  children?: ReactNode
  className?: string
  tone?: 'light' | 'dark' | 'monochrome'
}

const CELL_SIZE = 55
const INFLUENCE_RADIUS = 260
const MAX_WARP = 24
const DOT_SPACING = 28
const LERP_SPEED = 0.08
const POINTER_AWAY = -9999

const themes = {
  light: {
    background: '#ffffff',
    lineBase: { r: 37, g: 100, b: 154, a: 0.07 },
    lineActive: { r: 37, g: 100, b: 154, a: 0.48 },
    nodeBase: { r: 37, g: 100, b: 154, a: 0.1 },
    nodeActive: { r: 37, g: 100, b: 154, a: 0.76 },
    dot: 'rgba(37,100,154,0.025)',
    glow: '37,100,154',
    ripple: '37,100,154',
  },
  dark: {
    background: '#161618',
    lineBase: { r: 255, g: 255, b: 255, a: 0.13 },
    lineActive: { r: 74, g: 158, b: 255, a: 0.9 },
    nodeBase: { r: 255, g: 255, b: 255, a: 0.2 },
    nodeActive: { r: 74, g: 158, b: 255, a: 1 },
    dot: 'rgba(255,255,255,0.05)',
    glow: '74,158,255',
    ripple: '100,180,255',
  },
  monochrome: {
    background: '#000000',
    lineBase: { r: 255, g: 255, b: 255, a: 0.13 },
    lineActive: { r: 255, g: 255, b: 255, a: 0.9 },
    nodeBase: { r: 255, g: 255, b: 255, a: 0.2 },
    nodeActive: { r: 255, g: 255, b: 255, a: 1 },
    dot: 'rgba(255,255,255,0.05)',
    glow: '255,255,255',
    ripple: '255,255,255',
  },
} as const

function lerp(a: number, b: number, amount: number) {
  return a + (b - a) * amount
}

function lerpColor(base: Color, active: Color, amount: number) {
  const red = Math.round(lerp(base.r, active.r, amount))
  const green = Math.round(lerp(base.g, active.g, amount))
  const blue = Math.round(lerp(base.b, active.b, amount))
  const alpha = lerp(base.a, active.a, amount)
  return `rgba(${red},${green},${blue},${alpha.toFixed(3)})`
}

export function KineticGrid({ children, className, tone = 'light' }: KineticGridProps) {
  const rootRef = useRef<HTMLDivElement>(null)
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const pointerRef = useRef<Point>({ x: POINTER_AWAY, y: POINTER_AWAY })
  const targetPointerRef = useRef<Point>({ x: POINTER_AWAY, y: POINTER_AWAY })
  const ripplesRef = useRef<Ripple[]>([])
  const frameRef = useRef(0)
  const sizeRef = useRef({ width: 0, height: 0 })

  const getWarpedPoint = useCallback((
    gridX: number,
    gridY: number,
    column: number,
    row: number,
    pointer: Point,
    ripples: Ripple[],
    columns: number,
    rows: number,
  ) => {
    const edgeMargin = 1.5
    const columnPin = Math.min(column / edgeMargin, (columns - 1 - column) / edgeMargin, 1)
    const rowPin = Math.min(row / edgeMargin, (rows - 1 - row) / edgeMargin, 1)
    const pinFactor = columnPin * columnPin * rowPin * rowPin
    const deltaX = gridX - pointer.x
    const deltaY = gridY - pointer.y
    const distance = Math.hypot(deltaX, deltaY)
    const proximity = Math.max(0, 1 - distance / INFLUENCE_RADIUS) * pinFactor
    let rippleX = 0
    let rippleY = 0

    for (const ripple of ripples) {
      const deltaRippleX = gridX - ripple.x
      const deltaRippleY = gridY - ripple.y
      const rippleDistance = Math.hypot(deltaRippleX, deltaRippleY)
      const difference = rippleDistance - ripple.radius
      const waveWidth = 55

      if (Math.abs(difference) < waveWidth) {
        const strength = (1 - Math.abs(difference) / waveWidth) * ripple.opacity * 18 * pinFactor
        const angle = Math.atan2(deltaRippleY, deltaRippleX)
        const direction = difference < 0 ? -1 : 1
        rippleX -= Math.cos(angle) * strength * direction
        rippleY -= Math.sin(angle) * strength * direction
      }
    }

    if (distance < INFLUENCE_RADIUS && distance > 0 && pinFactor > 0) {
      const progress = distance / INFLUENCE_RADIUS
      const eased = progress < 0.01 ? 0 : (1 - progress) ** 2 * Math.min(1, distance / 60)
      const warpAmount = eased * MAX_WARP * pinFactor
      const angle = Math.atan2(deltaY, deltaX)
      return {
        point: {
          x: gridX - Math.cos(angle) * warpAmount + rippleX,
          y: gridY - Math.sin(angle) * warpAmount + rippleY,
        },
        proximity,
      }
    }

    return { point: { x: gridX + rippleX, y: gridY + rippleY }, proximity }
  }, [])

  const draw = useCallback((now: number) => {
    const canvas = canvasRef.current
    if (!canvas) return
    const context = canvas.getContext('2d')
    if (!context) return

    const { width, height } = sizeRef.current
    if (width <= 0 || height <= 0) return
    const pointer = pointerRef.current
    const ripples = ripplesRef.current
    const theme = themes[tone]

    context.clearRect(0, 0, width, height)
    context.fillStyle = theme.background
    context.fillRect(0, 0, width, height)

    context.fillStyle = theme.dot
    for (let x = DOT_SPACING / 2; x < width; x += DOT_SPACING) {
      for (let y = DOT_SPACING / 2; y < height; y += DOT_SPACING) {
        context.beginPath()
        context.arc(x, y, 0.7, 0, Math.PI * 2)
        context.fill()
      }
    }

    for (let index = ripples.length - 1; index >= 0; index -= 1) {
      const ripple = ripples[index]
      if (!ripple) continue
      const age = (now - ripple.born) / 1000
      ripple.radius = Math.max(0, age * 400)
      ripple.opacity = Math.max(0, 1 - age * 1.2)
      if (ripple.opacity <= 0) ripples.splice(index, 1)
    }

    const columns = Math.max(2, Math.ceil(width / CELL_SIZE)) + 1
    const rows = Math.max(2, Math.ceil(height / CELL_SIZE)) + 1
    const cellWidth = width / (columns - 1)
    const cellHeight = height / (rows - 1)
    const points: Point[][] = []
    const proximities: number[][] = []

    for (let row = 0; row < rows; row += 1) {
      const rowPoints: Point[] = []
      const rowProximities: number[] = []
      points[row] = rowPoints
      proximities[row] = rowProximities
      for (let column = 0; column < columns; column += 1) {
        const warped = getWarpedPoint(column * cellWidth, row * cellHeight, column, row, pointer, ripples, columns, rows)
        rowPoints[column] = warped.point
        rowProximities[column] = warped.proximity
      }
    }

    const drawSegment = (start: Point, end: Point, startProximity: number, endProximity: number) => {
      const average = (startProximity + endProximity) / 2
      const intensity = average * average * (3 - 2 * average)
      context.beginPath()
      context.moveTo(start.x, start.y)
      context.lineTo(end.x, end.y)
      context.strokeStyle = lerpColor(theme.lineBase, theme.lineActive, intensity)
      context.lineWidth = lerp(0.7, 1.4, intensity)
      context.stroke()
    }

    context.lineCap = 'butt'
    for (let row = 0; row < rows; row += 1) {
      for (let column = 0; column < columns - 1; column += 1) {
        const start = points[row]?.[column]
        const end = points[row]?.[column + 1]
        const startProximity = proximities[row]?.[column]
        const endProximity = proximities[row]?.[column + 1]
        if (start && end && startProximity !== undefined && endProximity !== undefined) drawSegment(start, end, startProximity, endProximity)
      }
    }
    for (let column = 0; column < columns; column += 1) {
      for (let row = 0; row < rows - 1; row += 1) {
        const start = points[row]?.[column]
        const end = points[row + 1]?.[column]
        const startProximity = proximities[row]?.[column]
        const endProximity = proximities[row + 1]?.[column]
        if (start && end && startProximity !== undefined && endProximity !== undefined) drawSegment(start, end, startProximity, endProximity)
      }
    }

    for (let row = 0; row < rows; row += 1) {
      for (let column = 0; column < columns; column += 1) {
        const point = points[row]?.[column]
        const proximity = proximities[row]?.[column]
        if (!point || proximity === undefined) continue
        const intensity = proximity * proximity * (3 - 2 * proximity)
        const radius = lerp(1.35, 2.8, intensity)

        if (intensity > 0.3) {
          const glowRadius = radius + lerp(0, 6, (intensity - 0.3) / 0.7)
          const gradient = context.createRadialGradient(point.x, point.y, radius * 0.5, point.x, point.y, glowRadius)
          gradient.addColorStop(0, `rgba(${theme.glow},${(intensity * 0.24).toFixed(3)})`)
          gradient.addColorStop(1, `rgba(${theme.glow},0)`)
          context.beginPath()
          context.arc(point.x, point.y, glowRadius, 0, Math.PI * 2)
          context.fillStyle = gradient
          context.fill()
        }

        context.beginPath()
        context.arc(point.x, point.y, radius, 0, Math.PI * 2)
        context.fillStyle = lerpColor(theme.nodeBase, theme.nodeActive, intensity)
        context.fill()
      }
    }

    for (const ripple of ripples) {
      context.beginPath()
      context.arc(ripple.x, ripple.y, Math.max(0, ripple.radius), 0, Math.PI * 2)
      context.strokeStyle = `rgba(${theme.ripple},${(ripple.opacity * 0.2).toFixed(3)})`
      context.lineWidth = 1.25
      context.stroke()
    }
  }, [getWarpedPoint, tone])

  useEffect(() => {
    const root = rootRef.current
    const canvas = canvasRef.current
    if (!root || !canvas) return

    const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches
    const animateFrame = (now: number) => {
      const pointer = pointerRef.current
      const target = targetPointerRef.current
      pointer.x = lerp(pointer.x, target.x, LERP_SPEED)
      pointer.y = lerp(pointer.y, target.y, LERP_SPEED)
      draw(now)
      frameRef.current = requestAnimationFrame(animateFrame)
    }
    const setSize = () => {
      const { width, height } = root.getBoundingClientRect()
      const density = Math.min(window.devicePixelRatio || 1, 2)
      canvas.width = Math.max(1, Math.round(width * density))
      canvas.height = Math.max(1, Math.round(height * density))
      canvas.getContext('2d')?.setTransform(density, 0, 0, density, 0, 0)
      sizeRef.current = { width, height }
      if (reducedMotion) draw(performance.now())
    }

    const onPointerMove = (event: PointerEvent) => {
      const bounds = root.getBoundingClientRect()
      targetPointerRef.current = { x: event.clientX - bounds.left, y: event.clientY - bounds.top }
    }
    const onPointerLeave = () => {
      targetPointerRef.current = { x: POINTER_AWAY, y: POINTER_AWAY }
    }
    const onPointerDown = (event: PointerEvent) => {
      if (reducedMotion) return
      const bounds = root.getBoundingClientRect()
      ripplesRef.current.push({
        x: event.clientX - bounds.left,
        y: event.clientY - bounds.top,
        radius: 0,
        opacity: 1,
        born: performance.now(),
      })
    }

    const resizeObserver = new ResizeObserver(setSize)
    resizeObserver.observe(root)
    root.addEventListener('pointermove', onPointerMove, { passive: true })
    root.addEventListener('pointerleave', onPointerLeave, { passive: true })
    root.addEventListener('pointerdown', onPointerDown, { passive: true })
    setSize()
    if (reducedMotion) draw(performance.now())
    else frameRef.current = requestAnimationFrame(animateFrame)

    return () => {
      resizeObserver.disconnect()
      root.removeEventListener('pointermove', onPointerMove)
      root.removeEventListener('pointerleave', onPointerLeave)
      root.removeEventListener('pointerdown', onPointerDown)
      cancelAnimationFrame(frameRef.current)
    }
  }, [draw])

  return (
    <div ref={rootRef} className={cn('relative h-full w-full overflow-hidden', className)}>
      <canvas ref={canvasRef} aria-hidden="true" className="pointer-events-none absolute inset-0 size-full" />
      <div className="relative z-10 h-full w-full">{children}</div>
    </div>
  )
}
