/**
 * StatCards — KPI cards with Lucide icons and Apple-style accent lines.
 */

import { Target, Clock, Smartphone, Shield } from 'lucide-react'

function formatDuration(seconds) {
  if (!seconds || seconds <= 0) return '0m'
  const h = Math.floor(seconds / 3600)
  const m = Math.floor((seconds % 3600) / 60)
  if (h > 0) return `${h}h ${m}m`
  return `${m}m`
}

export default function StatCards({ summary }) {
  if (!summary) return null

  const cards = [
    {
      label: 'Focus Score',
      value: `${summary.focus_percentage || 0}%`,
      accent: 'focus',
      icon: Target,
      sub: null,
    },
    {
      label: 'Focus Time',
      value: formatDuration(summary.focus_seconds),
      accent: 'focus',
      icon: Clock,
      sub: null,
    },
    {
      label: 'Distraction Time',
      value: formatDuration(summary.distraction_seconds),
      accent: 'distraction',
      icon: Smartphone,
      sub: null,
    },
    {
      label: 'Interventions',
      value: summary.interventions_today || 0,
      accent: summary.interventions_today > 0 ? 'warning' : 'focus',
      icon: Shield,
      sub: summary.intervention_success_rate
        ? `${summary.intervention_success_rate}% effective`
        : null,
    },
  ]

  return (
    <div className="dashboard-grid">
      {cards.map((card) => {
        const Icon = card.icon
        return (
          <div key={card.label} className={`card stat-card ${card.accent}`}>
            <div className="card-label">
              <Icon size={14} />
              {card.label}
            </div>
            <div className={`card-value ${card.accent}`}>{card.value}</div>
            {card.sub && <div className="card-sub">{card.sub}</div>}
          </div>
        )
      })}
    </div>
  )
}
