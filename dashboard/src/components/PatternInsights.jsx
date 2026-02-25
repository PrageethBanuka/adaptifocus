/**
 * PatternInsights — Shows discovered behavioral patterns and vulnerability windows.
 */

import {
  RadarChart, Radar, PolarGrid, PolarAngleAxis,
  ResponsiveContainer, PolarRadiusAxis,
} from 'recharts'

function formatHour(h) {
  if (h === 0) return '12AM'
  if (h === 12) return '12PM'
  if (h < 12) return `${h}AM`
  return `${h - 12}PM`
}

export default function PatternInsights({ summary, hourly }) {
  // Convert hourly data into vulnerability radar
  const radarData = hourly
    .filter(h => h.total > 0)
    .map(h => ({
      hour: formatHour(h.hour),
      vulnerability: h.total > 0
        ? Math.round((h.distraction / h.total) * 100)
        : 0,
      fullMark: 100,
    }))

  // Find peak vulnerability hours
  const peakHours = hourly
    .filter(h => h.total > 0)
    .sort((a, b) => (b.distraction / b.total) - (a.distraction / a.total))
    .slice(0, 3)

  // Find best focus hours
  const bestHours = hourly
    .filter(h => h.total > 0)
    .sort((a, b) => (b.focus / b.total) - (a.focus / a.total))
    .slice(0, 3)

  return (
    <div className="card chart-card">
      <div className="card-label">🧠 Pattern Insights</div>

      {/* Vulnerability Radar */}
      {radarData.length > 0 && (
        <div style={{ width: '100%', height: '200px', marginBottom: '16px' }}>
          <ResponsiveContainer>
            <RadarChart data={radarData}>
              <PolarGrid stroke="rgba(255,255,255,0.08)" />
              <PolarAngleAxis
                dataKey="hour"
                tick={{ fill: '#606070', fontSize: 9 }}
              />
              <PolarRadiusAxis
                angle={90}
                domain={[0, 100]}
                tick={false}
                axisLine={false}
              />
              <Radar
                name="Distraction %"
                dataKey="vulnerability"
                stroke="#ff6b6b"
                fill="#ff6b6b"
                fillOpacity={0.15}
                strokeWidth={2}
              />
            </RadarChart>
          </ResponsiveContainer>
        </div>
      )}

      {/* Quick insights */}
      <div style={{ fontSize: '13px', lineHeight: '1.8' }}>
        {peakHours.length > 0 && (
          <div style={{ marginBottom: '8px' }}>
            <span style={{ color: '#ff6b6b', fontWeight: 600 }}>⚠️ Peak vulnerability: </span>
            <span style={{ color: '#a0a0b0' }}>
              {peakHours.map(h => formatHour(h.hour)).join(', ')}
            </span>
          </div>
        )}
        {bestHours.length > 0 && (
          <div style={{ marginBottom: '8px' }}>
            <span style={{ color: '#4ecdc4', fontWeight: 600 }}>🎯 Best focus hours: </span>
            <span style={{ color: '#a0a0b0' }}>
              {bestHours.map(h => formatHour(h.hour)).join(', ')}
            </span>
          </div>
        )}
        {summary && (
          <div>
            <span style={{ color: '#667eea', fontWeight: 600 }}>📊 Total events: </span>
            <span style={{ color: '#a0a0b0' }}>
              {summary.total_events} across {Math.round(summary.total_seconds / 3600)}h
            </span>
          </div>
        )}
      </div>
    </div>
  )
}
