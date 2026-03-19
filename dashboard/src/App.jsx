import { useState, useEffect } from 'react'
import { Focus } from 'lucide-react'
import { getFocusSummary, getHourlyBreakdown, getInterventionHistory, getStreak, getDailyReport, getWeeklyReport } from './api/client.js'
import FocusTimeline from './components/FocusTimeline.jsx'
import PatternInsights from './components/PatternInsights.jsx'
import InterventionLog from './components/InterventionLog.jsx'
import TopDomains from './components/TopDomains.jsx'
import StatCards from './components/StatCards.jsx'
import StreakCard from './components/StreakCard.jsx'
import ProductivityGauge from './components/ProductivityGauge.jsx'
import WeeklyComparison from './components/WeeklyComparison.jsx'

function App() {
  const [summary, setSummary] = useState(null)
  const [hourly, setHourly] = useState([])
  const [interventions, setInterventions] = useState([])
  const [streak, setStreak] = useState(null)
  const [dailyReport, setDailyReport] = useState(null)
  const [weeklyReport, setWeeklyReport] = useState(null)
  const [days, setDays] = useState(7)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    const params = new URLSearchParams(window.location.search)
    const urlToken = params.get('token')
    if (urlToken) {
      localStorage.setItem('adaptifocus_token', urlToken)
      window.history.replaceState({}, document.title, window.location.pathname)
    }
    loadData()
  }, [days])

  async function loadData() {
    setLoading(true)
    setError(null)
    try {
      const [summaryData, hourlyData, interventionData, streakData, dailyData, weeklyData] = await Promise.all([
        getFocusSummary(days),
        getHourlyBreakdown(days),
        getInterventionHistory(days),
        getStreak().catch(() => null),
        getDailyReport().catch(() => null),
        getWeeklyReport().catch(() => null),
      ])
      setSummary(summaryData)
      setHourly(hourlyData)
      setInterventions(interventionData)
      setStreak(streakData)
      setDailyReport(dailyData)
      setWeeklyReport(weeklyData)
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }

  if (error) {
    return (
      <div className="dashboard-container">
        <div className="empty-state" style={{ paddingTop: '80px' }}>
          <div className="empty-icon"><Focus size={20} /></div>
          <p style={{ color: 'var(--text-secondary)', marginBottom: '6px' }}>Could not connect to the API</p>
          <p style={{ fontSize: '12px', color: 'var(--text-muted)' }}>
            Make sure the backend is running
          </p>
          <button
            className="control-btn"
            style={{ marginTop: '16px' }}
            onClick={loadData}
          >
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
          <div className="dashboard-logo"><Focus size={20} /></div>
          <div>
            <h1 className="dashboard-title">AdaptiFocus</h1>
            <p className="dashboard-subtitle">Attention Analytics</p>
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
          {/* KPI Cards */}
          <StatCards summary={summary} />

          {/* Row: Timeline + Patterns */}
          <div className="dashboard-row-3">
            <FocusTimeline data={hourly} />
            <PatternInsights summary={summary} hourly={hourly} />
          </div>

          {/* Row: Streak + Gauge + Weekly */}
          <div className="dashboard-grid" style={{ gridTemplateColumns: '1fr 1fr 2fr' }}>
            <StreakCard streak={streak} />
            <ProductivityGauge report={dailyReport} />
            <WeeklyComparison report={weeklyReport} />
          </div>

          {/* Row: Domains + Interventions */}
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
