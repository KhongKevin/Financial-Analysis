import React, { useState, useEffect } from 'react'
import ValueGauge from '../components/ValueGauge'
import ValueGaugeCompact from '../components/ValueGaugeCompact'
import PERatioChart from '../components/PERatioChart'
import './Home.css'

function Home() {
  const [tickers, setTickers] = useState('NFLX,AMD,GOOG,NVDA,INTC,AMZN')
  const [years, setYears] = useState('2')
  const [chartYears, setChartYears] = useState('5')
  const [allData, setAllData] = useState([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [expandedStock, setExpandedStock] = useState(null)

  const loadAllData = async () => {
    setLoading(true)
    setError('')
    try {
      const tickerList = tickers.split(',').map(t => t.trim()).filter(t => t)
      
      // Load both gauge and chart data
      const [gaugeResponse, chartResponse] = await Promise.all([
        fetch('/api/batch/value_pe_avg', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            tickers: tickerList,
            years: parseInt(years),
            filename: 'EPS_manual.txt'
          })
        }),
        fetch('/api/batch/pe_ratios', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            tickers: tickerList,
            years: parseInt(chartYears),
            source: 'manual',
            include_forward: true,
            smoothing: 0,
            filename: 'EPS_manual.txt'
          })
        })
      ])

      const gaugeData = await gaugeResponse.json()
      const chartData = await chartResponse.json()

      if (gaugeData.success && chartData.success) {
        // Combine data by ticker
        const dataMap = new Map()
        
        gaugeData.results.filter(r => r.success).forEach(item => {
          dataMap.set(item.ticker, {
            ticker: item.ticker,
            score: item.score_100,
            details: item.details,
            gaugeData: item
          })
        })

        chartData.results.filter(r => r.success).forEach(item => {
          const existing = dataMap.get(item.ticker) || { ticker: item.ticker }
          existing.chartData = item
          dataMap.set(item.ticker, existing)
        })

        // Convert to array and sort by score (highest first)
        const sortedData = Array.from(dataMap.values())
          .filter(item => item.score !== undefined)
          .sort((a, b) => (b.score || 0) - (a.score || 0))

        setAllData(sortedData)
      } else {
        setError('Failed to load data')
      }
    } catch (err) {
      setError(`Error: ${err.message}`)
    } finally {
      setLoading(false)
    }
  }

  const toggleExpand = (ticker) => {
    setExpandedStock(expandedStock === ticker ? null : ticker)
  }

  useEffect(() => {
    // Auto-load on mount
    loadAllData()
  }, [])

  return (
    <div className="home-page">
      <div className="controls">
        <input
          type="text"
          placeholder="Tickers (comma-separated)"
          value={tickers}
          onChange={(e) => setTickers(e.target.value)}
        />
        <label>
          Years (Gauges):
          <input
            type="number"
            value={years}
            onChange={(e) => setYears(e.target.value)}
            min="1"
            max="10"
            style={{ width: '60px', marginLeft: '5px' }}
          />
        </label>
        <label>
          Years (Charts):
          <input
            type="number"
            value={chartYears}
            onChange={(e) => setChartYears(e.target.value)}
            min="1"
            max="20"
            style={{ width: '60px', marginLeft: '5px' }}
          />
        </label>
        <button onClick={loadAllData} disabled={loading}>
          {loading ? 'Loading...' : 'Load Data'}
        </button>
      </div>

      {error && <div className="error">{error}</div>}

      {allData.length > 0 && (
        <div className="stock-list">
          {allData.map((item, index) => (
            <div key={item.ticker} className="stock-item">
              <div 
                className="stock-header"
                onClick={() => toggleExpand(item.ticker)}
              >
                <div className="stock-rank">#{index + 1}</div>
                <div className="stock-name">{item.ticker}</div>
                <div className="stock-score">Score: {item.score?.toFixed(0)}%</div>
                <div className="stock-previews">
                  <ValueGaugeCompact ticker={item.ticker} score={item.score} />
                  {item.chartData && (
                    <div className="chart-thumbnail">
                      <PERatioChart
                        ticker={item.ticker}
                        peTtm={item.chartData.pe_ttm}
                        peForward={item.chartData.pe_forward}
                        price={item.chartData.price}
                        compact={true}
                      />
                    </div>
                  )}
                </div>
                <div className="expand-indicator">
                  {expandedStock === item.ticker ? '▼' : '▶'}
                </div>
              </div>
              
              {expandedStock === item.ticker && (
                <div className="stock-expanded">
                  <div className="expanded-gauge">
                    <ValueGauge
                      ticker={item.ticker}
                      score={item.score}
                      details={item.details}
                    />
                  </div>
                  {item.chartData && (
                    <div className="expanded-chart">
                      <PERatioChart
                        ticker={item.ticker}
                        peTtm={item.chartData.pe_ttm}
                        peForward={item.chartData.pe_forward}
                        price={item.chartData.price}
                      />
                    </div>
                  )}
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

export default Home

