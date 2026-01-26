import React, { useState, useEffect } from 'react'
import ValueGauge from '../components/ValueGauge'
import './Gauges.css'

function Gauges() {
  const [tickers, setTickers] = useState('NFLX,AMD,GOOG,NVDA,INTC,AMZN')
  const [years, setYears] = useState('2')
  const [gaugeData, setGaugeData] = useState([])
  const [debtData, setDebtData] = useState([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [activeTab, setActiveTab] = useState('pe-reversion')

  const handleLoadGauges = async () => {
    setLoading(true)
    setError('')
    try {
      const tickerList = tickers.split(',').map(t => t.trim()).filter(t => t)

      // If on DE tab, bake in the fetch
      if (activeTab === 'debt-equity') {
        setFetchingBalance(true)
        for (const ticker of tickerList) {
          try {
            await fetch(`/api/fetch_balance/${ticker}`, { method: 'POST' })
          } catch (e) {
            console.error(`Failed to fetch balance for ${ticker}`, e)
          }
        }
        setFetchingBalance(false)
      }

      const [peRes, debtRes] = await Promise.all([
        fetch('/api/batch/value_pe_avg', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ tickers: tickerList, years: parseInt(years), filename: 'EPS_manual.txt' })
        }),
        fetch('/api/batch/debt_to_equity', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ tickers: tickerList, filename: 'Balance_manual.txt' })
        })
      ])

      const peJson = await peRes.json()
      const debtJson = await debtRes.json()

      if (peJson.success) {
        setGaugeData(peJson.results.filter(r => r.success).sort((a, b) => (b.score_100 || 0) - (a.score_100 || 0)))
      }
      if (debtJson.success) {
        setDebtData(debtJson.results.filter(r => r.success).sort((a, b) => (b.score_100 || 0) - (a.score_100 || 0)))
      }

      if (!peJson.success && !debtJson.success) {
        setError('Failed to load gauge data')
      }
    } catch (err) {
      setError(`Error: ${err.message}`)
    } finally {
      setLoading(false)
    }
  }

  const [fetchingBalance, setFetchingBalance] = useState(false)

  const handleFetchBalance = async () => {
    setFetchingBalance(true)
    const tickerList = tickers.split(',').map(t => t.trim()).filter(t => t)
    let successCount = 0
    let failCount = 0

    for (const ticker of tickerList) {
      try {
        const res = await fetch(`/api/fetch_balance/${ticker}`, { method: 'POST' })
        const data = await res.json()
        if (data.success) {
          successCount++
        } else {
          failCount++
        }
      } catch (err) {
        failCount++
      }
    }

    alert(`Balance Sheet Fetch Results:\nSuccess: ${successCount}\nFailed: ${failCount}`)
    handleLoadGauges() // Reload after fetching
    setFetchingBalance(false)
  }

  useEffect(() => {
    handleLoadGauges()
  }, [])

  return (
    <div className="gauges-page">
      <form className="controls" onSubmit={(e) => { e.preventDefault(); handleLoadGauges(); }}>
        <input
          type="text"
          placeholder="Tickers (comma-separated)"
          value={tickers}
          onChange={(e) => setTickers(e.target.value)}
        />
        <label>
          Years (History):
          <input
            type="number"
            value={years}
            onChange={(e) => setYears(e.target.value)}
            min="1"
            max="10"
            style={{ width: '60px', marginLeft: '5px' }}
          />
        </label>
        <button type="submit" className="load-button" disabled={loading || fetchingBalance}>
          {loading || fetchingBalance ? 'Processing...' : 'Load Gauges'}
        </button>
      </form>

      <div className="sub-tabs">
        <button
          className={`sub-tab ${activeTab === 'pe-reversion' ? 'active' : ''}`}
          onClick={() => setActiveTab('pe-reversion')}
        >
          P/E Average Reversion Score
        </button>
        <button
          className={`sub-tab ${activeTab === 'debt-equity' ? 'active' : ''}`}
          onClick={() => setActiveTab('debt-equity')}
        >
          Debt-to-Equity Valuation
        </button>
      </div>

      {error && <div className="error">{error}</div>}

      {loading && <div className="loading">Loading...</div>}

      {activeTab === 'pe-reversion' && gaugeData.length > 0 && (
        <section className="section">
          <h2 className="section-title">P/E Average Reversion Score</h2>
          <div className="gauge-container">
            {gaugeData.map((item) => (
              <div key={item.ticker} className="glass-card">
                <div style={{ position: 'relative' }}>
                  {item.details && item.details.data_points < 8 && (
                    <span
                      className="data-warning"
                      title="Using annual data instead of quarterly"
                      style={{
                        position: 'absolute',
                        top: '10px',
                        right: '10px',
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
                  <ValueGauge
                    ticker={item.ticker}
                    score={item.score_100}
                    details={item.details}
                  />
                </div>
              </div>
            ))}
          </div>
        </section>
      )}

      {activeTab === 'debt-equity' && (
        <section className="section">
          <h2 className="section-title" style={{ margin: 0, marginBottom: '20px' }}>Debt-to-Equity Valuation</h2>
          {debtData.length > 0 ? (
            <div className="gauge-container">
              {debtData.map((item) => (
                <div key={item.ticker} className="glass-card">
                  <ValueGauge
                    ticker={item.ticker}
                    score={item.score_100}
                    details={item.details}
                    type="debt"
                  />
                </div>
              ))}
            </div>
          ) : !loading && (
            <div className="loading" style={{ marginTop: '50px' }}>
              No Debt-to-Equity data found for these tickers.
              Click "Fetch Balance Sheets" to retrieve data from StockAnalysis.
            </div>
          )}
        </section>
      )}
    </div>
  )
}

export default Gauges


