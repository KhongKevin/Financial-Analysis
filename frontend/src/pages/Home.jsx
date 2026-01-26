import React, { useState, useEffect, useMemo, memo } from 'react'
import ValueGauge from '../components/ValueGauge'
import ValueGaugeCompact from '../components/ValueGaugeCompact'
import PERatioChart from '../components/PERatioChart'
import './Home.css'

// Performance Optimized Component for Stock Cards
// Prevents entire list from re-rendering when unrelated state (like weights dropdown) changes
const StockCard = memo(({ item, index, expanded, onToggle, getCompanyName }) => {
  return (
    <div className="stock-item">
      <div className="stock-header" onClick={onToggle}>
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
        <div className="stock-score">Total Score: {item.totalScore?.toFixed(0)}%</div>
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
          <ValueGaugeCompact ticker={item.ticker} score={item.score} type="pe" />
          {item.debtScore !== undefined && (
            <ValueGaugeCompact ticker={item.ticker} score={item.debtScore} type="de" />
          )}
        </div>
        <div className="expand-indicator">
          {expanded ? '▼' : '▶'}
        </div>
      </div>

      {expanded && (
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
              type="pe"
            />
          </div>
          {item.debtScore !== undefined && (
            <div className="expanded-gauge">
              <ValueGauge
                ticker={item.ticker}
                score={item.debtScore}
                details={item.debtDetails}
                type="debt"
              />
            </div>
          )}
        </div>
      )}
    </div>
  )
})

