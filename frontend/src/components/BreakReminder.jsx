const BREAK_IDEAL_SECONDS = 20 * 60

export default function BreakReminder({ secondsSinceBreak = 0, breakDue = false }) {
  // When due, the BreakPrompt component takes over — hide this
  if (breakDue) return null

  const minutesToBreak = Math.max(
    0,
    Math.floor((BREAK_IDEAL_SECONDS - secondsSinceBreak) / 60),
  )

  return (
    <div className="break-reminder break-reminder--ok">
      <div className="break-dot break-dot--ok" />
      <span>Next 20-20-20 break in {minutesToBreak} min</span>
    </div>
  )
}