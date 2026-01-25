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

  const getCompanyName = (ticker) => {
    const names = {
      'NFLX': 'Netflix, Inc.',
      'AMD': 'Advanced Micro Devices, Inc.',
      'GOOG': 'Alphabet Inc.',
      'NVDA': 'NVIDIA Corporation',
      'INTC': 'Intel Corporation',
      'AMZN': 'Amazon.com, Inc.',
      'TSLA': 'Tesla, Inc.',
      'UNH': 'UnitedHealth Group Incorporated'
    }
    return names[ticker] || ''
  }

  // ... inside Home component ...
  const [missingTickers, setMissingTickers] = useState([])
  const [fetchingTicker, setFetchingTicker] = useState(null)

  const loadAllData = async () => {
    setLoading(true)
    setError('')
    setMissingTickers([])
    try {
      const tickerList = tickers.split(',').map(t => t.trim()).filter(t => t)

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

      const newMissing = new Set()

      if (gaugeData.success && chartData.success) {
        const dataMap = new Map()

        gaugeData.results.forEach(item => {
          if (item.success) {
            dataMap.set(item.ticker, {
              ticker: item.ticker,
              score: item.score_100,
              details: item.details,
              gaugeData: item
            })
          } else if (item.error_code === 'MISSING_DATA') {
            newMissing.add(item.ticker)
          }
        })

        chartData.results.forEach(item => {
          if (item.success) {
            const existing = dataMap.get(item.ticker) || { ticker: item.ticker }
            existing.chartData = item
            dataMap.set(item.ticker, existing)
          }
          // If chart also reports missing, it's already caught or will be.
        })

        const sortedData = Array.from(dataMap.values())
          .filter(item => item.score !== undefined)
          .sort((a, b) => (b.score || 0) - (a.score || 0))

        setAllData(sortedData)
        setMissingTickers(Array.from(newMissing))
      } else {
        setError('Failed to load data')
      }
    } catch (err) {
      setError(`Error: ${err.message}`)
    } finally {
      setLoading(false)
    }
  }

  const handleFetchData = async (ticker) => {
    setFetchingTicker(ticker)
    try {
      const res = await fetch(`/api/fetch_eps/${ticker}`, { method: 'POST' })
      const data = await res.json()
      if (data.success) {
        let message = `Data fetched for ${ticker}.`
        if (data.warning) {
          message += `\n\n⚠️ ${data.warning}`
        }
        alert(message)
        loadAllData()
      } else {
        alert(`Failed to fetch: ${data.error}`)
      }
    } catch (err) {
      alert(`Error: ${err.message}`)
    } finally {
      setFetchingTicker(null)
    }
  }

  // Helper to check if data is sparse (likely annual)
  const isAnnualData = (ticker) => {
    // Check if ticker has fewer than 8 data points (less than 2 years quarterly)
    // This is a heuristic - we'd need backend to track this properly
    // For now, we'll add this check when we have the data count
    return false // Placeholder
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
        <label>
          Stocks:
          <input
            type="text"
            placeholder="Tickers (comma-separated)"
            value={tickers}
            onChange={(e) => setTickers(e.target.value)}
            style={{ marginLeft: '5px' }}
          />
        </label>
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
        <button className="load-button" onClick={loadAllData} disabled={loading}>
          {loading ? 'Loading...' : 'Load Data'}
        </button>
      </div>

      {error && <div className="error">{error}</div>}

      {/* Modal for Missing Data */}
      {missingTickers.length > 0 && (
        <div style={{
          position: 'fixed',
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          backgroundColor: 'rgba(0, 0, 0, 0.7)',
          backdropFilter: 'blur(5px)',
          display: 'flex',
          justifyContent: 'center',
          alignItems: 'center',
          zIndex: 2000
        }}>
          <div className="glass-card" style={{
            width: '400px',
            padding: '2rem',
            display: 'flex',
            flexDirection: 'column',
            gap: '1.5rem',
            boxShadow: '0 8px 32px rgba(0, 0, 0, 0.5)'
          }}>
            <h2 style={{ margin: 0, color: '#fff', fontSize: '1.5rem' }}>Missing Data Found</h2>
            <p style={{ color: 'rgba(255, 255, 255, 0.8)', margin: 0 }}>
              The following tickers are missing from the local database. Would you like to fetch their data?
            </p>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
              {missingTickers.map(t => (
                <div key={t} style={{
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  background: 'rgba(255, 255, 255, 0.05)',
                  padding: '10px',
                  borderRadius: '8px'
                }}>
                  <span style={{ fontWeight: '700', fontSize: '1.1rem' }}>{t}</span>
                  <button
                    onClick={() => handleFetchData(t)}
                    disabled={fetchingTicker === t}
                    className="load-button"
                    style={{
                      height: '32px',
                      fontSize: '0.8rem',
                      padding: '0 16px'
                    }}
                  >
                    {fetchingTicker === t ? 'Fetching...' : 'Fetch'}
                  </button>
                </div>
              ))}
            </div>

            <button
              onClick={() => setMissingTickers([])}
              style={{
                background: 'transparent',
                border: '1px solid rgba(255, 255, 255, 0.3)',
                color: 'rgba(255, 255, 255, 0.6)',
                padding: '10px',
                borderRadius: '8px',
                cursor: 'pointer',
                marginTop: '10px'
              }}
            >
              Close
            </button>
          </div>
        </div>
      )}

      {allData.length > 0 && (
        <div className="stock-list">
          {allData.map((item, index) => (
            <div key={item.ticker} className="stock-item">
              <div
                className="stock-header"
                onClick={() => toggleExpand(item.ticker)}
              >
                <div className="stock-rank">#{index + 1}</div>
                <div className="stock-info">
                  <div className="stock-ticker">
                    {item.ticker}
                    {item.chartData && item.chartData.data_points < 8 && (
                      <span
                        className="data-warning"
                        title="Using annual data instead of quarterly"
                        style={{
                          marginLeft: '8px',
                          fontSize: '1rem',
                          color: '#FFD700',
                          opacity: 0.8,
                          cursor: 'help'
                        }}
                      >
                        ⚠
                      </span>
                    )}
                  </div>
                  <div className="stock-company-name">{getCompanyName(item.ticker)}</div>
                </div>
                <div className="stock-score">Score: {item.score?.toFixed(0)}%</div>
                <div className="stock-previews">
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
                  <ValueGaugeCompact ticker={item.ticker} score={item.score} />
                </div>
                <div className="expand-indicator">
                  {expandedStock === item.ticker ? '▼' : '▶'}
                </div>
              </div>

              {expandedStock === item.ticker && (
                <div className="stock-expanded">
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
                  <div className="expanded-gauge">
                    <ValueGauge
                      ticker={item.ticker}
                      score={item.score}
                      details={item.details}
                    />
                  </div>
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


