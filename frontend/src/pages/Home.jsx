import React, { useState, useEffect, useMemo, memo, useRef } from 'react'
import ValueGauge from '../components/ValueGauge'
import ValueGaugeCompact from '../components/ValueGaugeCompact'
import PERatioChart from '../components/PERatioChart'
import SetFilterModal from '../components/SetFilterModal'
import LoadingBar from '../components/LoadingBar'
import './Home.css'
import { DEFAULT_TICKERS } from '../constants'

// Performance Optimized Component for Stock Cards
// Prevents entire list from re-rendering when unrelated state (like weights dropdown) changes
const StockCard = memo(({ item, index, expanded, onToggle, getCompanyName }) => {
  let warningTitle = '';
  const gaps = [
    ...(item.details?.data_gaps || []),
    ...(item.pegDetails?.data_gaps || []),
    ...(item.debtDetails?.data_gaps || [])
  ];
  const uniqueGaps = [...new Set(gaps)];
  
  if (uniqueGaps.length > 0) {
    warningTitle = uniqueGaps.join(' | ');
  } else if (
    (item.chartData && item.chartData.data_points < 8) ||
    (item.details && item.details.data_points < 8) ||
    (item.pegDetails && item.pegDetails.data_points < 8)
  ) {
    warningTitle = "Sparse data points for robust calculation.";
  }

  const showWarning = warningTitle !== '';

  const priceUp = item.liveChange >= 0;
  const priceColor = item.livePrice ? (priceUp ? '#22c55e' : '#ef4444') : 'rgba(255,255,255,0.4)';
  const arrow = item.livePrice ? (priceUp ? '▲' : '▼') : '';

  return (
    <div className="stock-item">
      <div className="stock-header" onClick={onToggle}>
        <div className="stock-rank">#{index + 1}</div>
        <div className="stock-info">
          <div className="stock-ticker">
            {item.ticker}
            {showWarning && (
                <span
                  className="data-warning"
                  title={warningTitle}
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
          {item.livePrice && (
            <div className="stock-live-price" style={{ marginTop: '4px', display: 'flex', alignItems: 'center', gap: '6px' }}>
              <span style={{ fontSize: '1.05rem', fontWeight: 700, color: '#fff' }}>${item.livePrice.toFixed(2)}</span>
              <span style={{ fontSize: '0.8rem', fontWeight: 600, color: priceColor, display: 'flex', alignItems: 'center', gap: '2px' }}>
                <span style={{ fontSize: '0.65rem' }}>{arrow}</span>
                {item.liveChange >= 0 ? '+' : ''}{item.liveChange?.toFixed(2)} ({item.liveChangePct >= 0 ? '+' : ''}{item.liveChangePct?.toFixed(2)}%)
              </span>
            </div>
          )}
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
          {item.pegScore !== undefined && (
            <ValueGaugeCompact ticker={item.ticker} score={item.pegScore} type="peg" />
          )}
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
          {item.pegScore !== undefined && (
            <div className="expanded-gauge">
              <ValueGauge
                ticker={item.ticker}
                score={item.pegScore}
                details={item.pegDetails}
                type="peg"
              />
            </div>
          )}
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
  const [years, setYears] = useState('2')
  const [chartYears, setChartYears] = useState('5')
  const [allData, setAllData] = useState([])
  const [loading, setLoading] = useState(false)
  const [isBackgroundLoading, setIsBackgroundLoading] = useState(false)
  const [error, setError] = useState('')
  const [expandedStock, setExpandedStock] = useState(null)
  const [showWeights, setShowWeights] = useState(false)
  const [currentPage, setCurrentPage] = useState(0)

  // Loading Progress State
  const [loadingProgress, setLoadingProgress] = useState({ current: 0, total: 0 })
  
  // Set Filter State
  const [isSetModalOpen, setIsSetModalOpen] = useState(false)
  const [selectedSets, setSelectedSets] = useState([])
  const [manualTickers, setManualTickers] = useState(DEFAULT_TICKERS)
  const [activeTickers, setActiveTickers] = useState(() => DEFAULT_TICKERS.split(',').map(t => t.trim()).filter(t => t))

  const [prevYears, setPrevYears] = useState('2')
  const [prevChartYears, setPrevChartYears] = useState('5')

  const ITEMS_PER_PAGE = 5

  // Weighting State
  const [peWeight, setPeWeight] = useState(() => Number(localStorage.getItem('peWeight')) || 70)
  const [debtWeight, setDebtWeight] = useState(() => Number(localStorage.getItem('debtWeight')) || 10)
  const [pegWeight, setPegWeight] = useState(() => Number(localStorage.getItem('pegWeight')) || 20)

  useEffect(() => {
    localStorage.setItem('peWeight', peWeight)
    localStorage.setItem('debtWeight', debtWeight)
    localStorage.setItem('pegWeight', pegWeight)
  }, [peWeight, debtWeight, pegWeight])

  // New Memoized Scoring Logic
  // Updates in real-time as sliders move without re-fetching
  const scoredData = useMemo(() => {
    return allData.map(item => {
      const peV = item.score || 0
      const debtV = item.debtScore !== undefined ? item.debtScore : 50
      const pegV = item.pegScore !== undefined ? item.pegScore : 0

      // Normalize weights
      const totalWeight = peWeight + debtWeight + pegWeight || 1
      const weightedAvg = (peV * peWeight + debtV * debtWeight + pegV * pegWeight) / totalWeight

      return { ...item, totalScore: weightedAvg }
    }).sort((a, b) => (b.totalScore || 0) - (a.totalScore || 0))
  }, [allData, peWeight, debtWeight, pegWeight])

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
  
  const currentLoadId = useRef(0)

  const loadAllData = async (tickerListToLoad) => {
    const loadId = ++currentLoadId.current;
    
    if (!tickerListToLoad || tickerListToLoad.length === 0) {
      setAllData([])
      return
    }

    const paramsChanged = (years !== prevYears || chartYears !== prevChartYears)
    
    let existingData = []
    let fetchList = tickerListToLoad

    if (!paramsChanged) {
      existingData = allData.filter(d => tickerListToLoad.includes(d.ticker))
      const existingTickers = new Set(existingData.map(d => d.ticker))
      fetchList = tickerListToLoad.filter(t => !existingTickers.has(t))
    }

    setAllData(existingData)

    if (fetchList.length === 0) return

    setPrevYears(years)
    setPrevChartYears(chartYears)

    setLoading(true)
    setIsBackgroundLoading(true)
    setError('')
    setMissingTickers([])
    setCurrentPage(0)
    try {
      const chunks = []
      for (let i = 0; i < fetchList.length; i += ITEMS_PER_PAGE) {
        chunks.push(fetchList.slice(i, i + ITEMS_PER_PAGE))
      }
      
      setLoadingProgress({ current: 0, total: chunks.length })

      const dataMap = new Map()
      const newMissing = new Set()

      // Fetch live prices for new tickers up-front (non-blocking)
      const livePriceMap = new Map()
      try {
        const livePriceRes = await fetch('/api/batch/live_price', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ tickers: fetchList })
        })
        const livePriceData = await livePriceRes.json()
        if (livePriceData.success) {
          livePriceData.results.forEach(r => {
            if (r.success) livePriceMap.set(r.ticker, r)
          })
        }
      } catch (e) {
        console.warn('Live price fetch failed:', e)
      }

      for (let i = 0; i < chunks.length; i++) {
        const chunk = chunks[i]

        const [gaugeResponse, debtResponse, pegResponse, chartResponse] = await Promise.all([
          fetch('/api/batch/value_pe_avg', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ tickers: chunk, years: parseInt(years), filename: 'DATA/EPS_manual.txt' })
          }),
          fetch('/api/batch/debt_to_equity', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ tickers: chunk, years: parseInt(years), filename: 'DATA/Balance_manual.txt' })
          }),
          fetch('/api/batch/peg_ratio', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ tickers: chunk, years: parseInt(years), filename: 'DATA/EPS_manual.txt' })
          }),
          fetch('/api/batch/pe_ratios', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ tickers: chunk, years: parseInt(chartYears), source: 'manual', include_forward: true, smoothing: 0, filename: 'DATA/EPS_manual.txt' })
          })
        ])

        const gaugeData = await gaugeResponse.json()
        const debtData = await debtResponse.json()
        const pegData = await pegResponse.json()
        const chartData = await chartResponse.json()

        if (gaugeData.success && debtData.success && pegData.success && chartData.success) {
          // 1. Base Gauges (P/E)
          gaugeData.results.forEach(item => {
            if (item.success) {
              const live = livePriceMap.get(item.ticker)
              dataMap.set(item.ticker, {
                ticker: item.ticker,
                score: item.score_100,
                details: item.details,
                gaugeData: item,
                livePrice: live?.price || null,
                liveChange: live?.change || 0,
                liveChangePct: live?.change_pct || 0
              })
            } else if (item.error_code === 'MISSING_DATA') {
              newMissing.add(item.ticker)
            }
          })

          // 2. Debt
          debtData.results.forEach(item => {
            if (item.success && dataMap.has(item.ticker)) {
              dataMap.get(item.ticker).debtScore = item.score_100
              dataMap.get(item.ticker).debtDetails = item.details
            }
          })

          // 3. PEG
          pegData.results.forEach(item => {
            if (item.success && dataMap.has(item.ticker)) {
              dataMap.get(item.ticker).pegScore = item.score_100
              dataMap.get(item.ticker).pegDetails = item.details
            }
          })

          // 4. Charts
          chartData.results.forEach(item => {
            if (item.success && dataMap.has(item.ticker)) {
              dataMap.get(item.ticker).chartData = item
            }
          })

          if (loadId !== currentLoadId.current) return;

          const chunkFinalData = Array.from(dataMap.values()).filter(item => item.score !== undefined)
          setAllData(prev => {
            // Safety measure: Ensure we only add tickers that are STILL requested in activeTickers
            // (If the activeTickers changed right after this fetch, another loadAllData is handling it, but just in case)
            const filtered = prev.filter(d => !dataMap.has(d.ticker))
            return [...filtered, ...chunkFinalData]
          })
          setMissingTickers(Array.from(newMissing))
        } else {
          setError('Failed to load segment of data')
        }
        
        setLoadingProgress(prev => ({ ...prev, current: i + 1 }))

        // Unlock the submit button loading state after first chunk so user sees data immediately
        if (i === 0 && loadId === currentLoadId.current) setLoading(false)
      }
    } catch (err) {
      if (loadId === currentLoadId.current) setError(`Error: ${err.message}`)
    } finally {
      if (loadId === currentLoadId.current) {
        setLoading(false)
        setIsBackgroundLoading(false)
      }
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
        loadAllData(activeTickers)
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
    loadAllData(activeTickers)
  }, [])

  return (
    <div className="home-page">
      <form className="controls" onSubmit={(e) => { e.preventDefault(); loadAllData(activeTickers); }}>
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
                    <span style={{ color: '#60a5fa', fontWeight: 'bold' }}>{peWeight}</span>
                  </div>
                  <input
                    type="range" min="0" max="100" value={peWeight}
                    onChange={(e) => setPeWeight(Number(e.target.value))}
                  />
                </div>

                <div style={{ display: 'flex', flexDirection: 'column', gap: '5px' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.9rem' }}>
                    <label>PEG Ratio:</label>
                    <span style={{ color: '#60a5fa', fontWeight: 'bold' }}>{pegWeight}</span>
                  </div>
                  <input
                    type="range" min="0" max="100" value={pegWeight}
                    onChange={(e) => setPegWeight(Number(e.target.value))}
                  />
                </div>

                <div style={{ display: 'flex', flexDirection: 'column', gap: '5px' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.9rem' }}>
                    <label>Debt-to-Equity:</label>
                    <span style={{ color: '#60a5fa', fontWeight: 'bold' }}>{debtWeight}</span>
                  </div>
                  <input
                    type="range" min="0" max="100" value={debtWeight}
                    onChange={(e) => setDebtWeight(Number(e.target.value))}
                  />
                </div>
              </div>
            </div>
          )}
        </div>

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
      </form >

      {error && <div className="error">{error}</div>
      }

      {
        missingTickers.length > 0 && (
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
        )
      }

      {
        scoredData.length > 0 && (
          <div className="stock-list-container">
            <div className="stock-list">
              {scoredData.slice(currentPage * ITEMS_PER_PAGE, (currentPage + 1) * ITEMS_PER_PAGE).map((item, index) => (
                <StockCard
                  key={item.ticker}
                  item={item}
                  index={(currentPage * ITEMS_PER_PAGE) + index}
                  expanded={expandedStock === item.ticker}
                  onToggle={() => toggleExpand(item.ticker)}
                  getCompanyName={getCompanyName}
                />
              ))}
            </div>
            
            {(() => {
              const totalPages = Math.max(1, Math.ceil(scoredData.length / ITEMS_PER_PAGE));
              const pages = [];
              for (let i = Math.max(0, currentPage - 2); i <= Math.min(totalPages - 1, currentPage + 2); i++) {
                pages.push(
                  <button 
                    key={i} 
                    className={`secondary-button page-num-btn ${currentPage === i ? 'active-page' : ''}`}
                    style={{ margin: '0 4px' }}
                    onClick={() => setCurrentPage(i)}
                  >
                    {i + 1}
                  </button>
                );
              }
              return (
                <div className="pagination-controls glass-card" style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', gap: '10px', marginTop: '20px', padding: '15px' }}>
                  <button className="secondary-button page-num-btn" onClick={() => setCurrentPage(0)} disabled={currentPage === 0}>|◀</button>
                  <button className="secondary-button page-num-btn" onClick={() => setCurrentPage(p => Math.max(0, p - 1))} disabled={currentPage === 0}>◀</button>
                  
                  <div style={{ display: 'flex', alignItems: 'center' }}>
                    {pages}
                  </div>

                  <button className="secondary-button page-num-btn" onClick={() => setCurrentPage(p => Math.min(totalPages - 1, p + 1))} disabled={currentPage >= totalPages - 1}>▶</button>
                  <button className="secondary-button page-num-btn" onClick={() => setCurrentPage(totalPages - 1)} disabled={currentPage >= totalPages - 1}>▶|</button>
                </div>
              );
            })()}
          </div>
        )
      }
      <SetFilterModal 
        isOpen={isSetModalOpen} 
        onClose={() => setIsSetModalOpen(false)} 
        selectedSets={selectedSets} 
        manualTickersStr={manualTickers}
        onApply={(sets, manualStr, combinedArray) => {
          setSelectedSets(sets);
          setManualTickers(manualStr);
          setActiveTickers(combinedArray);
          loadAllData(combinedArray);
        }} 
      />
      <LoadingBar 
        isLoading={isBackgroundLoading} 
        currentChunk={loadingProgress.current} 
        totalChunks={loadingProgress.total} 
      />
    </div>
  )
}

export default Home

