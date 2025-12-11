import React from 'react'
import './ValueGauge.css'

function ValueGaugeCompact({ ticker, score }) {
  // Compact version of gauge for list view
  // Smaller size with thicker stroke for visibility
  const radius = 40
  const centerX = 50
  const centerY = 50
  const strokeWidth = 12 // Thicker for visibility at small size
  
  // Helper function to convert percentage (0-100) to angle in degrees
  const percentToAngle = (percent) => 180 - (percent / 100) * 180
  
  // Helper function to get point on arc from angle
  const angleToPoint = (angleDeg) => {
    const angleRad = (angleDeg * Math.PI) / 180
    return {
      x: centerX + radius * Math.cos(angleRad),
      y: centerY - radius * Math.sin(angleRad)
    }
  }
  
  // Helper function to create arc path
  const createArc = (startPercent, endPercent) => {
    const startAngle = percentToAngle(startPercent)
    const endAngle = percentToAngle(endPercent)
    const startPoint = angleToPoint(startAngle)
    const endPoint = angleToPoint(endAngle)
    const largeArc = endPercent - startPercent > 50 ? 1 : 0
    return `M ${startPoint.x} ${startPoint.y} A ${radius} ${radius} 0 ${largeArc} 1 ${endPoint.x} ${endPoint.y}`
  }
  
  // Calculate score angle and position
  const scoreAngle = percentToAngle(score)
  const scorePoint = angleToPoint(scoreAngle)
  
  return (
    <div className="value-gauge-compact">
      <svg width="100" height="60" className="gauge-svg-compact" viewBox="0 0 100 60">
        {/* Background semicircle (gray) */}
        <path
          d={createArc(0, 100)}
          fill="none"
          stroke="currentColor"
          strokeWidth={strokeWidth}
          strokeLinecap="round"
          className="gauge-background"
        />
        
        {/* Red zone: 0-50% */}
        <path
          d={createArc(0, 50)}
          fill="none"
          stroke="#dc3545"
          strokeWidth={strokeWidth}
          strokeLinecap="round"
        />
        
        {/* Yellow zone: 50-75% */}
        <path
          d={createArc(50, 75)}
          fill="none"
          stroke="#ffc107"
          strokeWidth={strokeWidth}
          strokeLinecap="round"
        />
        
        {/* Green zone: 75-100% */}
        <path
          d={createArc(75, 100)}
          fill="none"
          stroke="#28a745"
          strokeWidth={strokeWidth}
          strokeLinecap="round"
        />
        
        {/* Score marker line (pointer) */}
        <line
          x1={centerX}
          y1={centerY}
          x2={scorePoint.x}
          y2={scorePoint.y}
          stroke="#333"
          strokeWidth="2"
          strokeLinecap="round"
        />
        
        {/* Score text */}
        <text
          x={centerX}
          y={centerY + 8}
          textAnchor="middle"
          dominantBaseline="middle"
          className="gauge-score-text-compact"
          fontSize="10"
          fontWeight="bold"
        >
          {score.toFixed(0)}%
        </text>
      </svg>
      <div className="gauge-ticker-compact">{ticker}</div>
    </div>
  )
}

export default ValueGaugeCompact

