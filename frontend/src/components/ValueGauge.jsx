import React from 'react'
import './ValueGauge.css'

function ValueGauge({ ticker, score, details }) {
  // score is 0-100, where 0 is on the left, 100 is on the right
  // We need to draw a semicircle from 180° (left) to 0° (right)
  // Score 0 = 180°, Score 100 = 0°
  
  const radius = 100
  const centerX = 120
  const centerY = 120
  const strokeWidth = 20
  
  // Helper function to convert percentage (0-100) to angle in degrees
  // 0% (left) = 180°, 100% (right) = 0°
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
  
  // Calculate text position - place it above the needle tip with consistent offset
  // Use a fixed radius offset from the center for uniform positioning
  const textRadius = radius + 35
  const textAngleRad = (scoreAngle * Math.PI) / 180
  const textX = centerX + textRadius * Math.cos(textAngleRad)
  const textY = centerY - textRadius * Math.sin(textAngleRad)
  
  // Calculate label positions
  const label0Point = angleToPoint(180)
  const label100Point = angleToPoint(0)
  const label25Point = angleToPoint(percentToAngle(25))
  const label50Point = angleToPoint(percentToAngle(50))
  const label75Point = angleToPoint(percentToAngle(75))
  
  return (
    <div className="value-gauge">
      <h3 className="gauge-title">{ticker}</h3>
      <svg width="240" height="140" className="gauge-svg" viewBox="0 0 240 140">
        <defs>
          {/* Background circle for perfect alignment */}
          <circle id="gauge-arc" cx={centerX} cy={centerY} r={radius} fill="none" />
          {/* Text background filter for better visibility */}
          <filter x="-50%" y="-50%" width="200%" height="200%" id="textbg">
            <feFlood floodColor="white" floodOpacity="0.9"/>
            <feComposite in="SourceGraphic"/>
          </filter>
        </defs>
        
        {/* Background semicircle (gray) */}
        <path
          d={createArc(0, 100)}
          fill="none"
          stroke="#e0e0e0"
          strokeWidth={strokeWidth}
          strokeLinecap="round"
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
          strokeWidth="3"
          strokeLinecap="round"
        />
        
        {/* Score text - with background for visibility */}
        <text
          x={textX}
          y={textY}
          textAnchor="middle"
          dominantBaseline="middle"
          className="gauge-score-text"
          fontSize="16"
          fontWeight="bold"
          filter="url(#textbg)"
        >
          {score.toFixed(0)}%
        </text>
        
        {/* Labels: 0%, 25%, 50%, 75%, 100% */}
        <text
          x={label0Point.x}
          y={label0Point.y + 15}
          textAnchor="middle"
          className="gauge-label"
          fontSize="11"
        >
          0%
        </text>
        <text
          x={label25Point.x}
          y={label25Point.y - 8}
          textAnchor="middle"
          className="gauge-label"
          fontSize="11"
        >
          25%
        </text>
        <text
          x={label50Point.x}
          y={label50Point.y - 8}
          textAnchor="middle"
          className="gauge-label"
          fontSize="11"
        >
          50%
        </text>
        <text
          x={label75Point.x}
          y={label75Point.y - 8}
          textAnchor="middle"
          className="gauge-label"
          fontSize="11"
        >
          75%
        </text>
        <text
          x={label100Point.x}
          y={label100Point.y + 15}
          textAnchor="middle"
          className="gauge-label"
          fontSize="11"
        >
          100%
        </text>
      </svg>
      
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

