/**
 * PatternInsights — Vulnerability radar + insights with Lucide icons.
 */

import { Brain, AlertTriangle, Target, Activity } from 'lucide-react'
import {
  RadarChart, Radar, PolarGrid, PolarAngleAxis,
  ResponsiveContainer, PolarRadiusAxis,
} from 'recharts'

function formatHour(h) {
  if (h === 0) return '12a'
  if (h === 12) return '12p'
  if (h < 12) return `${h}a`
  return `${h - 12}p`
}

export default function PatternInsights({ summary, hourly }) {
  const radarData = hourly
    .filter(h => h.total > 0)
    .map(h => ({
      hour: formatHour(h.hour),
      vulnerability: h.total > 0
        ? Math.round((h.distraction / h.total) * 100)
        : 0,
      fullMark: 100,
    }))

  const peakHours = hourly
    .filter(h => h.total > 0)
    .sort((a, b) => (b.distraction / b.total) - (a.distraction / a.total))
    .slice(0, 3)

  const bestHours = hourly
    .filter(h => h.total > 0)
    .sort((a, b) => (b.focus / b.total) - (a.focus / a.total))
    .slice(0, 3)

  return (
    <div className="card chart-card">
      <div className="card-label"><Brain size={14} /> Pattern Insights</div>

      {radarData.length > 0 && (
        <div style={{ width: '100%', height: '190px', marginBottom: '14px' }}>
          <ResponsiveContainer>
            <RadarChart data={radarData}>
              <PolarGrid stroke="rgba(255,255,255,0.05)" />
              <PolarAngleAxis
                dataKey="hour"
                tick={{ fill: '#48484A', fontSize: 8 }}
              />
              <PolarRadiusAxis angle={90} domain={[0, 100]} tick={false} axisLine={false} />
              <Radar
                name="Distraction %"
                dataKey="vulnerability"
                stroke="#FF453A"
                fill="#FF453A"
                fillOpacity={0.1}
                strokeWidth={1.5}
              />
            </RadarChart>
          </ResponsiveContainer>
        </div>
      )}

      <div style={{ fontSize: '12px', lineHeight: '2' }}>
        {peakHours.length > 0 && (
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
            <AlertTriangle size={12} style={{ color: '#FF453A', flexShrink: 0 }} />
            <span style={{ color: '#98989D' }}>
              Peak vulnerability: <span style={{ color: '#F5F5F7', fontWeight: 500 }}>
                {peakHours.map(h => formatHour(h.hour)).join(', ')}
              </span>
            </span>
          </div>
        )}
        {bestHours.length > 0 && (
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
            <Target size={12} style={{ color: '#30D158', flexShrink: 0 }} />
            <span style={{ color: '#98989D' }}>
              Best focus hours: <span style={{ color: '#F5F5F7', fontWeight: 500 }}>
                {bestHours.map(h => formatHour(h.hour)).join(', ')}
              </span>
            </span>
          </div>
        )}
        {summary && (
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
            <Activity size={12} style={{ color: '#0A84FF', flexShrink: 0 }} />
            <span style={{ color: '#98989D' }}>
              {summary.total_events} events across <span style={{ color: '#F5F5F7', fontWeight: 500 }}>
                {Math.round(summary.total_seconds / 3600)}h
              </span>
            </span>
          </div>
        )}
      </div>
    </div>
  )
}
