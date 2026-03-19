/**
 * FocusTimeline — Hourly stacked bar chart with clean Apple styling.
 */

import { BarChart3 } from 'lucide-react'
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid,
  Tooltip, ResponsiveContainer,
} from 'recharts'

function formatHour(h) {
  if (h === 0) return '12a'
  if (h === 12) return '12p'
  if (h < 12) return `${h}a`
  return `${h - 12}p`
}

function formatSeconds(s) {
  if (s < 60) return `${s}s`
  return `${Math.floor(s / 60)}m`
}

const CustomTooltip = ({ active, payload, label }) => {
  if (!active || !payload) return null
  return (
    <div style={{
      background: 'rgba(28, 28, 30, 0.95)',
      backdropFilter: 'blur(20px)',
      border: '1px solid rgba(255,255,255,0.08)',
      borderRadius: '10px',
      padding: '10px 14px',
      fontSize: '12px',
    }}>
      <p style={{ fontWeight: 600, marginBottom: '4px', color: '#F5F5F7', fontSize: '11px' }}>
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
        <div className="card-label"><BarChart3 size={14} /> Hourly Timeline</div>
        <div className="empty-state">
          <div className="empty-icon"><BarChart3 size={18} /></div>
          <p>No hourly data available</p>
        </div>
      </div>
    )
  }

  return (
    <div className="card chart-card">
      <div className="card-label"><BarChart3 size={14} /> Hourly Timeline</div>
      <div className="chart-wrapper">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={data} barGap={0}>
            <CartesianGrid
              strokeDasharray="3 3"
              stroke="rgba(255,255,255,0.03)"
              vertical={false}
            />
            <XAxis
              dataKey="hour"
              tickFormatter={formatHour}
              stroke="transparent"
              tick={{ fill: '#48484A', fontSize: 10 }}
              axisLine={false}
              tickLine={false}
            />
            <YAxis
              tickFormatter={formatSeconds}
              stroke="transparent"
              tick={{ fill: '#48484A', fontSize: 10 }}
              axisLine={false}
              tickLine={false}
            />
            <Tooltip content={<CustomTooltip />} />
            <Bar
              dataKey="focus"
              name="Focus"
              fill="#30D158"
              radius={[3, 3, 0, 0]}
              stackId="stack"
            />
            <Bar
              dataKey="distraction"
              name="Distraction"
              fill="#FF453A"
              radius={[3, 3, 0, 0]}
              stackId="stack"
            />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  )
}
