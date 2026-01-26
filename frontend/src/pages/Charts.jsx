import React, { useState, useEffect } from 'react'
import PERatioChart from '../components/PERatioChart'
import './Charts.css'

function Charts() {
  const [tickers, setTickers] = useState('NFLX,AMD,GOOG,NVDA,INTC,AMZN')
  const [chartYears, setChartYears] = useState('5')
  const [chartData, setChartData] = useState([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const handleLoadCharts = async () => {
    setLoading(true)
    setError('')
    try {
      const tickerList = tickers.split(',').map(t => t.trim()).filter(t => t)
      const response = await fetch('/api/batch/pe_ratios', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          tickers: tickerList,
          years: parseInt(chartYears),
          source: 'manual',
          include_forward: true,
          smoothing: 0,
          filename: 'EPS_manual.txt'
        })
      })

      const data = await response.json()
      if (data.success) {
        setChartData(data.results.filter(r => r.success))
      } else {
        setError('Failed to load chart data')
      }
    } catch (err) {
      setError(`Error: ${err.message}`)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    handleLoadCharts()
  }, [])

  return (
    <div className="charts-page">
      <form className="controls" onSubmit={(e) => { e.preventDefault(); handleLoadCharts(); }}>
        <input
          type="text"
          placeholder="Tickers (comma-separated)"
          value={tickers}
          onChange={(e) => setTickers(e.target.value)}
        />
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
          {loading ? 'Loading...' : 'Load Charts'}
        </button>
      </form>

      {error && <div className="error">{error}</div>}

      {loading && <div className="loading">Loading...</div>}

      {chartData.length > 0 && (
        <section className="section">
          <h2 className="section-title">P/E Ratios Over Time</h2>
          {chartData.map((item) => (
            <div key={item.ticker} className="glass-card" style={{ position: 'relative' }}>
              {item.data_points < 8 && (
                <span
                  className="data-warning"
                  title="Using annual data instead of quarterly"
                  style={{
                    position: 'absolute',
                    top: '15px',
                    right: '15px',
                    fontSize: '1.2rem',
                    color: '#FFD700',
                    opacity: 0.8,
                    cursor: 'help',
                    zIndex: 10
                  }}
                >
                  ⚠
                </span>
              )}
              <PERatioChart
                ticker={item.ticker}
                peTtm={item.pe_ttm}
                peForward={item.pe_forward}
                price={item.price}
              />
            </div>
          ))}
        </section>
      )}
    </div>
  )
}

export default Charts


