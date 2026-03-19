/**
 * ProductivityGauge — Circular gauge showing daily productivity score.
 */

import { Gauge } from 'lucide-react'

function getColor(score) {
  if (score >= 80) return '#30D158'
  if (score >= 60) return '#0A84FF'
  if (score >= 40) return '#FF9F0A'
  return '#FF453A'
}

export default function ProductivityGauge({ report }) {
  if (!report) return null

  const score = report.productivity_score || 0
  const color = getColor(score)
  const radius = 56
  const circumference = 2 * Math.PI * radius
  const offset = circumference - (score / 100) * circumference

  return (
    <div className="card">
      <div className="card-label"><Gauge size={14} /> Productivity</div>

      <div className="gauge-container">
        <div className="gauge-ring">
          <svg width="140" height="140">
            {/* Background ring */}
            <circle
              cx="70" cy="70" r={radius}
              fill="none"
              stroke="rgba(255,255,255,0.04)"
              strokeWidth="8"
            />
            {/* Progress ring */}
            <circle
              cx="70" cy="70" r={radius}
              fill="none"
              stroke={color}
              strokeWidth="8"
              strokeLinecap="round"
              strokeDasharray={circumference}
              strokeDashoffset={offset}
              style={{ transition: 'stroke-dashoffset 1s cubic-bezier(0.25, 0.46, 0.45, 0.94)' }}
            />
          </svg>
          <div className="gauge-center">
            <div className="gauge-value" style={{ color }}>{score}%</div>
            <div className="gauge-label-text">Score</div>
          </div>
        </div>

        {report.grade && (
          <div className="gauge-grade">
            {report.grade.letter} — {report.grade.message}
          </div>
        )}
      </div>
    </div>
  )
}
