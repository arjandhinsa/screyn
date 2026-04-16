export default function FocusGauge({ score = 0 }) {
  const size = 220
  const stroke = 14
  const radius = (size - stroke) / 2
  const circumference = 2 * Math.PI * radius
  const clamped = Math.max(0, Math.min(100, score))
  const offset = circumference - (clamped / 100) * circumference

  // Colour band
  let accent = '#3DBFA0' // good
  if (clamped < 40) accent = '#E85A71'        // bad
  else if (clamped < 65) accent = '#E8A838'   // warn

  return (
    <div className="focus-gauge">
      <svg width={size} height={size}>
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          stroke="rgba(255,255,255,0.06)"
          strokeWidth={stroke}
        />
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          stroke={accent}
          strokeWidth={stroke}
          strokeLinecap="round"
          strokeDasharray={circumference}
          strokeDashoffset={offset}
          transform={`rotate(-90 ${size / 2} ${size / 2})`}
          style={{ transition: 'stroke-dashoffset 0.6s ease, stroke 0.6s ease' }}
        />
      </svg>
      <div className="focus-gauge-inner">
        <div className="focus-gauge-label">Focus</div>
        <div className="focus-gauge-value mono" style={{ color: accent }}>
          {Math.round(clamped)}
        </div>
        <div className="focus-gauge-max">/ 100</div>
      </div>
    </div>
  )
}
