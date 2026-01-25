import React from 'react'

const HowToUse = () => {
    return (
        <div style={{
            padding: '2rem',
            color: 'rgba(255, 255, 255, 0.9)',
            background: 'rgba(255, 255, 255, 0.05)',
            borderRadius: '8px',
            margin: '2rem auto',
            maxWidth: '800px',
            backdropFilter: 'blur(10px)',
            border: '1px solid rgba(255, 255, 255, 0.1)'
        }}>
            <h1>How to Use</h1>
            <p>Welcome to the Financial Analysis Dashboard. Here is how to navigate and use the features:</p>

            <br />

            <h3>1. Home Page</h3>
            <ul>
                <li>Enter stock tickers (comma separated) in the input field.</li>
                <li>Set the number of years for analysis.</li>
                <li>Click "LOAD DATA" to fetch the latest Value Scores and P/E Ratios.</li>
                <li>Click on any stock card to expand it for more details (Full Gauge & Chart).</li>
            </ul>

            <br />

            <h3>2. Gauges Page</h3>
            <ul>
                <li>View comprehensive "Value Score" gauges for all loaded stocks.</li>
                <li>Scores are based on historical P/E averages (0-100 scale).</li>
            </ul>

            <br />

            <h3>3. Charts Page</h3>
            <ul>
                <li>Compare P/E Ratio trends over time.</li>
                <li>Visualize TTM (Trailing Twelve Months) and Forward P/E (if available).</li>
            </ul>
        </div>
    )
}

export default HowToUse
