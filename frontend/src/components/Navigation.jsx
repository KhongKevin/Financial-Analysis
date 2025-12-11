import React from 'react'
import { Link, useLocation } from 'react-router-dom'
import './Navigation.css'

function Navigation({ darkMode, toggleDarkMode }) {
  const location = useLocation()

  return (
    <nav className={`navigation ${darkMode ? 'dark' : ''}`}>
      <div className="nav-content">
        <Link to="/" className={`nav-link ${location.pathname === '/' ? 'active' : ''}`}>
          Home
        </Link>
        <Link to="/gauges" className={`nav-link ${location.pathname === '/gauges' ? 'active' : ''}`}>
          Gauges
        </Link>
        <Link to="/charts" className={`nav-link ${location.pathname === '/charts' ? 'active' : ''}`}>
          Charts
        </Link>
        <button className="dark-mode-toggle" onClick={toggleDarkMode} aria-label="Toggle dark mode">
          {darkMode ? '☀️' : '🌙'}
        </button>
      </div>
    </nav>
  )
}

export default Navigation

