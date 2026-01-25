import React from 'react'

const About = () => {
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
            <h1>About This Project</h1>
            <p>
                This financial dashboard provides simulated analysis of PE Ratios and Value Scores for various tech stocks.
            </p>
            <p>
                It demonstrates modern UI design principles including Glassmorphism, dynamic data visualization, and responsive layouts.
            </p>
            <br />
            <h3>Features</h3>
            <ul>
                <li>Real-time interaction with simulated data</li>
                <li>Interactive Gauges</li>
                <li>Historical P/E Charts</li>
                <li>Modern Glass UI</li>
            </ul>
        </div>
    )
}

export default About
