import { useState } from 'react'
import { GapCard, Spinner, Empty, ErrorBox } from '../components/ui'

const SEV_ORDER = { critical: 0, high: 1, medium: 2, low: 3 }

export default function GapsPage({ caseData, loading, error, refresh }) {
  const [openId, setOpenId]   = useState(null)
  const [filter, setFilter]   = useState('ALL')

  if (loading) return <Spinner label="Loading gaps…" />
  if (error)   return <ErrorBox message={error} onRetry={refresh} />

  const allGaps = caseData?.investigation_gaps ?? []
  const counts  = allGaps.reduce((a, g) => ({ ...a, [g.severity]: (a[g.severity] || 0) + 1 }), {})
  const aiCount = allGaps.filter(g => g.ai_analysis || g.ai_recommendation).length

  const visible = (filter === 'ALL' ? allGaps : allGaps.filter(g => g.severity === filter.toLowerCase()))
    .sort((a, b) => (SEV_ORDER[a.severity] ?? 9) - (SEV_ORDER[b.severity] ?? 9))

  if (!allGaps.length) return <Empty icon="ti-check" label="No investigation gaps detected — case looks clean." />

  return (
    <div>
      {/* Header stats */}
      <div style={{ display: 'flex', gap: 10, marginBottom: 12, flexWrap: 'wrap' }}>
        {[
          { v: allGaps.length, label: 'total gaps', col: 'var(--text-primary)' },
          { v: counts.high ?? 0, label: 'high severity', col: '#DC2626' },
          { v: counts.medium ?? 0, label: 'medium severity', col: '#D97706' },
          { v: aiCount, label: 'AI-enriched', col: '#534AB7' },
        ].map(({ v, label, col }) => (
          <div key={label} className="card card-sm" style={{ flex: 1, minWidth: 100 }}>
            <div className="mono" style={{ fontSize: 22, fontWeight: 500, color: col }}>{v}</div>
            <div style={{ fontSize: 12, color: 'var(--text-secondary)', marginTop: 1 }}>{label}</div>
          </div>
        ))}
      </div>

      {/* Filter tabs */}
      <div style={{ display: 'flex', borderBottom: '0.5px solid var(--border)', marginBottom: 12, gap: 2 }}>
        {[
          ['ALL', `All (${allGaps.length})`],
          ['HIGH', `High (${counts.high ?? 0})`],
          ['MEDIUM', `Medium (${counts.medium ?? 0})`],
          ['LOW', `Low (${counts.low ?? 0})`],
        ].map(([val, label]) => (
          <button key={val} className={`tab-btn${filter === val ? ' active' : ''}`} onClick={() => setFilter(val)}>
            {label}
          </button>
        ))}
      </div>

      {/* Gap cards */}
      {visible.map(g => (
        <GapCard
          key={g.id}
          gap={g}
          open={openId === g.id}
          onToggle={() => setOpenId(openId === g.id ? null : g.id)}
        />
      ))}
    </div>
  )
}
