import React, { useState, useEffect, useRef } from 'react'
import ValueGauge from '../components/ValueGauge'
import SetFilterModal from '../components/SetFilterModal'
import LoadingBar from '../components/LoadingBar'
import './Gauges.css'
import { DEFAULT_TICKERS } from '../constants'

function Gauges() {
  const [tickers, setTickers] = useState(DEFAULT_TICKERS)
  const [years, setYears] = useState('2')
  const [gaugeData, setGaugeData] = useState([])
  const [debtData, setDebtData] = useState([])
  const [pegData, setPegData] = useState([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [activeTab, setActiveTab] = useState('pe-reversion')

  // Set Filter State
  const [isSetModalOpen, setIsSetModalOpen] = useState(false)
  const [selectedSets, setSelectedSets] = useState([])
  const [manualTickers, setManualTickers] = useState(DEFAULT_TICKERS)
  const [activeTickers, setActiveTickers] = useState(() => DEFAULT_TICKERS.split(',').map(t => t.trim()).filter(t => t))
  const [prevYears, setPrevYears] = useState('2')
  
  const currentLoadId = useRef(0)

  const handleLoadGauges = async (tickerListToLoad) => {
    const loadId = ++currentLoadId.current;
    
    if (!tickerListToLoad || tickerListToLoad.length === 0) {
      setGaugeData([])
      setDebtData([])
      setPegData([])
      return
    }

    const paramsChanged = years !== prevYears
    let prevGauges = []
    let prevDebts = []
    let prevPegs = []
    let fetchList = tickerListToLoad

    if (!paramsChanged) {
      prevGauges = gaugeData.filter(d => tickerListToLoad.includes(d.ticker))
      prevDebts = debtData.filter(d => tickerListToLoad.includes(d.ticker))
      prevPegs = pegData.filter(d => tickerListToLoad.includes(d.ticker))
      
      // Because there are multiple types, just define fetchList by what we don't have
      // base it on gaugeData primarily:
      const existingTickers = new Set(prevGauges.map(d => d.ticker))
      fetchList = tickerListToLoad.filter(t => !existingTickers.has(t))
    }

    setGaugeData(prevGauges)
    setDebtData(prevDebts)
    setPegData(prevPegs)

    if (fetchList.length === 0) return

    setPrevYears(years)

    setLoading(true)
    setError('')
    try {
      // If on DE tab, bake in the fetch
      if (activeTab === 'debt-equity') {
        setFetchingBalance(true)
        for (const ticker of fetchList) {
          try {
            await fetch(`/api/fetch_balance/${ticker}`, { method: 'POST' })
          } catch (e) {
            console.error(`Failed to fetch balance for ${ticker}`, e)
          }
        }
        setFetchingBalance(false)
      }

      const peRes = await fetch('/api/batch/value_pe_avg', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ tickers: fetchList, years: parseInt(years), filename: 'DATA/EPS_manual.txt' })
      })
      const peJson = await peRes.json()
      
      const [debtResponse, pegResponse] = await Promise.all([
        fetch('/api/batch/debt_to_equity', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ tickers: fetchList, years: parseInt(years), filename: 'DATA/Balance_manual.txt' })
        }),
        fetch('/api/batch/peg_ratio', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ tickers: fetchList, years: parseInt(years), filename: 'DATA/EPS_manual.txt' })
        })
      ])

      const debtJson = await debtResponse.json()
      const pegJson = await pegResponse.json()

      if (loadId !== currentLoadId.current) return;

      let successAny = false
      if (peJson.success) {
        const newData = peJson.results.filter(r => r.success);
        setGaugeData(prev => [...prev.filter(d => !newData.find(n => n.ticker === d.ticker)), ...newData].sort((a, b) => (b.score_100 || 0) - (a.score_100 || 0)))
        successAny = true
      }
      
      if (debtJson.success) {
        const newData = debtJson.results.filter(r => r.success);
        setDebtData(prev => [...prev.filter(d => !newData.find(n => n.ticker === d.ticker)), ...newData].sort((a, b) => (b.score_100 || 0) - (a.score_100 || 0)))
        successAny = true
      }
      if (pegJson.success) {
        const newData = pegJson.results.filter(r => r.success);
        setPegData(prev => [...prev.filter(d => !newData.find(n => n.ticker === d.ticker)), ...newData].sort((a, b) => (b.score_100 || 0) - (a.score_100 || 0)))
        successAny = true
      }

      if (!successAny) {
        setError('Failed to load gauge data')
      }
    } catch (err) {
      if (loadId === currentLoadId.current) setError(`Error: ${err.message}`)
    } finally {
      if (loadId === currentLoadId.current) setLoading(false)
    }
  }

  const [fetchingBalance, setFetchingBalance] = useState(false)

  const handleFetchBalance = async () => {
    setFetchingBalance(true)
    const tickerList = activeTickers;
    
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
    handleLoadGauges(activeTickers) // Reload after fetching
    setFetchingBalance(false)
  }

  useEffect(() => {
    handleLoadGauges(activeTickers)
  }, [])

  return (
    <div className="gauges-page">
      <form className="controls" onSubmit={(e) => { e.preventDefault(); handleLoadGauges(activeTickers); }}>
        <label>
          <button 
            type="button" 
            className="secondary-button" 
            onClick={() => setIsSetModalOpen(true)}
            title="Choose Sets & Add-ons"
          >
            Choose Stocks {selectedSets.length > 0 ? `(${selectedSets.length})` : ''}
          </button>
        </label>
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
        <button
          className={`sub-tab ${activeTab === 'peg-ratio' ? 'active' : ''}`}
          onClick={() => setActiveTab('peg-ratio')}
        >
          PEG Ratio Valuation
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

      {activeTab === 'peg-ratio' && (
        <section className="section">
          <h2 className="section-title">PEG Ratio Valuation</h2>
          <div className="gauge-container">
            {pegData.map((item) => (
              <div key={item.ticker} className="glass-card">
                <div style={{ position: 'relative' }}>
                  {item.details && item.details.data_points < 8 && (
                    <span
                      className="data-warning"
                      title="Using annual data instead of quarterly or not enough data"
                      style={{
                        position: 'absolute',
                        top: '10px',
                        right: '10px',
                        fontSize: '1.2rem',
                        color: '#d63384',
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
                    type="peg"
                  />
                </div>
              </div>
            ))}
          </div>
        </section>
      )}
      
      <SetFilterModal 
        isOpen={isSetModalOpen} 
        onClose={() => setIsSetModalOpen(false)} 
        selectedSets={selectedSets} 
        manualTickersStr={manualTickers}
        onApply={(sets, manualStr, combinedArray) => {
          setSelectedSets(sets);
          setManualTickers(manualStr);
          setActiveTickers(combinedArray);
          handleLoadGauges(combinedArray);
        }} 
      />
      <LoadingBar isLoading={loading || fetchingBalance} />
    </div>
  )
}

export default Gauges



