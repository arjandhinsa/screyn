import { useEffect, useState } from 'react'
import './History.css'

function formatDuration(seconds) {
  if (!seconds) return '—'
  const h = Math.floor(seconds / 3600)
  const m = Math.floor((seconds % 3600) / 60)
  if (h > 0) return `${h}h ${m}m`
  return `${m}m`
}

function formatDate(iso) {
  if (!iso) return '—'
  const d = new Date(iso)
  return d.toLocaleString(undefined, {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
}

function focusAccent(score) {
  if (score == null) return '#E8E6E1'
  if (score >= 65) return '#3DBFA0'
  if (score >= 40) return '#E8A838'
  return '#E85A71'
}

export default function History() {
  const [sessions, setSessions] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    let cancelled = false
    async function load() {
      try {
        const res = await fetch('/api/sessions?limit=50')
        if (!res.ok) throw new Error('Failed to fetch sessions')
        const data = await res.json()
        if (!cancelled) setSessions(data)
      } catch (err) {
        if (!cancelled) setError(err.message)
      } finally {
        if (!cancelled) setLoading(false)
      }
    }
    load()
    return () => { cancelled = true }
  }, [])

  if (loading) {
    return <div className="history-empty">Loading sessions…</div>
  }

  if (error) {
    return (
      <div className="history-empty">
        Could not load sessions. Is the backend running?
      </div>
    )
  }

  if (!sessions.length) {
    return (
      <div className="history-empty">
        No sessions yet. Sit in front of your camera and start working — Screyn will
        record your first session automatically.
      </div>
    )
  }

  return (
    <div className="history">
      <div className="section-label">Recent sessions</div>
      <div className="history-list">
        {sessions.map((s) => (
          <div key={s.id} className="history-card">
            <div className="history-card-main">
              <div className="history-date">{formatDate(s.start_time)}</div>
              <div className="history-duration mono">{formatDuration(s.duration_seconds)}</div>
            </div>
            <div className="history-card-metrics">
              <div className="history-metric">
                <span className="history-metric-label">Focus</span>
                <span
                  className="history-metric-value mono"
                  style={{ color: focusAccent(s.avg_focus_score) }}
                >
                  {s.avg_focus_score != null ? Math.round(s.avg_focus_score) : '—'}
                </span>
              </div>
              <div className="history-metric">
                <span className="history-metric-label">Blinks/min</span>
                <span className="history-metric-value mono">
                  {s.avg_blink_rate != null ? s.avg_blink_rate.toFixed(1) : '—'}
                </span>
              </div>
              <div className="history-metric">
                <span className="history-metric-label">Breaks</span>
                <span className="history-metric-value mono">{s.break_count}</span>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
