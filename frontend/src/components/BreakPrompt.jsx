import { useEffect, useState } from 'react'

/**
 * Prominent prompt shown when a 20-20-20 break is due.
 * User clicks Start, watches the 20 second countdown, then the break
 * is automatically registered when the countdown hits zero.
 */
export default function BreakPrompt({ onComplete }) {
  const [phase, setPhase] = useState('ready') // 'ready' | 'counting'
  const [countdown, setCountdown] = useState(20)

  useEffect(() => {
    if (phase !== 'counting') return
    if (countdown <= 0) {
      onComplete()
      return
    }
    const timer = setTimeout(() => setCountdown((c) => c - 1), 1000)
    return () => clearTimeout(timer)
  }, [phase, countdown, onComplete])

  if (phase === 'counting') {
    return (
      <div className="break-prompt break-prompt--counting">
        <div className="break-prompt-countdown mono">{countdown}</div>
        <div className="break-prompt-content">
          <h3>Look at something 20 feet away</h3>
          <p>Give your eyes and mind a reset. Back in {countdown} seconds.</p>
        </div>
      </div>
    )
  }

  return (
    <div className="break-prompt">
      <div className="break-prompt-icon">👁</div>
      <div className="break-prompt-content">
        <h3>Time for a 20-20-20 break</h3>
        <p>
          Look at something 20 feet (6m) away for 20 seconds. Your eyes and your
          focus will thank you.
        </p>
      </div>
      <button
        className="break-prompt-button"
        onClick={() => setPhase('counting')}
      >
        Start break
      </button>
    </div>
  )
}