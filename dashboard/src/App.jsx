import { useState, useEffect } from 'react'
import { getFocusSummary, getHourlyBreakdown, getInterventionHistory } from './api/client.js'
import FocusTimeline from './components/FocusTimeline.jsx'
import PatternInsights from './components/PatternInsights.jsx'
import InterventionLog from './components/InterventionLog.jsx'
import TopDomains from './components/TopDomains.jsx'
import StatCards from './components/StatCards.jsx'

function App() {
  const [summary, setSummary] = useState(null)
  const [hourly, setHourly] = useState([])
  const [interventions, setInterventions] = useState([])
  const [days, setDays] = useState(7)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    // Check for token in URL (sent by the extension)
    const params = new URLSearchParams(window.location.search)
    const urlToken = params.get('token')
    if (urlToken) {
      localStorage.setItem('adaptifocus_token', urlToken)
      // Clean up URL so token isn't visible/bookmarked
      window.history.replaceState({}, document.title, window.location.pathname)
    }

    loadData()
  }, [days])

  async function loadData() {
    setLoading(true)
    setError(null)
    try {
      const [summaryData, hourlyData, interventionData] = await Promise.all([
        getFocusSummary(days),
        getHourlyBreakdown(days),
        getInterventionHistory(days),
      ])
      setSummary(summaryData)
      setHourly(hourlyData)
      setInterventions(interventionData)
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }

  if (error) {
    return (
      <div className="dashboard-container">
        <div className="empty-state">
          <div className="empty-icon">⚠️</div>
          <p>Could not connect to the backend API.</p>
          <p style={{ fontSize: '13px', marginTop: '8px', color: 'var(--text-muted)' }}>
            Make sure the backend is running: <code>uvicorn main:app --reload</code>
          </p>
          <button className="control-btn" style={{ marginTop: '16px' }} onClick={loadData}>
            Retry
          </button>
        </div>
      </div>
    )
  }

  return (
    <div className="dashboard-container">
      {/* Header */}
      <header className="dashboard-header">
        <div className="dashboard-header-left">
          <span className="dashboard-logo">🎯</span>
          <div>
            <h1 className="dashboard-title">AdaptiFocus</h1>
            <p className="dashboard-subtitle">AI-Driven Attention Analytics</p>
          </div>
        </div>
        <div className="dashboard-controls">
          {[1, 7, 14, 30].map(d => (
            <button
              key={d}
              className={`control-btn ${days === d ? 'active' : ''}`}
              onClick={() => setDays(d)}
            >
              {d === 1 ? 'Today' : `${d}D`}
            </button>
          ))}
        </div>
      </header>

      {loading ? (
        <div className="loading">
          <div className="loading-spinner" />
          Loading analytics...
        </div>
      ) : (
        <>
          {/* Stat Cards Row */}
          <StatCards summary={summary} />

          {/* Hourly Focus Timeline */}
          <div className="dashboard-row-3">
            <FocusTimeline data={hourly} />
            <PatternInsights summary={summary} hourly={hourly} />
          </div>

          {/* Bottom Row: Domains + Interventions */}
          <div className="dashboard-row">
            <TopDomains summary={summary} />
            <InterventionLog interventions={interventions} />
          </div>
        </>
      )}
    </div>
  )
}

export default App
