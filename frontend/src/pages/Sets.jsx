import React, { useState, useEffect } from 'react';
import './Sets.css';

// Helper to get or create a userId
const getUserId = () => {
  let uid = localStorage.getItem('userId');
  if (!uid) {
    uid = 'user_' + Math.random().toString(36).substr(2, 9);
    localStorage.setItem('userId', uid);
  }
  return uid;
};

function Sets() {
  const [sets, setSets] = useState({});
  const [newSetName, setNewSetName] = useState('');
  const [selectedSet, setSelectedSet] = useState(null);
  const [newTicker, setNewTicker] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  
  const userId = getUserId();

  const fetchSets = async () => {
    setLoading(true);
    try {
      const res = await fetch(`/api/sets?userId=${userId}`);
      const data = await res.json();
      if (data.success) {
        setSets(data.sets);
        if (selectedSet && !data.sets[selectedSet]) {
            setSelectedSet(null);
        }
      } else {
        setError(data.error);
      }
    } catch (err) {
      setError('Failed to fetch sets');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchSets();
  }, []);

  const handleCreateSet = async (e) => {
    e.preventDefault();
    if (!newSetName.trim()) return;
    
    if (sets[newSetName]) {
        setError("Set already exists");
        return;
    }

    try {
      const res = await fetch('/api/sets', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          userId,
          setName: newSetName.trim(),
          tickers: []
        })
      });
      const data = await res.json();
      if (data.success) {
        setSets(data.sets);
        setNewSetName('');
        setSelectedSet(newSetName.trim());
      }
    } catch (err) {
      setError('Failed to create set');
    }
  };

  const handleAddTicker = async (e) => {
    e.preventDefault();
    if (!selectedSet || !newTicker.trim()) return;
    
    const ticker = newTicker.trim().toUpperCase();
    const currentTickers = sets[selectedSet] || [];
    
    if (currentTickers.includes(ticker)) {
        setNewTicker('');
        return; // Already added
    }

    const updatedTickers = [...currentTickers, ticker];

    try {
      const res = await fetch('/api/sets', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          userId,
          setName: selectedSet,
          tickers: updatedTickers
        })
      });
      const data = await res.json();
      if (data.success) {
        setSets(data.sets);
        setNewTicker('');
      }
    } catch (err) {
      setError('Failed to add ticker');
    }
  };

  const handleRemoveTicker = async (tickerToRemove) => {
    if (!selectedSet) return;
    const updatedTickers = sets[selectedSet].filter(t => t !== tickerToRemove);
    
    try {
      const res = await fetch('/api/sets', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          userId,
          setName: selectedSet,
          tickers: updatedTickers
        })
      });
      const data = await res.json();
      if (data.success) {
        setSets(data.sets);
      }
    } catch (err) {
      setError('Failed to remove ticker');
    }
  };

  const handleDeleteSet = async (setName) => {
    if (!window.confirm(`Are you sure you want to delete ${setName}?`)) return;
    
    try {
      const res = await fetch(`/api/sets/${setName}?userId=${userId}`, {
        method: 'DELETE'
      });
      const data = await res.json();
      if (data.success) {
        setSets(data.sets);
        if (selectedSet === setName) {
            setSelectedSet(null);
        }
      }
    } catch (err) {
      setError('Failed to delete set');
    }
  };

  return (
    <div className="sets-page">
      <div className="sets-container glass-card">
        <h2>Manage Stock Sets</h2>
        {error && <div className="error">{error}</div>}
        
        <div className="sets-layout">
          <div className="sets-sidebar">
            <h3>Your Sets</h3>
            <form onSubmit={handleCreateSet} className="create-set-form">
              <input 
                type="text" 
                placeholder="New Set Name" 
                value={newSetName}
                onChange={(e) => setNewSetName(e.target.value)}
              />
              <button style={{ backgroundColor: '#3b82f6', borderRadius: '6px', color: 'white', border: 'none', cursor: 'pointer', padding: '0.5rem 1rem', fontWeight: 'bold' }} type="submit">+</button>
            </form>
            
            {loading && <p>Loading sets...</p>}
            
            <ul className="set-list">
              {Object.keys(sets).map(s => (
                <li 
                    key={s} 
                    className={`set-list-item ${selectedSet === s ? 'active' : ''}`}
                    onClick={() => setSelectedSet(s)}
                >
                  <span className="set-name">{s}</span>
                  <button 
                    className="delete-set-btn"
                    onClick={(e) => { e.stopPropagation(); handleDeleteSet(s); }}
                    title="Delete Set"
                  >
                    ×
                  </button>
                </li>
              ))}
              {Object.keys(sets).length === 0 && !loading && (
                  <p className="no-sets">No sets created yet.</p>
              )}
            </ul>
          </div>
          
          <div className="sets-content">
            {selectedSet ? (
              <div className="set-details">
                <h3>{selectedSet}</h3>
                
                <form onSubmit={handleAddTicker} className="add-ticker-form">
                  <input 
                    type="text" 
                    placeholder="Add Ticker (e.g. AAPL)" 
                    value={newTicker}
                    onChange={(e) => setNewTicker(e.target.value)}
                  />
                  <button style={{ backgroundColor: '#3b82f6', borderRadius: '6px', color: 'white', border: 'none', cursor: 'pointer', padding: '0.5rem 1rem', fontWeight: 'bold' }} type="submit">Add Stock</button>
                </form>
                
                <div className="ticker-tags">
                  {(sets[selectedSet] || []).map(ticker => (
                    <div key={ticker} className="ticker-tag">
                      {ticker}
                      <button onClick={() => handleRemoveTicker(ticker)}>×</button>
                    </div>
                  ))}
                  {(sets[selectedSet] || []).length === 0 && (
                      <p className="no-tickers">No stocks in this set.</p>
                  )}
                </div>
              </div>
            ) : (
              <div className="no-selection">
                <p>Select a set from the left to manage its stocks.</p>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

export default Sets;
