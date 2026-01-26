import React, { useEffect, useRef } from 'react'
import '../lib/gauge.js'

const getPointerColor = () =>
  document.body.classList.contains('dark-mode') ? '#ffffff' : '#000000'

function ValueGaugeCompact({ ticker, score, type = 'pe' }) {
  const canvasRef = useRef(null)
  const gaugeRef = useRef(null)
  const textFieldRef = useRef(null)
  const wrapperRef = useRef(null)

  useEffect(() => {
    if (!gaugeRef.current) return

    const updateTheme = () => {
      const color = getPointerColor()
      gaugeRef.current.setOptions({
        pointer: { color }
      })
      gaugeRef.current.render()
    }

    updateTheme()

    const observer = new MutationObserver(updateTheme)
    observer.observe(document.body, {
      attributes: true,
      attributeFilter: ['class']
    })

    return () => observer.disconnect()
  }, [])

  useEffect(() => {
    if (!canvasRef.current || !window.Gauge) return

    if (!gaugeRef.current) {
      const ctx = canvasRef.current.getContext('2d')
      ctx.clearRect(0, 0, canvasRef.current.width, canvasRef.current.height)

      const textFieldEl = document.createElement('div')
      textFieldEl.className = 'gauge-text-field-compact'
      const parent = wrapperRef.current || canvasRef.current.parentNode
      if (parent) {
        parent.appendChild(textFieldEl)
      }
      textFieldRef.current = textFieldEl

      gaugeRef.current = new window.Gauge(canvasRef.current)
      gaugeRef.current.setOptions({
        angle: 0,
        lineWidth: 0.25,
        radiusScale: 1.0,
        pointer: {
          length: 0.6,
          strokeWidth: 0.05,
          iconScale: 1,
          color: getPointerColor()
        },
        limitMax: true,
        limitMin: true,
        strokeColor: '#e0e0e0',
        highDpiSupport: true,
        percentColors: [
          [0.0, "#dc3545"],
          [0.50, "#ffc107"],
          [1.0, "#28a745"]
        ],
        staticZones: null,
        generateGradient: true,
        fontSize: 12
      })
      gaugeRef.current.maxValue = 100
      gaugeRef.current.minValue = 0
      gaugeRef.current.setTextField(textFieldEl, 0)
    }

    if (gaugeRef.current && typeof score === 'number') {
      gaugeRef.current.set(score)
    }

    return () => {
      if (textFieldRef.current && textFieldRef.current.parentNode) {
        textFieldRef.current.parentNode.removeChild(textFieldRef.current)
      }
    }
  }, [score])

  return (
    <div className="value-gauge-compact">
      <div className="gauge-wrapper-compact" ref={wrapperRef}>
        <canvas ref={canvasRef} width="100" height="60" className="gauge-canvas-compact"></canvas>
      </div>
      <div className="gauge-ticker-compact">
        {type === 'pe' ? 'Relative PE' : type.toUpperCase()}: {ticker}
      </div>
    </div>
  )
}

export default ValueGaugeCompact
