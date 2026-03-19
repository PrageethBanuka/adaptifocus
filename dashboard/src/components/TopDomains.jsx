/**
 * TopDomains — Domain ranking with clean bar visualization.
 */

import { Globe, Smartphone, Monitor } from 'lucide-react'

function formatDuration(seconds) {
  if (!seconds || seconds <= 0) return '0m'
  const h = Math.floor(seconds / 3600)
  const m = Math.floor((seconds % 3600) / 60)
  if (h > 0) return `${h}h ${m}m`
  return `${m}m`
}

function DomainList({ domains, type, maxSeconds }) {
  if (!domains || domains.length === 0) {
    return <p style={{ color: 'var(--text-muted)', fontSize: '12px' }}>No data</p>
  }

  return (
    <ul className="domain-list">
      {domains.map((d, i) => {
        const pct = maxSeconds > 0 ? (d.seconds / maxSeconds) * 100 : 0
        return (
          <li key={i} className="domain-item">
            <span className="domain-name">{d.domain}</span>
            <div className="domain-bar-wrapper">
              <div
                className={`domain-bar ${type}`}
                style={{ width: `${Math.max(pct, 2)}%` }}
              />
            </div>
            <span className="domain-time">{formatDuration(d.seconds)}</span>
          </li>
        )
      })}
    </ul>
  )
}

export default function TopDomains({ summary }) {
  if (!summary) return null

  const distractingDomains = summary.top_distracting_domains || []
  const productiveDomains = summary.top_productive_domains || []

  const maxDistraction = distractingDomains.length > 0 ? distractingDomains[0].seconds : 1
  const maxProductive = productiveDomains.length > 0 ? productiveDomains[0].seconds : 1

  return (
    <div className="card">
      <div className="card-label"><Globe size={14} /> Top Domains</div>

      <div style={{ marginBottom: '18px' }}>
        <div className="section-subtitle" style={{ color: '#FF453A' }}>
          <Smartphone size={13} />
          Most Distracting
        </div>
        <DomainList
          domains={distractingDomains}
          type="distraction"
          maxSeconds={maxDistraction}
        />
      </div>

      <div>
        <div className="section-subtitle" style={{ color: '#30D158' }}>
          <Monitor size={13} />
          Most Productive
        </div>
        <DomainList
          domains={productiveDomains}
          type="productive"
          maxSeconds={maxProductive}
        />
      </div>
    </div>
  )
}
