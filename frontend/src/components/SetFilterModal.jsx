import React, { useState, useEffect } from 'react';
import './SetFilterModal.css';

// Reuse the helper to get userId
const getUserId = () => {
  let uid = localStorage.getItem('userId');
  if (!uid) {
    uid = 'user_' + Math.random().toString(36).substr(2, 9);
    localStorage.setItem('userId', uid);
  }
  return uid;
};

function SetFilterModal({ isOpen, onClose, selectedSets, manualTickersStr, onApply }) {
  const [sets, setSets] = useState({});
  const [localSelected, setLocalSelected] = useState(new Set());
  const [localManualTickers, setLocalManualTickers] = useState('');
  const [searchQuery, setSearchQuery] = useState('');
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (isOpen) {
      setLocalSelected(new Set(selectedSets));
      setLocalManualTickers(manualTickersStr);
      fetchSets();
    }
  }, [isOpen, selectedSets, manualTickersStr]);

  const fetchSets = async () => {
    if (Object.keys(sets).length === 0) {
      setLoading(true);
    }
    const userId = getUserId();
    try {
      const res = await fetch(`/api/sets?userId=${userId}`);
      const data = await res.json();
      if (data.success) {
        setSets(data.sets || {});
      }
    } catch (err) {
      console.error('Failed to fetch sets', err);
    } finally {
      setLoading(false);
    }
  };

  const toggleSet = (setName) => {
    setLocalSelected(prev => {
      const newSet = new Set(prev);
      if (newSet.has(setName)) {
        newSet.delete(setName);
      } else {
        newSet.add(setName);
      }
      return newSet;
    });
  };

  const handleApply = () => {
    // Determine the total set of tickers from active sets
    const combinedTickers = new Set();
    
    // Add manual add-on tickers
    const manualList = localManualTickers.split(',').map(t => t.trim().toUpperCase()).filter(t => t);
    manualList.forEach(t => combinedTickers.add(t));

    // Add sets tickers
    localSelected.forEach(setName => {
      const sTickers = sets[setName] || [];
      sTickers.forEach(t => combinedTickers.add(t));
    });
    
    onApply(Array.from(localSelected), localManualTickers, Array.from(combinedTickers));
    onClose();
  };

  if (!isOpen) return null;

  const setNames = Object.keys(sets);
  const filteredSets = setNames.filter(s => s.toLowerCase().includes(searchQuery.toLowerCase()));

  return (
    <div className="set-modal-overlay">
      <div className="set-modal-content glass-card">
        <div className="set-modal-header">
          <h3>Sets & Add-on Filters</h3>
          <button className="close-btn" onClick={onClose}>&times;</button>
        </div>

        <div className="set-section" style={{ flex: 1, display: 'flex', flexDirection: 'column' }}>
          <h4>Select Stock Sets</h4>
          <input 
            type="text" 
            placeholder="Search sets..." 
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="set-search-input"
          />

          <div className="set-tags-container">
            {loading && Object.keys(sets).length === 0 ? (
              <p className="loading-text">Loading...</p>
            ) : filteredSets.length > 0 ? (
              filteredSets.map(setName => (
                <div 
                  key={setName} 
                  className={`set-filter-tag ${localSelected.has(setName) ? 'selected' : ''}`}
                  onClick={() => toggleSet(setName)}
                >
                  <span>{setName}</span>
                  <span className="count-badge">{(sets[setName] || []).length}</span>
                </div>
              ))
            ) : (
              <p className="no-sets-text">
                {setNames.length === 0 ? "No sets created yet. Go to More > Sets to create some!" : "No sets match your search."}
              </p>
            )}
          </div>
        </div>

        <div className="set-section" style={{ marginTop: '1rem' }}>
          <h4>Add-On Tickers</h4>
          <div style={{ display: 'flex', alignItems: 'center' }}>
            <input 
              type="text" 
              placeholder="e.g. AAPL, NVDA" 
              value={localManualTickers}
              onChange={(e) => setLocalManualTickers(e.target.value)}
              className="manual-ticker-input"
              style={{ flex: 1, margin: 0, height: '44px', boxSizing: 'border-box' }}
            />
            <button 
              type="button" 
              onClick={() => setLocalManualTickers('')} 
              style={{ marginLeft: '5px', borderRadius: '6px', height: '44px', padding: '0 1rem', backgroundColor: '#4b5563', color: 'white', border: 'none', cursor: 'pointer', fontWeight: 'bold', boxSizing: 'border-box' }}
              title="Clear manual tickers"
            >
              Clear
            </button>
          </div>
          <p className="helper-text" style={{ marginTop: '0.5rem' }}>These stocks will be temporarily added to your view.</p>
        </div>

        <div className="set-modal-footer">
          <button 
            style={{ backgroundColor: '#6b7280', borderRadius: '6px', padding: '0.6rem 1.2rem', color: 'white', border: 'none', cursor: 'pointer', fontWeight: 'bold' }} 
            onClick={onClose}
          >
            Cancel
          </button>
          <button 
            style={{ backgroundColor: '#3b82f6', borderRadius: '6px', padding: '0.6rem 1.2rem', color: 'white', border: 'none', cursor: 'pointer', fontWeight: 'bold' }} 
            onClick={handleApply}
          >
            Apply Filters
          </button>
        </div>
      </div>
    </div>
  );
}

export default SetFilterModal;
