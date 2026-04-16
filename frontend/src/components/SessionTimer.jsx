import { useEffect, useState } from 'react'

function formatDuration(seconds) {
  if (!seconds || seconds < 0) return '00:00'
  const h = Math.floor(seconds / 3600)
  const m = Math.floor((seconds % 3600) / 60)
  const s = Math.floor(seconds % 60)
  if (h > 0) {
    return `${String(h).padStart(2, '0')}:${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`
  }
  return `${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`
}

export default function SessionTimer({ sessionId, activeSeconds = 0 }) {
  const [displaySeconds, setDisplaySeconds] = useState(0)

  // Sync with backend value
  useEffect(() => {
    setDisplaySeconds(activeSeconds)
  }, [activeSeconds])

  // Tick locally between WS updates for smoothness
  useEffect(() => {
    if (!sessionId) return
    const interval = setInterval(() => {
      setDisplaySeconds((s) => s + 1)
    }, 1000)
    return () => clearInterval(interval)
  }, [sessionId])

  return (
    <div className="session-timer">
      <div className="session-timer-label">
        {sessionId ? 'Active session' : 'Waiting for you'}
      </div>
      <div className="session-timer-value mono">{formatDuration(displaySeconds)}</div>
    </div>
  )
}