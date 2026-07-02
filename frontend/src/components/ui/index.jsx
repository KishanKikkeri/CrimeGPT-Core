/* ── Readiness Gauge (SVG circle) ────────────────────────── */
export function Gauge({ score, size = 140 }) {
  const r = size * 0.38, cx = size / 2, cy = size / 2
  const circ = 2 * Math.PI * r
  const offset = circ * (1 - score / 100)
  const col = score >= 75 ? '#16A34A' : score >= 55 ? '#D97706' : '#DC2626'

  return (
    <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`} aria-label={`Case readiness ${score}%`}>
      <circle cx={cx} cy={cy} r={r} fill="none" stroke="#E2E8F0" strokeWidth={size * 0.056} />
      <circle
        cx={cx} cy={cy} r={r} fill="none"
        stroke={col} strokeWidth={size * 0.056}
        strokeDasharray={circ} strokeDashoffset={offset}
        strokeLinecap="round"
        transform={`rotate(-90 ${cx} ${cy})`}
      />
      <text x={cx} y={cy - size * 0.05} textAnchor="middle"
        fontSize={size * 0.19} fontWeight="500" fill={col}
        fontFamily="'JetBrains Mono', monospace">
        {score}%
      </text>
      <text x={cx} y={cy + size * 0.12} textAnchor="middle"
        fontSize={size * 0.08} fill="#64748B">
        readiness
      </text>
    </svg>
  )
}

/* ── Score bar ───────────────────────────────────────────── */
export function ScoreBar({ label, value, weight }) {
  const cls = value >= 75 ? 'sbar-green' : value >= 50 ? 'sbar-amber' : 'sbar-red'
  return (
    <div style={{ marginBottom: 9 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 12 }}>
        <span style={{ color: 'var(--text-secondary)' }}>{label}</span>
        <div style={{ display: 'flex', gap: 6 }}>
          {weight && <span style={{ color: 'var(--text-secondary)', fontSize: 11 }}>{Math.round(weight * 100)}%wt</span>}
          <span className="mono" style={{ fontWeight: 500 }}>{value}%</span>
        </div>
      </div>
      <div className="sbar">
        <div className={`sbar-fill ${cls}`} style={{ width: `${value}%` }} />
      </div>
    </div>
  )
}

/* ── Gap Card ────────────────────────────────────────────── */
export function GapCard({ gap, open, onToggle }) {
  const borderCls = gap.severity === 'high' || gap.severity === 'critical' ? 'gap-high'
    : gap.severity === 'medium' ? 'gap-medium' : 'gap-low'
  const badgeCls = gap.severity === 'high' || gap.severity === 'critical' ? 'badge-high'
    : gap.severity === 'medium' ? 'badge-medium' : 'badge-low'
  const hasAI = !!(gap.ai_analysis || gap.ai_recommendation)

  return (
    <article className={`gap-card ${borderCls}`} onClick={onToggle}>
      <div style={{ display: 'flex', gap: 6, alignItems: 'center', marginBottom: 5 }}>
        <span className={`badge ${badgeCls}`}>{gap.severity.toUpperCase()}</span>
        {hasAI && <span className="badge badge-ai"><i className="ti ti-sparkles" style={{ fontSize: 10 }} aria-hidden="true" /> AI</span>}
        <span style={{ fontSize: 12, color: 'var(--text-secondary)' }}>{gap.category}</span>
        <i className={`ti ti-chevron-${open ? 'up' : 'down'}`} style={{ marginLeft: 'auto', fontSize: 14, color: 'var(--text-secondary)' }} aria-hidden="true" />
      </div>

      <p style={{ fontSize: 13, lineHeight: 1.5, color: 'var(--text-primary)' }}>{gap.description}</p>

      {open && (
        <div style={{ marginTop: 8 }}>
          {hasAI ? (
            <div className="ai-block">
              {gap.ai_analysis && (
                <div style={{ marginBottom: gap.ai_recommendation ? 8 : 0 }}>
                  <p style={{ fontSize: 11, fontWeight: 500, color: '#3C3489', marginBottom: 4 }}>
                    <i className="ti ti-brain" style={{ fontSize: 11, marginRight: 4 }} aria-hidden="true" />
                    AI analysis
                  </p>
                  <p style={{ fontSize: 13, lineHeight: 1.6, color: '#534AB7' }}>{gap.ai_analysis}</p>
                </div>
              )}
              {gap.ai_recommendation && (
                <div>
                  <p style={{ fontSize: 11, fontWeight: 500, color: '#3C3489', marginBottom: 4 }}>
                    <i className="ti ti-arrow-right-circle" style={{ fontSize: 11, marginRight: 4 }} aria-hidden="true" />
                    AI recommendation
                  </p>
                  <p style={{ fontSize: 13, lineHeight: 1.6, color: '#534AB7' }}>{gap.ai_recommendation}</p>
                </div>
              )}
            </div>
          ) : (
            <p style={{ fontSize: 13, color: 'var(--text-secondary)', marginTop: 4 }}>
              <i className="ti ti-arrow-right" style={{ marginRight: 3 }} aria-hidden="true" />
              {gap.recommendation}
            </p>
          )}
          {gap.provenance && (
            <div className="mono" style={{ fontSize: 11, color: 'var(--text-secondary)', marginTop: 6 }}>
              source: {gap.provenance.derived_from.join(', ')} · {gap.provenance.method} · {Math.round(gap.provenance.confidence * 100)}% conf
            </div>
          )}
        </div>
      )}

      {!open && (
        <p style={{ fontSize: 12, color: hasAI ? '#534AB7' : 'var(--text-secondary)', marginTop: 4 }}>
          {hasAI
            ? <><i className="ti ti-sparkles" style={{ fontSize: 11, marginRight: 3 }} aria-hidden="true" />
                {(gap.ai_recommendation || gap.ai_analysis || '').slice(0, 110)}…</>
            : <><i className="ti ti-arrow-right" style={{ fontSize: 11, marginRight: 3 }} aria-hidden="true" />
                {(gap.recommendation || '').slice(0, 110)}</>
          }
        </p>
      )}
    </article>
  )
}

/* ── Loading spinner ─────────────────────────────────────── */
export function Spinner({ label = 'Loading…' }) {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', padding: '3rem', gap: 12 }}>
      <div style={{
        width: 32, height: 32, border: '3px solid #E2E8F0',
        borderTopColor: '#0F2240', borderRadius: '50%',
        animation: 'spin 0.7s linear infinite',
      }} />
      <p style={{ fontSize: 13, color: 'var(--text-secondary)' }}>{label}</p>
      <style>{`@keyframes spin { to { transform: rotate(360deg) } }`}</style>
    </div>
  )
}

/* ── Empty state ─────────────────────────────────────────── */
export function Empty({ icon = 'ti-mood-empty', label = 'Nothing here yet' }) {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', padding: '3rem', gap: 10, color: 'var(--text-secondary)' }}>
      <i className={`ti ${icon}`} style={{ fontSize: 38, opacity: .3 }} aria-hidden="true" />
      <p style={{ fontSize: 13 }}>{label}</p>
    </div>
  )
}

/* ── Error state ─────────────────────────────────────────── */
export function ErrorBox({ message, onRetry }) {
  return (
    <div style={{ background: '#FEF2F2', border: '0.5px solid #FECACA', borderRadius: 8, padding: '1rem', margin: '1rem' }}>
      <p style={{ color: '#991B1B', fontWeight: 500, marginBottom: 4 }}>Something went wrong</p>
      <p style={{ fontSize: 13, color: '#991B1B' }}>{message}</p>
      {onRetry && (
        <button onClick={onRetry} className="btn-ghost" style={{ marginTop: 8, fontSize: 12 }}>
          <i className="ti ti-refresh" aria-hidden="true" /> Try again
        </button>
      )}
    </div>
  )
}
