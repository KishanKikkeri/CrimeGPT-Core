import { useState } from 'react'
import { Spinner, Empty, ErrorBox } from '../components/ui'

function fmtTime(ts) {
  if (!ts) return '??:??'
  try {
    const d = new Date(ts)
    return d.toTimeString().slice(0, 5)
  } catch { return '??:??' }
}

function hasContradiction(events, event) {
  if (!event.timestamp) return false
  const evTime = new Date(event.timestamp)
  return events.some(other => {
    if (other.event_id === event.event_id || !other.timestamp) return false
    const shared = event.linked_people.filter(p => other.linked_people.includes(p))
    if (!shared.length) return false
    const diff = Math.abs(new Date(other.timestamp) - evTime) / 60000
    return diff > 5
  })
}

export default function TimelinePage({ caseData, loading, error, refresh }) {
  const [selected, setSelected] = useState(null)

  if (loading) return <Spinner label="Building timeline…" />
  if (error)   return <ErrorBox message={error} onRetry={refresh} />

  const events = caseData?.timeline ?? []
  if (!events.length) return <Empty icon="ti-clock" label="No timeline events yet." />

  const contradiction = events.filter(e => hasContradiction(events, e))
  const contraIds = new Set(contradiction.map(e => e.event_id))

  const sel = selected ? events.find(e => e.event_id === selected) : null

  return (
    <div style={{ display: 'grid', gridTemplateColumns: '1fr 320px', gap: 12, alignItems: 'start' }}>
      <div className="card">
        <div style={{ marginBottom: 12, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <div>
            <p style={{ fontWeight: 500, marginBottom: 2 }}>Investigation timeline</p>
            <p style={{ fontSize: 13, color: 'var(--text-secondary)' }}>
              {events.length} events · {contraIds.size} contradiction marker{contraIds.size !== 1 ? 's' : ''}
            </p>
          </div>
          {contraIds.size > 0 && (
            <span className="badge badge-high">
              <i className="ti ti-alert-triangle" style={{ fontSize: 10 }} aria-hidden="true" />
              {contraIds.size} contradiction
            </span>
          )}
        </div>

        {events.map((ev, i) => {
          const isWarn = contraIds.has(ev.event_id)
          const isSelected = selected === ev.event_id
          const showContra = isWarn && i > 0 && !contraIds.has(events[i-1]?.event_id)

          return (
            <div key={ev.event_id}>
              {showContra && (
                <div className="contra-banner">
                  <i className="ti ti-alert-triangle" style={{ marginRight: 5, fontSize: 13 }} aria-hidden="true" />
                  Timeline contradiction detected — timestamps for the same subject are inconsistent
                </div>
              )}

              <div
                style={{ display: 'flex', gap: 12, alignItems: 'flex-start', cursor: 'pointer', borderRadius: 6, padding: '2px 6px', background: isSelected ? '#EFF6FF' : 'transparent' }}
                onClick={() => setSelected(isSelected ? null : ev.event_id)}
              >
                <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', paddingTop: 3 }}>
                  <div className={`tl-dot${isWarn ? ' tl-dot-warn' : ''}`} />
                  {i < events.length - 1 && <div className="tl-line" />}
                </div>

                <div style={{ paddingBottom: 12, flex: 1 }}>
                  <div style={{ display: 'flex', gap: 8, alignItems: 'baseline' }}>
                    <span className="mono" style={{ fontSize: 13, fontWeight: 500 }}>{fmtTime(ev.timestamp)}</span>
                    <span className="mono" style={{ fontSize: 11, color: 'var(--text-secondary)' }}>{ev.event_id}</span>
                    {isWarn && <span className="badge badge-high" style={{ fontSize: 10, padding: '1px 6px' }}>contradiction</span>}
                  </div>
                  <p style={{ fontSize: 13, color: 'var(--text-secondary)', marginTop: 2, lineHeight: 1.5 }}>{ev.description}</p>
                  <span className="mono" style={{ fontSize: 11, color: 'var(--text-secondary)' }}>
                    {ev.source} · {Math.round((ev.confidence ?? 0) * 100)}% conf
                  </span>
                </div>
              </div>
            </div>
          )
        })}
      </div>

      {/* Detail panel */}
      <div className="card">
        {sel ? (
          <>
            <p style={{ fontWeight: 500, marginBottom: 10 }}>Event detail</p>
            <div className="mono" style={{ fontSize: 22, fontWeight: 500, marginBottom: 2 }}>{fmtTime(sel.timestamp)}</div>
            <p style={{ fontSize: 11, color: 'var(--text-secondary)', marginBottom: 12 }}>{sel.event_id}</p>
            <p style={{ fontSize: 13, lineHeight: 1.6, marginBottom: 12 }}>{sel.description}</p>
            {[
              { label: 'Source', value: sel.source },
              { label: 'Confidence', value: `${Math.round((sel.confidence ?? 0) * 100)}%` },
              { label: 'Linked people', value: sel.linked_people?.join(', ') || '—' },
              { label: 'Linked evidence', value: sel.linked_evidence?.join(', ') || '—' },
            ].map(({ label, value }) => (
              <div key={label} style={{ display: 'flex', justifyContent: 'space-between', padding: '7px 0', borderBottom: '0.5px solid var(--border)', fontSize: 13 }}>
                <span style={{ color: 'var(--text-secondary)' }}>{label}</span>
                <span className="mono" style={{ fontWeight: 500 }}>{value}</span>
              </div>
            ))}
            {contraIds.has(sel.event_id) && (
              <div style={{ marginTop: 12, background: '#FEF2F2', borderRadius: 6, padding: '8px 10px' }}>
                <p style={{ fontSize: 12, color: '#DC2626', fontWeight: 500, marginBottom: 3 }}>⚠ Contradiction detected</p>
                <p style={{ fontSize: 12, color: '#DC2626' }}>This event's timestamp conflicts with another event involving the same subject.</p>
              </div>
            )}
          </>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', padding: '2rem', color: 'var(--text-secondary)' }}>
            <i className="ti ti-hand-click" style={{ fontSize: 32, opacity: .3, marginBottom: 10 }} aria-hidden="true" />
            <p style={{ fontSize: 13 }}>Click an event to inspect it</p>
          </div>
        )}
      </div>
    </div>
  )
}
