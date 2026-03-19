/**
 * StreakCard — Focus streak display with ring visual and badge.
 */

import { Flame, Zap, Star, Diamond, Sparkles, Target } from 'lucide-react'

const BADGES = {
  5: { icon: Diamond, label: 'Diamond Focus', color: '#BF5AF2' },
  4: { icon: Flame, label: 'On Fire', color: '#FF9F0A' },
  3: { icon: Zap, label: 'Streak Master', color: '#FFD60A' },
  2: { icon: Star, label: 'Rising Star', color: '#0A84FF' },
  1: { icon: Sparkles, label: 'Getting Started', color: '#30D158' },
  0: { icon: Target, label: 'Start Your Journey', color: '#48484A' },
}

export default function StreakCard({ streak }) {
  if (!streak) return null

  const badge = BADGES[streak.badge?.level ?? 0] || BADGES[0]
  const BadgeIcon = badge.icon

  return (
    <div className="card streak-card">
      <div className="card-label"><Flame size={14} /> Focus Streak</div>

      <div className="streak-ring" style={{ 
        borderColor: `${badge.color}40`,
        background: `${badge.color}15`,
        color: badge.color,
      }}>
        {streak.current_streak}
      </div>

      <div className="streak-badge-title" style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
        <BadgeIcon size={15} style={{ color: badge.color }} />
        {badge.label}
      </div>

      <div className="streak-badge-sub">
        Best: {streak.best_streak} days · {streak.total_focused_sessions} total sessions
      </div>
    </div>
  )
}
