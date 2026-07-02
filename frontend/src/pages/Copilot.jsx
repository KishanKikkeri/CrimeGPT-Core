import { Spinner, ErrorBox } from '../components/ui'

const SEV_ORDER = { critical: 0, high: 1, medium: 2, low: 3 }

export default function CopilotPage({ caseData, loading, error, refresh }) {
  if (loading) return <Spinner label="Generating copilot analysis…" />
  if (error)   return <ErrorBox message={error} onRetry={refresh} />

  const gaps   = caseData?.investigation_gaps ?? []
  const legal  = caseData?.legal_analysis
  const health = caseData?.health ?? {}
  const highGaps = gaps.filter(g => g.severity === 'high' || g.severity === 'critical')
  const score  = health.overall ?? 0

  // Build priority actions from gaps, sorted by severity
  const priorityActions = [...gaps]
    .sort((a, b) => (SEV_ORDER[a.severity] ?? 9) - (SEV_ORDER[b.severity] ?? 9))
    .slice(0, 6)
    .map((g, i) => ({
      n: i + 1,
      text: g.ai_recommendation || g.recommendation,
      severity: g.severity,
      timing: g.severity === 'critical' || g.severity === 'high' ? 'Immediate' : g.severity === 'medium' ? 'Within 48 hr' : 'Before review',
    }))

  return (
    <div>
      {/* AI Summary */}
      <div className="card" style={{ marginBottom: 12 }}>
        <div style={{ display: 'flex', gap: 10, alignItems: 'center', marginBottom: 12 }}>
          <div style={{ width: 34, height: 34, borderRadius: 8, background: '#EEEDFE', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
            <i className="ti ti-brain" style={{ fontSize: 18, color: '#534AB7' }} aria-hidden="true" />
          </div>
          <div>
            <p style={{ fontWeight: 500 }}>AI investigation summary</p>
            <p style={{ fontSize: 12, color: 'var(--text-secondary)' }}>Claude Sonnet 4.6 · Generated from full case analysis</p>
          </div>
        </div>

        <div style={{ background: 'var(--gray-100)', borderRadius: 8, padding: '1rem', marginBottom: 12 }}>
          {gaps.length > 0 ? (
            <p style={{ fontSize: 14, lineHeight: 1.7 }}>
              The {caseData?.title || 'case'} investigation contains <strong>{highGaps.length} high-severity evidentiary risks</strong> and {gaps.length - highGaps.length} additional issues.
              {score < 70 && ' The case cannot advance to legal review in its current state.'}
              {health.evidence_integrity < 50 && ' Chain-of-custody documentation is missing for multiple evidence items, rendering physical evidence potentially inadmissible.'}
              {gaps.some(g => g.category === 'timeline_contradiction') && ' A timeline contradiction has been detected that creates a direct cross-examination vulnerability.'}
            </p>
          ) : (
            <p style={{ fontSize: 14, lineHeight: 1.7 }}>
              The case appears well-structured with no critical gaps detected. Case Readiness is {score}%.
              {legal?.statutes?.length > 0 && ` Relevant statutes: ${legal.statutes.slice(0, 2).join(', ')}.`}
            </p>
          )}
        </div>

        <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
          <span className="badge badge-ai">
            <i className="ti ti-sparkles" style={{ fontSize: 10 }} aria-hidden="true" /> Case readiness: {score}%
          </span>
          {highGaps.length > 0 && <span className="badge badge-high">{highGaps.length} high-severity gaps</span>}
          {legal?.statutes?.length > 0 && <span className="badge badge-info">{legal.statutes.length} statutes identified</span>}
        </div>
      </div>

      {/* Priority actions */}
      {priorityActions.length > 0 && (
        <div className="card" style={{ marginBottom: 12 }}>
          <p style={{ fontWeight: 500, marginBottom: 12 }}>Priority actions</p>
          {priorityActions.map(({ n, text, severity, timing }) => (
            <div key={n} style={{ display: 'flex', gap: 12, alignItems: 'flex-start', padding: '9px 0', borderBottom: '0.5px solid var(--border)' }}>
              <div style={{
                width: 26, height: 26, borderRadius: '50%',
                background: 'var(--gray-100)',
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                flexShrink: 0, fontSize: 12, fontWeight: 500, color: 'var(--text-secondary)',
                fontFamily: 'var(--font-mono)',
              }}>{n}</div>
              <div style={{ flex: 1 }}>
                <p style={{ fontSize: 13, lineHeight: 1.5, marginBottom: 4 }}>{text}</p>
                <div style={{ display: 'flex', gap: 6 }}>
                  <span className={`badge badge-${severity === 'high' || severity === 'critical' ? 'high' : severity === 'medium' ? 'medium' : 'low'}`}>
                    {severity.toUpperCase()}
                  </span>
                  <span style={{ fontSize: 11, color: 'var(--text-secondary)' }}>{timing}</span>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Legal exposure */}
      <div className="card">
        <p style={{ fontWeight: 500, marginBottom: 10 }}>Legal exposure summary</p>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
          {[
            { label: 'Applicable statutes', v: legal?.statutes?.length ? legal.statutes[0] : 'Not yet analysed', icon: 'ti-scale', col: 'var(--text-primary)' },
            { label: 'Inadmissible evidence', v: `${(caseData?.evidence ?? []).filter(e => e.admissibility_status !== 'admissible').length} of ${(caseData?.evidence ?? []).length}`, icon: 'ti-x', col: '#DC2626' },
            { label: 'Compliance issues', v: `${(caseData?.compliance_findings ?? []).filter(f => f.severity === 'high').length} HIGH`, icon: 'ti-alert-circle', col: '#D97706' },
            { label: 'Case readiness', v: `${score}%`, icon: 'ti-chart-bar', col: score >= 75 ? '#16A34A' : score >= 55 ? '#D97706' : '#DC2626' },
          ].map(({ label, v, icon, col }) => (
            <div key={label} style={{ display: 'flex', gap: 10, alignItems: 'center', padding: '10px', background: 'var(--gray-100)', borderRadius: 8 }}>
              <i className={`ti ${icon}`} style={{ fontSize: 20, color: col, flexShrink: 0 }} aria-hidden="true" />
              <div>
                <p style={{ fontSize: 13, fontWeight: 500, color: col }}>{v}</p>
                <p style={{ fontSize: 11, color: 'var(--text-secondary)' }}>{label}</p>
              </div>
            </div>
          ))}
        </div>
        {legal?.statutes?.length > 0 && (
          <div style={{ marginTop: 12, paddingTop: 12, borderTop: '0.5px solid var(--border)' }}>
            <p style={{ fontSize: 12, color: 'var(--text-secondary)', marginBottom: 6 }}>All applicable statutes</p>
            {legal.statutes.map(s => (
              <div key={s} style={{ display: 'flex', gap: 8, padding: '5px 0', fontSize: 13 }}>
                <i className="ti ti-scale" style={{ color: 'var(--text-secondary)', marginTop: 2, flexShrink: 0, fontSize: 14 }} aria-hidden="true" />
                {s}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
