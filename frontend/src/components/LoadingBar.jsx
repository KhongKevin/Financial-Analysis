import React, { useState, useEffect } from 'react';
import './LoadingBar.css';

function LoadingBar({ isLoading, totalChunks = 0, currentChunk = 0 }) {
  const [hidden, setHidden] = useState(false);

  // Reset hidden state whenever it starts loading again
  useEffect(() => {
    if (isLoading) {
      setHidden(false);
    }
  }, [isLoading]);

  if (!isLoading || hidden) return null;

  return (
    <div className="floating-loading-bar-container">
      <div className="floating-loading-bar glass-card">
        <div className="loading-content">
          <div className="loading-spinner"></div>
          <span className="loading-message">Loading data...</span>
          {totalChunks > 1 && (
            <span className="loading-progress">
              ({currentChunk} of {totalChunks} pages)
            </span>
          )}
        </div>
        <button 
          className="hide-loading-btn"
          onClick={() => setHidden(true)}
          title="Hide loading bar"
        >
          &times;
        </button>
      </div>
    </div>
  );
}

export default LoadingBar;
