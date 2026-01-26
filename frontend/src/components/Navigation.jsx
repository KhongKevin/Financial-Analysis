import React from 'react'
import { Link, useLocation } from 'react-router-dom'
import './Navigation.css'

function Navigation({ darkMode, toggleDarkMode }) {
  const location = useLocation()

  const isMoreActive = location.pathname === '/about' || location.pathname === '/how-to-use'
  const isGaugesActive = location.pathname.startsWith('/gauges')

  return (
    <nav className={`navigation ${darkMode ? 'dark' : ''}`}>
      <div className="nav-title">
        {location.pathname === '/' ? 'Home' :
          isGaugesActive ? 'Gauges' :
            location.pathname === '/charts' ? 'Charts' : 'Finance'}
      </div>

      <div className="nav-links-container">
        <div className="nav-links">
          <Link to="/" className={`nav-link ${location.pathname === '/' ? 'active' : ''}`}>
            <svg className="nav-icon" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"></path>
              <polyline points="9 22 9 12 15 12 15 22"></polyline>
            </svg>
            HOME
          </Link>
          <Link to="/gauges" className={`nav-link ${isGaugesActive ? 'active' : ''}`}>
            <svg className="nav-icon" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <circle cx="12" cy="12" r="10"></circle>
              <polyline points="12 6 12 12 16 14"></polyline>
            </svg>
            GAUGES
          </Link>
          <Link to="/charts" className={`nav-link ${location.pathname === '/charts' ? 'active' : ''}`}>
            <svg className="nav-icon" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <circle cx="12" cy="12" r="10"></circle>
              <polyline points="12 8 12 12 14 14"></polyline>
            </svg>
            CHARTS
          </Link>

          <div className="nav-dropdown-container">
            <button className={`nav-link dropdown-trigger ${isMoreActive ? 'active' : ''}`}>
              <svg className="nav-icon" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <circle cx="12" cy="12" r="1"></circle>
                <circle cx="19" cy="12" r="1"></circle>
                <circle cx="5" cy="12" r="1"></circle>
              </svg>
              MORE
            </button>
            <div className="nav-dropdown-menu">
              <Link to="/about" className="dropdown-item">About</Link>
              <Link to="/how-to-use" className="dropdown-item">How to Use</Link>
            </div>
          </div>
        </div>
      </div>

      {/* Dark mode toggle removed as requested */}
      <div className="nav-content">
      </div>

    </nav>
  )
}

export default Navigation


