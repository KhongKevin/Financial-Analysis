import React, { useState, useEffect, useRef } from 'react'
import PERatioChart from '../components/PERatioChart'
import SetFilterModal from '../components/SetFilterModal'
import LoadingBar from '../components/LoadingBar'
import { DEFAULT_TICKERS } from '../constants'

function Charts() {
  const [chartYears, setChartYears] = useState('5')
  const [chartData, setChartData] = useState([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  // Set Filter State
  const [isSetModalOpen, setIsSetModalOpen] = useState(false)
  const [selectedSets, setSelectedSets] = useState([])
  const [manualTickers, setManualTickers] = useState(DEFAULT_TICKERS)
  const [activeTickers, setActiveTickers] = useState(() => DEFAULT_TICKERS.split(',').map(t => t.trim()).filter(t => t))
  const [prevChartYears, setPrevChartYears] = useState('5')
  
  const currentLoadId = useRef(0)

  const handleLoadCharts = async (tickerListToLoad) => {
    const loadId = ++currentLoadId.current;
    
    if (!tickerListToLoad || tickerListToLoad.length === 0) {
      setChartData([])
      return
    }

    const yearsChanged = prevChartYears !== chartYears
    let existingData = []
    let fetchList = tickerListToLoad

    if (!yearsChanged) {
      existingData = chartData.filter(d => tickerListToLoad.includes(d.ticker))
      const existingTickers = new Set(existingData.map(d => d.ticker))
      fetchList = tickerListToLoad.filter(t => !existingTickers.has(t))
    }

    setChartData(existingData)

    if (fetchList.length === 0) return

    setPrevChartYears(chartYears)

    setLoading(true)
    setError('')
    try {
      const response = await fetch('/api/batch/pe_ratios', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          tickers: fetchList,
          years: parseInt(chartYears),
          source: 'manual',
          include_forward: true,
          smoothing: 0,
          filename: 'DATA/EPS_manual.txt'
        })
      })

      const data = await response.json()
      
      if (loadId !== currentLoadId.current) return;

      if (data.success) {
        const newData = data.results.filter(r => r.success);
        setChartData(prev => {
          const filtered = prev.filter(d => !newData.find(n => n.ticker === d.ticker));
          return [...filtered, ...newData];
        })
      } else {
        setError('Failed to load chart data')
      }
    } catch (err) {
      if (loadId === currentLoadId.current) setError(`Error: ${err.message}`)
    } finally {
      if (loadId === currentLoadId.current) setLoading(false)
    }
  }

  useEffect(() => {
    handleLoadCharts(activeTickers)
  }, [])

  return (
    <div className="charts-page">
      <form className="controls" onSubmit={(e) => { e.preventDefault(); handleLoadCharts(activeTickers); }}>
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
      
      <SetFilterModal 
        isOpen={isSetModalOpen} 
        onClose={() => setIsSetModalOpen(false)} 
        selectedSets={selectedSets} 
        manualTickersStr={manualTickers}
        onApply={(sets, manualStr, combinedArray) => {
          setSelectedSets(sets);
          setManualTickers(manualStr);
          setActiveTickers(combinedArray);
          handleLoadCharts(combinedArray);
        }} 
      />
      <LoadingBar isLoading={loading} />
    </div>
  )
}

export default Charts



