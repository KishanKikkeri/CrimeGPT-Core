import { useState, useMemo } from 'react'
import { useNavigate } from 'react-router-dom'
import { Gauge, ScoreBar, Spinner, ErrorBox } from '../components/ui'

const WEIGHTS = { completeness: 0.35, evidence_integrity: 0.25, legal_readiness: 0.20, documentation_quality: 0.20 }

function calcSimScore(health, fixes) {
  const e = fixes.custody ? 85 : health.evidence_integrity
  const l = fixes.custody ? 75 : (fixes.forensic ? 50 : health.legal_readiness)
  const d = health.documentation_quality + (fixes.forensic ? 5 : 0) + (fixes.witness ? 5 : 0)
  return Math.round(100 * 0.35 + e * 0.25 + l * 0.20 + Math.min(100, d) * 0.20)
}

export default function DashboardPage({ caseData, loading, error, refresh }) {
  const navigate = useNavigate()
  const [fixes, setFixes] = useState({ custody: false, forensic: false, witness: false })
  const toggle = k => setFixes(f => ({ ...f, [k]: !f[k] }))

  const health = caseData?.health || { completeness: 0, evidence_integrity: 0, legal_readiness: 0, documentation_quality: 0 }
  const simScore = useMemo(() => calcSimScore(health, fixes), [health, fixes])
  const anyFix = Object.values(fixes).some(Boolean)
  const displayScore = anyFix ? simScore : (health.overall ?? 0)

  const gaps = caseData?.investigation_gaps || []
  const highCount = gaps.filter(g => g.severity === 'high' || g.severity === 'critical').length
  const medCount  = gaps.filter(g => g.severity === 'medium').length

  if (loading) return <Spinner label="Loading case…" />
  if (error)   return <ErrorBox message={error} onRetry={refresh} />

  const METRICS = [
    { label: 'Victims', v: caseData?.victims?.length ?? 0, icon: 'ti-user', col: 'var(--text-primary)' },
    { label: 'Witnesses', v: caseData?.witnesses?.length ?? 0, icon: 'ti-users', col: 'var(--text-primary)' },
    { label: 'Evidence items', v: caseData?.evidence?.length ?? 0, icon: 'ti-package', col: 'var(--text-primary)' },
    { label: 'Timeline events', v: caseData?.timeline?.length ?? 0, icon: 'ti-clock', col: 'var(--text-primary)' },
    { label: 'HIGH gaps', v: highCount, icon: 'ti-alert-triangle', col: '#DC2626', click: () => navigate('../gaps') },
    { label: 'MEDIUM gaps', v: medCount, icon: 'ti-alert-circle', col: '#D97706', click: () => navigate('../gaps') },
  ]

  const SIMS = [
    { k: 'custody', label: 'Complete custody chains', sub: 'EV-001, EV-003, EV-004', imp: '+22%', icon: 'ti-link' },
    { k: 'forensic', label: 'Attach forensic report', sub: 'EV-001 fingerprint analysis', imp: '+3%', icon: 'ti-microscope' },
    { k: 'witness', label: 'Identify witness W2', sub: 'Anonymous passerby contact', imp: '+1%', icon: 'ti-user-question' },
  ]

  return (
    <div>
      {/* Top row: gauge + metrics */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12, marginBottom: 12 }}>
        <div className="card" style={{ display: 'flex', gap: 18, alignItems: 'center' }}>
          <Gauge score={displayScore} size={136} />
          <div style={{ flex: 1 }}>
            <p style={{ fontSize: 12, color: 'var(--text-secondary)', marginBottom: 10 }}>Score breakdown</p>
            <ScoreBar label="Completeness" value={health.completeness} weight={WEIGHTS.completeness} />
            <ScoreBar label="Evidence integrity" value={anyFix && fixes.custody ? 85 : health.evidence_integrity} weight={WEIGHTS.evidence_integrity} />
            <ScoreBar label="Legal readiness" value={anyFix && fixes.custody ? 75 : (anyFix && fixes.forensic ? 50 : health.legal_readiness)} weight={WEIGHTS.legal_readiness} />
            <ScoreBar label="Documentation quality" value={Math.min(100, health.documentation_quality + (fixes.forensic ? 5 : 0) + (fixes.witness ? 5 : 0))} weight={WEIGHTS.documentation_quality} />
          </div>
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8, alignContent: 'start' }}>
          {METRICS.map(({ label, v, icon, col, click }) => (
            <div key={label} className="stat-box" onClick={click} style={{ cursor: click ? 'pointer' : 'default' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                <div>
                  <div className="stat-num" style={{ color: col }}>{v}</div>
                  <div style={{ fontSize: 12, color: 'var(--text-secondary)', marginTop: 2 }}>{label}</div>
                </div>
                <i className={`ti ${icon}`} style={{ fontSize: 18, color: col, opacity: .4 }} aria-hidden="true" />
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Simulation panel */}
      <div className="card">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 14 }}>
          <div>
            <p style={{ fontWeight: 500, marginBottom: 3 }}>What happens if…</p>
            <p style={{ fontSize: 13, color: 'var(--text-secondary)' }}>Toggle fixes to see real-time readiness impact</p>
          </div>
          <div style={{ textAlign: 'right' }}>
            <div className="mono" style={{ fontSize: 26, fontWeight: 500, color: displayScore >= 75 ? '#16A34A' : displayScore >= 55 ? '#D97706' : '#DC2626' }}>
              {displayScore}%
            </div>
            <div style={{ fontSize: 12, color: 'var(--text-secondary)', marginTop: 1 }}>
              {anyFix ? `+${displayScore - (health.overall ?? 0)}% projected` : 'current baseline'}
            </div>
          </div>
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 10 }}>
          {SIMS.map(({ k, label, sub, imp, icon }) => (
            <div key={k} className={`sim-card${fixes[k] ? ' on' : ''}`} onClick={() => toggle(k)}>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 8 }}>
                <div style={{
                  width: 16, height: 16, borderRadius: 4,
                  border: `2px solid ${fixes[k] ? '#16A34A' : '#CBD5E1'}`,
                  display: 'flex', alignItems: 'center', justifyContent: 'center',
                }}>
                  {fixes[k] && <i className="ti ti-check" style={{ fontSize: 11, color: '#16A34A' }} aria-hidden="true" />}
                </div>
                <span className="mono" style={{ fontSize: 12, fontWeight: 500, color: '#16A34A' }}>{imp}</span>
              </div>
              <i className={`ti ${icon}`} style={{ fontSize: 20, color: 'var(--text-secondary)', marginBottom: 4, display: 'block' }} aria-hidden="true" />
              <p style={{ fontSize: 13, fontWeight: 500, marginBottom: 2 }}>{label}</p>
              <p style={{ fontSize: 12, color: 'var(--text-secondary)' }}>{sub}</p>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
