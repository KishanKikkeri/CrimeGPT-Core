import { useState } from 'react'
import { Spinner, ErrorBox } from '../components/ui'
import { generateReport } from '../services/api'

const REPORT_TYPES = [
  { v: 'investigation_report',       l: 'Investigation report',       d: 'Full structured case — people, timeline, evidence, gaps, legal', icon: 'ti-file-text' },
  { v: 'court_brief',                l: 'Court brief',                d: 'Admissible evidence + applicable law + open compliance issues', icon: 'ti-scale' },
  { v: 'case_summary',               l: 'Case summary',               d: 'Two-page overview with key findings and readiness score', icon: 'ti-clipboard-list' },
  { v: 'evidence_summary',           l: 'Evidence summary',           d: 'Evidence-focused with custody chain status per item', icon: 'ti-package' },
  { v: 'executive_intelligence_report', l: 'Executive intelligence brief', d: 'One-page readiness overview with priority actions', icon: 'ti-chart-bar' },
]

function fmtDate(iso) {
  if (!iso) return '—'
  return new Date(iso).toLocaleString('en-IN', { dateStyle: 'medium', timeStyle: 'short' })
}

export default function ReportsPage({ caseData, loading, error, refresh }) {
  const [rType,      setRType]      = useState('investigation_report')
  const [generating, setGenerating] = useState(false)
  const [genError,   setGenError]   = useState(null)
  const [preview,    setPreview]    = useState(null)

  if (loading) return <Spinner label="Loading reports…" />
  if (error)   return <ErrorBox message={error} onRetry={refresh} />

  const existing = caseData?.reports ?? []

  const handleGenerate = async () => {
    setGenerating(true)
    setGenError(null)
    try {
      const report = await generateReport(caseData.case_id, rType)
      setPreview(report)
      refresh()
    } catch (err) {
      setGenError(err.message)
    } finally {
      setGenerating(false)
    }
  }

  const handleDownload = (content, name) => {
    const blob = new Blob([content], { type: 'text/plain' })
    const url  = URL.createObjectURL(blob)
    const a    = document.createElement('a')
    a.href = url
    a.download = `${name}.txt`
    a.click()
    URL.revokeObjectURL(url)
  }

  return (
    <div>
      <div style={{ display: 'grid', gridTemplateColumns: '320px 1fr', gap: 12, alignItems: 'start' }}>
        {/* Left: type selector + existing reports */}
        <div>
          <div className="card" style={{ marginBottom: 12 }}>
            <p style={{ fontWeight: 500, marginBottom: 12 }}>Generate report</p>

            {REPORT_TYPES.map(r => (
              <div
                key={r.v}
                onClick={() => setRType(r.v)}
                style={{
                  display: 'flex', gap: 10, alignItems: 'flex-start',
                  padding: '10px', marginBottom: 6, cursor: 'pointer',
                  background: rType === r.v ? '#EFF6FF' : 'var(--gray-100)',
                  borderRadius: 8,
                  border: `0.5px solid ${rType === r.v ? '#BFDBFE' : 'var(--border)'}`,
                }}
              >
                <div style={{
                  width: 16, height: 16, borderRadius: '50%',
                  border: `2px solid ${rType === r.v ? '#1D4ED8' : '#CBD5E1'}`,
                  marginTop: 1, display: 'flex', alignItems: 'center',
                  justifyContent: 'center', flexShrink: 0,
                }}>
                  {rType === r.v && <div style={{ width: 7, height: 7, borderRadius: '50%', background: '#1D4ED8' }} />}
                </div>
                <div>
                  <p style={{ fontSize: 13, fontWeight: 500, marginBottom: 2 }}>{r.l}</p>
                  <p style={{ fontSize: 12, color: 'var(--text-secondary)' }}>{r.d}</p>
                </div>
              </div>
            ))}

            {genError && (
              <p style={{ fontSize: 12, color: '#DC2626', marginBottom: 8, padding: '6px 8px', background: '#FEF2F2', borderRadius: 6 }}>
                {genError}
              </p>
            )}

            <button
              className="btn-primary"
              onClick={handleGenerate}
              disabled={generating || !caseData}
              style={{ width: '100%', marginTop: 8, justifyContent: 'center', opacity: generating ? .7 : 1 }}
            >
              <i className={`ti ${generating ? 'ti-loader-2' : 'ti-file-download'}`}
                style={generating ? { animation: 'spin .6s linear infinite' } : {}}
                aria-hidden="true" />
              {generating ? 'Generating…' : 'Generate report'}
            </button>
            <style>{`@keyframes spin { to { transform: rotate(360deg) } }`}</style>
          </div>

          {/* Existing reports */}
          {existing.length > 0 && (
            <div className="card">
              <p style={{ fontWeight: 500, marginBottom: 10 }}>Previous reports</p>
              {existing.map(r => (
                <div key={r.report_id}
                  style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '8px 0', borderBottom: '0.5px solid var(--border)' }}>
                  <div>
                    <p style={{ fontSize: 13, fontWeight: 500 }}>{REPORT_TYPES.find(t => t.v === r.type)?.l || r.type}</p>
                    <p className="mono" style={{ fontSize: 11, color: 'var(--text-secondary)' }}>
                      v{r.version} · {fmtDate(r.generated_at)}
                    </p>
                  </div>
                  <button
                    className="btn-ghost"
                    style={{ padding: '4px 10px', fontSize: 12 }}
                    onClick={() => setPreview(r)}
                  >
                    <i className="ti ti-eye" style={{ fontSize: 13 }} aria-hidden="true" /> View
                  </button>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Right: preview */}
        <div className="card" style={{ minHeight: 400 }}>
          {preview ? (
            <>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
                <div>
                  <p style={{ fontWeight: 500, marginBottom: 2 }}>
                    {REPORT_TYPES.find(t => t.v === preview.type)?.l || preview.type}
                  </p>
                  <p className="mono" style={{ fontSize: 11, color: 'var(--text-secondary)' }}>
                    {preview.report_id} · v{preview.version}
                  </p>
                </div>
                <div style={{ display: 'flex', gap: 8 }}>
                  <span className="badge badge-active">
                    <i className="ti ti-check" style={{ fontSize: 10 }} aria-hidden="true" /> Generated
                  </span>
                  <button
                    className="btn-ghost"
                    style={{ padding: '5px 12px', fontSize: 12 }}
                    onClick={() => handleDownload(preview.content, preview.type)}
                  >
                    <i className="ti ti-download" style={{ fontSize: 13 }} aria-hidden="true" /> Download
                  </button>
                </div>
              </div>
              <pre style={{
                fontSize: 12, lineHeight: 1.7,
                whiteSpace: 'pre-wrap',
                fontFamily: 'var(--font-mono)',
                color: 'var(--text-secondary)',
                maxHeight: 520, overflowY: 'auto',
                background: 'var(--gray-100)',
                borderRadius: 8, padding: '1rem',
              }}>
                {preview.content}
              </pre>
            </>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', padding: '4rem', color: 'var(--text-secondary)', height: '100%' }}>
              <i className="ti ti-file-text" style={{ fontSize: 42, opacity: .25, marginBottom: 12 }} aria-hidden="true" />
              <p style={{ fontSize: 13 }}>Select a report type and click generate</p>
              <p style={{ fontSize: 12, marginTop: 4 }}>Available without re-running the full pipeline</p>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
