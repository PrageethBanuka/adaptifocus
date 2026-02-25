/**
 * InterventionLog — Shows recent interventions with level badges and outcomes.
 */

function timeAgo(isoString) {
  const now = new Date()
  const then = new Date(isoString)
  const diffMs = now - then
  const diffMins = Math.floor(diffMs / 60000)
  const diffHours = Math.floor(diffMs / 3600000)
  const diffDays = Math.floor(diffMs / 86400000)

  if (diffMins < 1) return 'just now'
  if (diffMins < 60) return `${diffMins}m ago`
  if (diffHours < 24) return `${diffHours}h ago`
  return `${diffDays}d ago`
}

function formatDuration(seconds) {
  if (!seconds || seconds <= 0) return '0s'
  if (seconds < 60) return `${seconds}s`
  const m = Math.floor(seconds / 60)
  return `${m}m`
}

export default function InterventionLog({ interventions }) {
  return (
    <div className="card">
      <div className="card-label" style={{ marginBottom: '16px' }}>
        🛡️ Intervention History
      </div>

      {(!interventions || interventions.length === 0) ? (
        <div className="empty-state" style={{ padding: '24px 0' }}>
          <div className="empty-icon">🛡️</div>
          <p>No interventions recorded yet</p>
        </div>
      ) : (
        <div style={{ maxHeight: '380px', overflowY: 'auto' }}>
          {interventions.map((item) => (
            <div key={item.id} className="intervention-item">
              <span className={`intervention-badge ${item.level}`}>
                {item.level.replace('_', ' ')}
              </span>
              <div style={{ flex: 1 }}>
                <div className="intervention-domain">
                  {item.trigger_domain || 'Unknown'}
                </div>
                <div className="intervention-time">
                  {timeAgo(item.timestamp)} · {formatDuration(item.duration_on_distraction)} on site
                </div>
              </div>
              {item.user_response && (
                <span className={`intervention-result ${item.user_response}`}>
                  {item.user_response}
                </span>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
