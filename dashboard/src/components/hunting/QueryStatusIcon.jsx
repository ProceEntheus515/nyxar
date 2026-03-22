export function QueryStatusIcon({ variant }) {
  if (variant === 'running') {
    return (
      <svg className="huntSpin" width="18" height="18" viewBox="0 0 24 24" aria-hidden="true">
        <circle
          cx="12"
          cy="12"
          r="10"
          fill="none"
          stroke="var(--color-primary)"
          strokeWidth="3"
          strokeDasharray="32"
          strokeLinecap="round"
          opacity="0.35"
        />
        <circle
          cx="12"
          cy="12"
          r="10"
          fill="none"
          stroke="var(--color-primary)"
          strokeWidth="3"
          strokeDasharray="16 48"
          strokeLinecap="round"
        />
      </svg>
    )
  }
  if (variant === 'timeout') {
    return (
      <svg width="18" height="18" viewBox="0 0 24 24" aria-hidden="true">
        <path
          fill="var(--color-warning)"
          d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm1 15h-2v-2h2v2zm0-4h-2V7h2v6z"
        />
      </svg>
    )
  }
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" aria-hidden="true">
      <path
        fill="var(--color-success)"
        d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-2 15l-5-5 1.41-1.41L10 14.17l7.59-7.59L19 8l-9 9z"
      />
    </svg>
  )
}
