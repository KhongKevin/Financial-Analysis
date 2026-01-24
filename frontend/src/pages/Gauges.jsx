import React, { useState, useEffect } from 'react'
import ValueGauge from '../components/ValueGauge'
import './Gauges.css'

function Gauges() {
  const [tickers, setTickers] = useState('NFLX,AMD,GOOG,NVDA,INTC,AMZN')
  const [years, setYears] = useState('2')
  const [gaugeData, setGaugeData] = useState([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const handleLoadGauges = async () => {
    setLoading(true)
    setError('')
    try {
      const tickerList = tickers.split(',').map(t => t.trim()).filter(t => t)
      const response = await fetch('/api/batch/value_pe_avg', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          tickers: tickerList,
          years: parseInt(years),
          filename: 'EPS_manual.txt'
        })
      })

      const data = await response.json()
      if (data.success) {
        // Sort by score (highest first)
        const sorted = data.results
          .filter(r => r.success)
          .sort((a, b) => (b.score_100 || 0) - (a.score_100 || 0))
        setGaugeData(sorted)
      } else {
        setError('Failed to load gauge data')
      }
    } catch (err) {
      setError(`Error: ${err.message}`)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    handleLoadGauges()
  }, [])

  return (
    <div className="gauges-page">
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
        <button onClick={handleLoadGauges} disabled={loading}>
          {loading ? 'Loading...' : 'Load Gauges'}
        </button>
      </div>

      {error && <div className="error">{error}</div>}

      {loading && <div className="loading">Loading...</div>}

      {gaugeData.length > 0 && (
        <section className="section">
          <h2 className="section-title">Valuation Scores (P/E Avg)</h2>
          <div className="gauge-container">
            {gaugeData.map((item) => (
              <ValueGauge
                key={item.ticker}
                ticker={item.ticker}
                score={item.score_100}
                details={item.details}
              />
            ))}
          </div>
        </section>
      )}
    </div>
  )
}

export default Gauges