function Home() {
  const [tickers, setTickers] = useState('NFLX,AMD,GOOG,NVDA,INTC,AMZN')
  const [years, setYears] = useState('2')
  const [chartYears, setChartYears] = useState('5')
  const [allData, setAllData] = useState([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [expandedStock, setExpandedStock] = useState(null)
  const [showWeights, setShowWeights] = useState(false)

  // Weighting State
  const [peWeight, setPeWeight] = useState(() => {
    return Number(localStorage.getItem('peWeight')) || 90
  })
  const [debtWeight, setDebtWeight] = useState(() => {
    return Number(localStorage.getItem('debtWeight')) || 10
  })

  useEffect(() => {
    localStorage.setItem('peWeight', peWeight)
    localStorage.setItem('debtWeight', debtWeight)
  }, [peWeight, debtWeight])

  // New Memoized Scoring Logic
  // Updates in real-time as sliders move without re-fetching
  const scoredData = useMemo(() => {
    return allData.map(item => {
      const peV = item.score || 0
      const debtV = item.debtScore !== undefined ? item.debtScore : 50

      const weightedAvg = (peV * peWeight / 100) + (debtV * debtWeight / 100)
      const numFactors = 2
      const totalScore = weightedAvg / numFactors

      return { ...item, totalScore }
    }).sort((a, b) => (b.totalScore || 0) - (a.totalScore || 0))
  }, [allData, peWeight, debtWeight])

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

  const [missingTickers, setMissingTickers] = useState([])
  const [fetchingTicker, setFetchingTicker] = useState(null)

  const loadAllData = async () => {
    setLoading(true)
    setError('')
    setMissingTickers([])
    try {
      const tickerList = tickers.split(',').map(t => t.trim()).filter(t => t)

      const [gaugeResponse, debtResponse, chartResponse] = await Promise.all([
        fetch('/api/batch/value_pe_avg', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ tickers: tickerList, years: parseInt(years), filename: 'EPS_manual.txt' })
        }),
        fetch('/api/batch/debt_to_equity', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ tickers: tickerList, filename: 'Balance_manual.txt' })
        }),
        fetch('/api/batch/pe_ratios', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ tickers: tickerList, years: parseInt(chartYears), source: 'manual', include_forward: true, smoothing: 0, filename: 'EPS_manual.txt' })
        })
      ])

      const gaugeData = await gaugeResponse.json()
      const debtData = await debtResponse.json()
      const chartData = await chartResponse.json()

      const newMissing = new Set()

      if (gaugeData.success && debtData.success && chartData.success) {
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

        debtData.results.forEach(item => {
          if (item.success) {
            const existing = dataMap.get(item.ticker) || { ticker: item.ticker }
            existing.debtScore = item.score_100
            existing.debtDetails = item.details
            dataMap.set(item.ticker, existing)
          }
        })

        chartData.results.forEach(item => {
          if (item.success) {
            const existing = dataMap.get(item.ticker) || { ticker: item.ticker }
            existing.chartData = item
            dataMap.set(item.ticker, existing)
          }
        })

        const finalData = Array.from(dataMap.values()).filter(item => item.score !== undefined)
        setAllData(finalData)
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
      const [epsRes, balRes] = await Promise.all([
        fetch(`/api/fetch_eps/${ticker}`, { method: 'POST' }),
        fetch(`/api/fetch_balance/${ticker}`, { method: 'POST' })
      ])

      const epsData = await epsRes.json()
      const balData = await balRes.json()

      if (epsData.success && balData.success) {
        let message = `Data fetched for ${ticker} (EPS & Balance Sheet).`
        if (epsData.warning) message += `\n\n⚠️ EPS: ${epsData.warning}`
        alert(message)
        loadAllData()
      } else {
        alert(`Failed to fetch: ${epsData.error || balData.error}`)
      }
    } catch (err) {
      alert(`Error: ${err.message}`)
    } finally {
      setFetchingTicker(null)
    }
  }

  const toggleExpand = (ticker) => {
    setExpandedStock(expandedStock === ticker ? null : ticker)
  }

  useEffect(() => {
    loadAllData()
  }, [])

  return (
    <div className="home-page">
      <form className="controls" onSubmit={(e) => { e.preventDefault(); loadAllData(); }}>
        <div style={{ position: 'relative' }}>
          <button
            type="button"
            className="secondary-button"
            onClick={() => setShowWeights(!showWeights)}
            title="Adjust Weighting"
          >
            ⚖️ Weights {showWeights ? '▼' : '▶'}
          </button>

          {showWeights && (
            <div className="weight-dropdown glass-card">
              <h3 style={{ margin: '0 0 15px 0', fontSize: '1rem', color: '#fff' }}>Score Weights</h3>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '5px' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.9rem' }}>
                    <label>Relative PE:</label>
                    <span style={{ color: '#60a5fa', fontWeight: 'bold' }}>{peWeight}%</span>
                  </div>
                  <input
                    type="range" min="0" max="100" value={peWeight}
                    onChange={(e) => {
                      const val = Number(e.target.value)
                      setPeWeight(val)
                      setDebtWeight(100 - val)
                    }}
                  />
                </div>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '5px' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.9rem' }}>
                    <label>Debt-to-Equity:</label>
                    <span style={{ color: '#60a5fa', fontWeight: 'bold' }}>{debtWeight}%</span>
                  </div>
                  <input
                    type="range" min="0" max="100" value={debtWeight}
                    onChange={(e) => {
                      const val = Number(e.target.value)
                      setDebtWeight(val)
                      setPeWeight(100 - val)
                    }}
                  />
                </div>
              </div>
            </div>
          )}
        </div>

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
        <button type="submit" className="load-button" disabled={loading}>
          {loading ? 'Loading...' : 'Load Data'}
        </button>
      </form>

      {error && <div className="error">{error}</div>}

      {missingTickers.length > 0 && (
        <div style={{
          position: 'fixed', top: 0, left: 0, right: 0, bottom: 0,
          backgroundColor: 'rgba(0, 0, 0, 0.7)', backdropFilter: 'blur(5px)',
          display: 'flex', justifyContent: 'center', alignItems: 'center', zIndex: 2000
        }}>
          <div className="glass-card" style={{
            width: '400px', padding: '2rem', display: 'flex', flexDirection: 'column',
            gap: '1.5rem', boxShadow: '0 8px 32px rgba(0, 0, 0, 0.5)'
          }}>
            <h2 style={{ margin: 0, color: '#fff', fontSize: '1.5rem' }}>Missing Data Found</h2>
            <p style={{ color: 'rgba(255, 255, 255, 0.8)', margin: 0 }}>
              The following tickers are missing data. Fetch them?
            </p>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
              {missingTickers.map(t => (
                <div key={t} style={{
                  display: 'flex', alignItems: 'center', justifyContent: 'space-between',
                  background: 'rgba(255, 255, 255, 0.05)', padding: '10px', borderRadius: '8px'
                }}>
                  <span style={{ fontWeight: '700', fontSize: '1.1rem' }}>{t}</span>
                  <button onClick={() => handleFetchData(t)} disabled={fetchingTicker === t} className="load-button" style={{ height: '32px', fontSize: '0.8rem', padding: '0 16px' }}>
                    {fetchingTicker === t ? 'Fetching...' : 'Fetch'}
                  </button>
                </div>
              ))}
            </div>
            <button onClick={() => setMissingTickers([])} style={{ background: 'transparent', border: '1px solid rgba(255, 255, 255, 0.3)', color: 'rgba(255, 255, 255, 0.6)', padding: '10px', borderRadius: '8px', cursor: 'pointer', marginTop: '10px' }}>
              Close
            </button>
          </div>
        </div>
      )}

      {scoredData.length > 0 && (
        <div className="stock-list">
          {scoredData.map((item, index) => (
            <StockCard
              key={item.ticker}
              item={item}
              index={index}
              expanded={expandedStock === item.ticker}
              onToggle={() => toggleExpand(item.ticker)}
              getCompanyName={getCompanyName}
            />
          ))}
        </div>
      )}
    </div>
  )
}

export default Home
