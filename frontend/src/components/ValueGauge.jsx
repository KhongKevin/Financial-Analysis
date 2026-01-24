import React, { useEffect, useRef } from 'react'
import '../lib/gauge.js'
import './ValueGauge.css'

const getPointerColor = () =>
  document.body.classList.contains('dark-mode') ? '#ffffff' : '#000000'


function ValueGauge({ ticker, score, details }) {
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
  
    // Watch for class changes on <body>
    const observer = new MutationObserver(updateTheme)
    observer.observe(document.body, {
      attributes: true,
      attributeFilter: ['class']
    })
  
    return () => observer.disconnect()
  }, [])
  useEffect(() => {
    if (!canvasRef.current || !window.Gauge) return

    // Initialize gauge
    if (!gaugeRef.current) {
      // Create text field element for displaying the score
      const textFieldEl = document.createElement('div')
      textFieldEl.className = 'gauge-text-field'
      // Append to wrapper if available, otherwise append to canvas parent
      const parent = wrapperRef.current || canvasRef.current.parentNode
      if (parent) {
        parent.appendChild(textFieldEl)
      }
      textFieldRef.current = textFieldEl

      // Initialize gauge with semicircle configuration
      gaugeRef.current = new window.Gauge(canvasRef.current)
      gaugeRef.current.setOptions({
        angle: 0, // Full semicircle from left to right (180 degrees)
        lineWidth: 0.2,
        radiusScale: 1.0,
        pointer: {
          length: 0.7,
          strokeWidth: 0.04,
          iconScale: 1,
          color: getPointerColor()
        },
        limitMax: true,
        limitMin: true,
        strokeColor: '#e0e0e0',
        highDpiSupport: true,
        staticZones: [
          { strokeStyle: '#dc3545', min: 0, max: 50 },
          { strokeStyle: '#ffc107', min: 50, max: 75 },
          { strokeStyle: '#28a745', min: 75, max: 100 }
        ],
        staticLabels: {
          font: '12px sans-serif',
          labels: [0, 25, 50, 75, 100],
          fractionDigits: 0,
          color: getPointerColor()
        },
        fontSize: 24
      })
      gaugeRef.current.maxValue = 100
      gaugeRef.current.minValue = 0
      gaugeRef.current.setTextField(textFieldEl, 0)
    }

    // Update gauge value
    if (gaugeRef.current && typeof score === 'number') {
      gaugeRef.current.set(score)
    }

    return () => {
      // Cleanup: remove text field if component unmounts
      if (textFieldRef.current && textFieldRef.current.parentNode) {
        textFieldRef.current.parentNode.removeChild(textFieldRef.current)
      }
    }
  }, [score])

  return (
    <div className="value-gauge">
      <h3 className="gauge-title">{ticker}</h3>
      <div className="gauge-wrapper" ref={wrapperRef}>
        <canvas ref={canvasRef} width="240" height="120" className="gauge-canvas"></canvas>
      </div>
      
      {details && (
        <div className="gauge-details">
          <div className="detail-item">
            <span className="detail-label">Current P/E:</span>
            <span className="detail-value">{details.current_pe.toFixed(2)}</span>
          </div>
          <div className="detail-item">
            <span className="detail-label">Avg P/E:</span>
            <span className="detail-value">{details.avg_pe.toFixed(2)}</span>
          </div>
          <div className="detail-item">
            <span className="detail-label">Min P/E:</span>
            <span className="detail-value">{details.min_pe.toFixed(2)}</span>
          </div>
          <div className="detail-item">
            <span className="detail-label">Max P/E:</span>
            <span className="detail-value">{details.max_pe.toFixed(2)}</span>
          </div>
        </div>
      )}
    </div>
  )
}

export default ValueGauge

