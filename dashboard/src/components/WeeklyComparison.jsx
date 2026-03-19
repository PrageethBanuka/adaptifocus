/**
 * WeeklyComparison — Week-over-week trend with day-by-day breakdown.
 */

import { TrendingUp, TrendingDown, Minus, Calendar } from 'lucide-react'

function formatDuration(seconds) {
  if (!seconds || seconds <= 0) return '0m'
  const h = Math.floor(seconds / 3600)
  const m = Math.floor((seconds % 3600) / 60)
  if (h > 0) return `${h}h ${m}m`
  return `${m}m`
}

export default function WeeklyComparison({ report }) {
  if (!report) return null

  const TrendIcon = report.trend > 0 ? TrendingUp : report.trend < 0 ? TrendingDown : Minus
  const trendClass = report.trend > 0 ? 'up' : report.trend < 0 ? 'down' : 'stable'

  return (
    <div className="card">
      <div className="card-label"><Calendar size={14} /> Weekly Overview</div>

      {/* Trend badge */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '16px' }}>
        <span style={{ fontSize: '24px', fontWeight: 700, color: 'var(--text-primary)' }}>
          {report.productivity_score}%
        </span>
        <span className={`trend-badge ${trendClass}`}>
          <TrendIcon size={11} />
          {Math.abs(report.trend)}%
        </span>
        <span style={{ fontSize: '11px', color: 'var(--text-muted)' }}>
          vs last week
        </span>
      </div>

      {/* Day breakdown */}
      {report.daily_breakdown && (
        <div>
          {report.daily_breakdown.map((day) => (
            <div key={day.date} className="weekly-stat">
              <span className="weekly-stat-label">
                {day.day.slice(0, 3)}
              </span>
              <div style={{
                flex: 1,
                margin: '0 12px',
                height: '4px',
                background: 'rgba(255,255,255,0.04)',
                borderRadius: '2px',
                overflow: 'hidden',
              }}>
                <div style={{
                  height: '100%',
                  width: `${day.productivity}%`,
                  background: day.productivity >= 60 ? '#30D158' : day.productivity >= 40 ? '#FF9F0A' : '#FF453A',
                  borderRadius: '2px',
                  transition: 'width 0.5s ease',
                }} />
              </div>
              <span className="weekly-stat-value">{day.productivity}%</span>
            </div>
          ))}
        </div>
      )}

      {/* Best / worst */}
      {report.best_day && (
        <div style={{ marginTop: '12px', fontSize: '11px', color: 'var(--text-muted)' }}>
          Best: <span style={{ color: '#30D158', fontWeight: 500 }}>{report.best_day.day}</span>
          {report.worst_day && (
            <> · Weakest: <span style={{ color: '#FF453A', fontWeight: 500 }}>{report.worst_day.day}</span></>
          )}
        </div>
      )}
    </div>
  )
}
