/**
 * StatCards — Top-level KPI cards showing focus summary metrics.
 */

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
      icon: '🎯',
    },
    {
      label: 'Focus Time',
      value: formatDuration(summary.focus_seconds),
      accent: 'focus',
      icon: '⏱️',
    },
    {
      label: 'Distraction Time',
      value: formatDuration(summary.distraction_seconds),
      accent: 'distraction',
      icon: '📱',
    },
    {
      label: 'Interventions',
      value: summary.interventions_today || 0,
      accent: summary.interventions_today > 0 ? 'neutral' : 'success',
      icon: '🛡️',
      sub: summary.intervention_success_rate
        ? `${summary.intervention_success_rate}% effective`
        : null,
    },
  ]

  return (
    <div className="dashboard-grid">
      {cards.map((card) => (
        <div key={card.label} className={`card stat-card ${card.accent}`}>
          <div className="card-label">
            <span style={{ marginRight: '6px' }}>{card.icon}</span>
            {card.label}
          </div>
          <div className={`card-value ${card.accent}`}>{card.value}</div>
          {card.sub && (
            <div className="card-change positive">{card.sub}</div>
          )}
        </div>
      ))}
    </div>
  )
}
