import React, { useState, useEffect } from 'react'
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom'
import Navigation from './components/Navigation'
import Home from './pages/Home'
import Gauges from './pages/Gauges'
import Charts from './pages/Charts'
import './App.css'

function App() {
  const [darkMode, setDarkMode] = useState(() => {
    const saved = localStorage.getItem('darkMode')
    return saved ? JSON.parse(saved) : false
  })

  useEffect(() => {
    if (darkMode) {
      document.body.classList.add('dark-mode')
    } else {
      document.body.classList.remove('dark-mode')
    }
    localStorage.setItem('darkMode', JSON.stringify(darkMode))
  }, [darkMode])

  const toggleDarkMode = () => {
    setDarkMode(!darkMode)
  }

  return (
    <Router>
      <Navigation darkMode={darkMode} toggleDarkMode={toggleDarkMode} />
      <div className="app">
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/gauges" element={<Gauges />} />
          <Route path="/charts" element={<Charts />} />
        </Routes>
      </div>
    </Router>
  )
}

export default App

