/**
 * PatternInsights — Vulnerability radar + insights with Lucide icons.
 */

import { Brain, AlertTriangle, Target, Activity } from 'lucide-react'
import {
  RadarChart, Radar, PolarGrid, PolarAngleAxis,
  ResponsiveContainer, PolarRadiusAxis, Legend,
} from 'recharts'

function formatHour(h) {
  if (h === 0) return '12a'
  if (h === 12) return '12p'
  if (h < 12) return `${h}a`
  return `${h - 12}p`
}

export default function PatternInsights({ summary, hourly }) {
  if (!hourly || hourly.length === 0) {
    return (
      <div className="card chart-card">
        <div className="card-label"><Brain size={14} /> Pattern Insights</div>
        <div className="empty-state">
          <div className="empty-icon"><Brain size={18} /></div>
          <p>No pattern data yet</p>
        </div>
      </div>
    )
  }

  const radarData = hourly
    .filter(h => h.total > 0)
    .map(h => ({
      hour: formatHour(h.hour),
      focus: Math.round((h.focus / h.total) * 100),
      distraction: Math.round((h.distraction / h.total) * 100),
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
        <div style={{ width: '100%', height: '210px', marginBottom: '14px' }}>
          <ResponsiveContainer>
            <RadarChart data={radarData}>
              <PolarGrid stroke="rgba(255,255,255,0.05)" />
              <PolarAngleAxis
                dataKey="hour"
                tick={{ fill: '#48484A', fontSize: 8 }}
              />
              <PolarRadiusAxis angle={90} domain={[0, 100]} tick={false} axisLine={false} />
              <Radar
                name="Focus %"
                dataKey="focus"
                stroke="#30D158"
                fill="#30D158"
                fillOpacity={0.08}
                strokeWidth={1.5}
              />
              <Radar
                name="Distraction %"
                dataKey="distraction"
                stroke="#FF453A"
                fill="#FF453A"
                fillOpacity={0.08}
                strokeWidth={1.5}
              />
              <Legend
                wrapperStyle={{ fontSize: '10px', color: '#48484A' }}
                iconSize={8}
              />
            </RadarChart>
          </ResponsiveContainer>
        </div>
      )}

      <div style={{ fontSize: '12px', lineHeight: '2' }}>
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

