import React from 'react'
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer
} from 'recharts'
import './PERatioChart.css'

function PERatioChart({ ticker, peTtm, peForward, price, compact = false }) {
  // Combine the data, grouping by date
  const dateMap = new Map()
  
  // Add P/E TTM data
  if (peTtm) {
    peTtm.forEach(item => {
      if (!dateMap.has(item.date)) {
        dateMap.set(item.date, { date: item.date })
      }
      dateMap.get(item.date).peTtm = item.value
    })
  }
  
  // Add Forward P/E data
  if (peForward) {
    peForward.forEach(item => {
      if (!dateMap.has(item.date)) {
        dateMap.set(item.date, { date: item.date })
      }
      dateMap.get(item.date).peForward = item.value
    })
  }
  
  // Add Price data
  if (price) {
    price.forEach(item => {
      if (!dateMap.has(item.date)) {
        dateMap.set(item.date, { date: item.date })
      }
      dateMap.get(item.date).price = item.value
    })
  }
  
  // Convert to array and sort by date
  const chartData = Array.from(dateMap.values())
    .map(item => ({
      ...item,
      date: item.date.split('T')[0] // Format date for display
    }))
    .sort((a, b) => new Date(a.date) - new Date(b.date))
  
  // Format date for display
  const formatDate = (dateStr) => {
    const date = new Date(dateStr)
    return date.toLocaleDateString('en-US', { year: 'numeric', month: 'short' })
  }
  
  // Format tooltip
  const CustomTooltip = ({ active, payload }) => {
    if (active && payload && payload.length) {
      return (
        <div className="custom-tooltip">
          <p className="tooltip-label">{payload[0].payload.date ? formatDate(payload[0].payload.date) : ''}</p>
          {payload.map((entry, index) => {
            if (entry.dataKey === 'peTtm') {
              return <p key={index} style={{ color: entry.color }}>{`TTM P/E: ${entry.value.toFixed(2)}`}</p>
            } else if (entry.dataKey === 'peForward') {
              return <p key={index} style={{ color: entry.color }}>{`Forward P/E: ${entry.value.toFixed(2)}`}</p>
            } else if (entry.dataKey === 'price') {
              return <p key={index} style={{ color: entry.color }}>{`Price: $${entry.value ? entry.value.toFixed(2) : 'N/A'}`}</p>
            }
            return null
          })}
        </div>
      )
    }
    return null
  }
  
  return (
    <div className={`pe-ratio-chart ${compact ? 'compact' : ''}`}>
      {!compact && <h3 className="chart-title">{ticker} P/E Ratios</h3>}
      <ResponsiveContainer width="100%" height={compact ? 100 : 400}>
        <LineChart data={chartData} margin={compact ? { top: 5, right: 5, left: 5, bottom: 5 } : { top: 5, right: 30, left: 20, bottom: 5 }}>
          {!compact && <CartesianGrid strokeDasharray="3 3" />}
          {!compact && (
            <XAxis 
              dataKey="date" 
              tickFormatter={formatDate}
              angle={-45}
              textAnchor="end"
              height={80}
            />
          )}
          {compact && <XAxis dataKey="date" hide />}
          {!compact && (
            <YAxis 
              yAxisId="pe"
              label={{ value: 'P/E Ratio', angle: -90, position: 'insideLeft' }}
            />
          )}
          {compact && <YAxis yAxisId="pe" hide />}
          {!compact && (
            <YAxis 
              yAxisId="price"
              orientation="right"
              label={{ value: 'Price ($)', angle: 90, position: 'insideRight' }}
            />
          )}
          {compact && <YAxis yAxisId="price" hide />}
          {!compact && <Tooltip content={<CustomTooltip />} />}
          {!compact && <Legend />}
          {peTtm && (
            <Line
              yAxisId="pe"
              type="monotone"
              dataKey="peTtm"
              stroke="#1f77b4"
              strokeWidth={2}
              name="TTM P/E"
              dot={false}
            />
          )}
          {peForward && (
            <Line
              yAxisId="pe"
              type="monotone"
              dataKey="peForward"
              stroke="#2ca02c"
              strokeWidth={2}
              strokeDasharray="5 5"
              name="Forward P/E"
              dot={false}
            />
          )}
          {price && (
            <Line
              yAxisId="price"
              type="monotone"
              dataKey="price"
              stroke="#ff7f0e"
              strokeWidth={2}
              name="Price"
              dot={false}
            />
          )}
        </LineChart>
      </ResponsiveContainer>
    </div>
  )
}

export default PERatioChart

