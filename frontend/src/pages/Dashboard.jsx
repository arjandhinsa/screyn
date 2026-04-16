import useWebSocket from '../hooks/useWebSocket'
import FocusGauge from '../components/FocusGauge'
import MetricCard from '../components/MetricCard'
import SessionTimer from '../components/SessionTimer'
import BreakReminder from '../components/BreakReminder'
import BreakPrompt from '../components/BreakPrompt'
import './Dashboard.css'

function healthyBlinkAccent(rate) {
  if (rate >= 12 && rate <= 22) return '#3DBFA0'
  if (rate >= 8 && rate <= 28) return '#E8A838'
  return '#E85A71'
}

export default function Dashboard() {
  const { data, status } = useWebSocket('/ws/live')

  const faceDetected = data?.face_detected ?? false
  const focusScore = data?.focus_score ?? 0
  const blinkRate = data?.blink_rate ?? 0
  const headStability = data?.head_stability ?? 0
  const distance = data?.screen_distance_cm
  const totalBlinks = data?.total_blinks_this_session ?? 0
  const secondsSinceBreak = data?.seconds_since_break ?? 0
  const sessionId = data?.session_id
  const activeSeconds = data?.active_seconds ?? 0
  const breakDue = data?.break_due ?? false

  const handleBreakComplete = async () => {
    try {
      await fetch('/api/sessions/take-break', { method: 'POST' })
    } catch (err) {
      console.error('Failed to register break:', err)
    }
  }

  return (
    <div className="dashboard">
      <div className="dashboard-status">
        <div className={`status-pill status-pill--${status}`}>
          <span className="status-dot" />
          {status === 'connected' ? 'Live' : status === 'connecting' ? 'Connecting' : 'Reconnecting'}
        </div>
        {data && !faceDetected && (
          <div className="status-note">No face detected — sit in view of the camera</div>
        )}
      </div>

      {breakDue && sessionId && (
        <BreakPrompt onComplete={handleBreakComplete} />
      )}

      <div className="dashboard-hero">
        <div className="hero-left">
          <SessionTimer sessionId={sessionId} activeSeconds={activeSeconds} />
          <BreakReminder
            secondsSinceBreak={secondsSinceBreak}
            breakDue={breakDue}
          />
        </div>
        <div className="hero-right">
          <FocusGauge score={focusScore} />
        </div>
      </div>

      <div className="section-label">Live metrics</div>
      <div className="metrics-grid">
        <MetricCard
          label="Blink rate"
          value={blinkRate.toFixed(1)}
          unit="/ min"
          sub={
            blinkRate >= 12 && blinkRate <= 22
              ? 'Healthy range'
              : blinkRate < 12
              ? 'Low — possible strain'
              : 'High — possible fatigue'
          }
          accent={healthyBlinkAccent(blinkRate)}
        />
        <MetricCard
          label="Head stability"
          value={Math.round(headStability * 100)}
          unit="%"
          sub={headStability > 0.7 ? 'Steady focus' : 'High movement'}
        />
        <MetricCard
          label="Screen distance"
          value={distance ? Math.round(distance) : '—'}
          unit={distance ? 'cm' : ''}
          sub={
            !distance
              ? 'Calibrating'
              : distance < 40
              ? 'Too close'
              : distance > 80
              ? 'Very far'
              : 'Good'
          }
        />
        <MetricCard
          label="Blinks this session"
          value={totalBlinks}
          sub={sessionId ? `Session #${sessionId}` : 'No active session'}
        />
      </div>
 
      <div className="dashboard-note">
        <div className="section-label">How Screyn works</div>
        <p>
          Your blink rate, head stability, and break patterns predict your focus and
          strain more reliably than any timer alone. Screyn watches these signals locally
          so no video ever leaves this device, and it helps you build screen habits
          that keep both your eyes and your attention sharp.
        </p>
      </div>
    </div>
  )
}
 