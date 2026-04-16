import './Settings.css'

export default function Settings() {
  return (
    <div className="settings">
      <div className="section-label">Configuration</div>
      <p className="settings-note">
        Settings are currently controlled via the backend <code>.env</code> file.
        Live in-app editing is on the roadmap — for now, change values in
        <code>backend/.env</code> and restart the backend.
      </p>

      <div className="settings-group">
        <h3>Camera</h3>
        <div className="settings-row">
          <span className="settings-key">CAMERA_INDEX</span>
          <span className="settings-desc">Which camera to use (0 = default webcam)</span>
        </div>
        <div className="settings-row">
          <span className="settings-key">TARGET_FPS</span>
          <span className="settings-desc">Frame rate for CV pipeline (15 is plenty)</span>
        </div>
        <div className="settings-row">
          <span className="settings-key">SHOW_PREVIEW</span>
          <span className="settings-desc">Open a preview window during development</span>
        </div>
      </div>

      <div className="settings-group">
        <h3>Blink detection</h3>
        <div className="settings-row">
          <span className="settings-key">EAR_THRESHOLD</span>
          <span className="settings-desc">
            Eye Aspect Ratio cutoff for a blink. Default 0.20. Lower if blinks are
            over-counted; raise if they're missed.
          </span>
        </div>
        <div className="settings-row">
          <span className="settings-key">EAR_CONSEC_FRAMES</span>
          <span className="settings-desc">Frames the eye must stay closed to count as a blink</span>
        </div>
      </div>

      <div className="settings-group">
        <h3>Focus scoring</h3>
        <div className="settings-row">
          <span className="settings-key">HEALTHY_BLINK_RATE_MIN / MAX</span>
          <span className="settings-desc">Your personal healthy blink range (default 12–22/min)</span>
        </div>
      </div>

      <div className="settings-group">
        <h3>Privacy</h3>
        <p className="settings-note">
          All Screyn data stays on this device. No video is ever recorded or transmitted.
          The CV pipeline processes each frame in memory and discards it.
        </p>
      </div>
    </div>
  )
}
