/**
 * FocusTimeline — Hourly stacked bar chart showing focus vs distraction.
 */

import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid,
  Tooltip, ResponsiveContainer, Legend,
} from 'recharts'

function formatHour(h) {
  if (h === 0) return '12AM'
  if (h === 12) return '12PM'
  if (h < 12) return `${h}AM`
  return `${h - 12}PM`
}

function formatSeconds(s) {
  if (s < 60) return `${s}s`
  const m = Math.floor(s / 60)
  return `${m}m`
}

const CustomTooltip = ({ active, payload, label }) => {
  if (!active || !payload) return null
  return (
    <div style={{
      background: '#1a1a2e',
      border: '1px solid rgba(255,255,255,0.1)',
      borderRadius: '8px',
      padding: '12px 16px',
      fontSize: '13px',
    }}>
      <p style={{ fontWeight: 600, marginBottom: '6px', color: '#f0f0f0' }}>
        {formatHour(label)}
      </p>
      {payload.map((entry) => (
        <p key={entry.name} style={{ color: entry.color, margin: '2px 0' }}>
          {entry.name}: {formatSeconds(entry.value)}
        </p>
      ))}
    </div>
  )
}

export default function FocusTimeline({ data }) {
  if (!data || data.length === 0) {
    return (
      <div className="card chart-card">
        <div className="card-label">📊 Hourly Focus Timeline</div>
        <div className="empty-state">
          <div className="empty-icon">📊</div>
          <p>No hourly data available</p>
        </div>
      </div>
    )
  }

  const chartData = data.map(d => ({
    ...d,
    hourLabel: formatHour(d.hour),
  }))

  return (
    <div className="card chart-card">
      <div className="card-label">📊 Hourly Focus Timeline</div>
      <div className="chart-wrapper">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={chartData} barGap={0}>
            <CartesianGrid
              strokeDasharray="3 3"
              stroke="rgba(255,255,255,0.05)"
              vertical={false}
            />
            <XAxis
              dataKey="hour"
              tickFormatter={formatHour}
              stroke="rgba(255,255,255,0.2)"
              tick={{ fill: '#606070', fontSize: 11 }}
              axisLine={{ stroke: 'rgba(255,255,255,0.08)' }}
            />
            <YAxis
              tickFormatter={formatSeconds}
              stroke="rgba(255,255,255,0.2)"
              tick={{ fill: '#606070', fontSize: 11 }}
              axisLine={{ stroke: 'rgba(255,255,255,0.08)' }}
            />
            <Tooltip content={<CustomTooltip />} />
            <Legend
              wrapperStyle={{ fontSize: '12px', color: '#a0a0b0' }}
            />
            <Bar
              dataKey="focus"
              name="Focus"
              fill="#4ecdc4"
              radius={[3, 3, 0, 0]}
              stackId="stack"
            />
            <Bar
              dataKey="distraction"
              name="Distraction"
              fill="#ff6b6b"
              radius={[3, 3, 0, 0]}
              stackId="stack"
            />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  )
}
