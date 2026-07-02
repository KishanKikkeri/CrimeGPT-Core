import { useState, useMemo } from 'react'
import { Spinner, Empty, ErrorBox } from '../components/ui'

const TYPE_COLOR = {
  physical: '#6D7280', digital: '#1E3A5F', document: '#0F766E',
  cctv: '#1E3A5F', photo: '#D97706', audio: '#7C3AED',
  forensic: '#0E7490', other: '#6D7280',
}
const SUSPECT_COL = '#DC2626'
const WITNESS_COL = '#6D28D9'
const VICTIM_COL  = '#0F766E'

function positionNodes(caseData) {
  const nodes = []
  const edges = []
  const pos = {}

  // Layout: suspects in centre, evidence top, witnesses left, victims right
  const suspects  = caseData?.suspects  ?? []
  const witnesses = caseData?.witnesses ?? []
  const evidence  = caseData?.evidence  ?? []
  const victims   = caseData?.victims   ?? []

  // Suspects — centre
  suspects.forEach((s, i) => {
    const x = 260 + i * 100
    const y = 160
    pos[s.id] = { x, y }
    nodes.push({ id: s.id, x, y, r: 26, label: s.id, sub: s.status, fill: SUSPECT_COL })
  })

  // Evidence — top arc
  evidence.forEach((e, i) => {
    const angle = (Math.PI / (evidence.length + 1)) * (i + 1)
    const x = 80 + i * (400 / Math.max(evidence.length - 1, 1))
    const y = 55
    pos[e.evidence_id] = { x, y }
    nodes.push({ id: e.evidence_id, x, y, r: 19, label: e.evidence_id, sub: e.type, fill: TYPE_COLOR[e.type] || '#6D7280' })
    e.linked_people?.forEach(pid => {
      if (pos[pid]) edges.push({ a: e.evidence_id, b: pid, col: TYPE_COLOR[e.type] || '#94A3B8', dash: e.chain_of_custody?.length === 0 ? '4,3' : null })
    })
  })

  // Witnesses — left
  witnesses.forEach((w, i) => {
    const x = 55
    const y = 100 + i * 90
    pos[w.id] = { x, y }
    nodes.push({ id: w.id, x, y, r: 18, label: w.id, sub: w.name ? w.name.split(' ')[0] : 'Anonymous', fill: WITNESS_COL })
    // Connect witnesses to timeline events they're linked to (simplified: connect to suspects)
    suspects.forEach(s => {
      if (pos[s.id]) edges.push({ a: w.id, b: s.id, col: WITNESS_COL, dash: !w.contact ? '4,3' : null })
    })
  })

  // Victims — right
  victims.forEach((v, i) => {
    const x = 480
    const y = 120 + i * 80
    pos[v.id] = { x, y }
    nodes.push({ id: v.id, x, y, r: 18, label: v.id, sub: v.name?.split(' ')[0] || 'Victim', fill: VICTIM_COL })
  })

  return { nodes, edges, pos }
}

export default function EvidencePage({ caseData, loading, error, refresh }) {
  const [selected, setSelected] = useState(null)

  if (loading) return <Spinner label="Building evidence board…" />
  if (error)   return <ErrorBox message={error} onRetry={refresh} />

  const evidence  = caseData?.evidence  ?? []
  const suspects  = caseData?.suspects  ?? []
  const witnesses = caseData?.witnesses ?? []

  if (!evidence.length && !suspects.length) return <Empty icon="ti-topology-ring" label="No evidence or entities to display yet." />

  const { nodes, edges, pos } = useMemo(() => positionNodes(caseData), [caseData])

  const selItem = selected
    ? ([...evidence, ...suspects, ...witnesses, ...(caseData?.victims ?? [])].find(
        x => (x.evidence_id || x.id) === selected
      ))
    : null

  const admissible  = evidence.filter(e => e.admissibility_status === 'admissible').length
  const noCustody   = evidence.filter(e => !e.chain_of_custody?.length).length

  return (
    <div style={{ display: 'grid', gridTemplateColumns: '1fr 280px', gap: 12, alignItems: 'start' }}>
      <div className="card">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
          <div>
            <p style={{ fontWeight: 500, marginBottom: 2 }}>Evidence connection board</p>
            <p style={{ fontSize: 13, color: 'var(--text-secondary)' }}>Click any node to inspect</p>
          </div>
          <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap' }}>
            {[
              { col: SUSPECT_COL, l: 'Suspect' },
              { col: WITNESS_COL, l: 'Witness' },
              { col: VICTIM_COL,  l: 'Victim' },
              { col: '#0E7490',   l: 'Forensic' },
              { col: '#1E3A5F',   l: 'Digital' },
              { col: '#6D7280',   l: 'Physical' },
            ].map(({ col, l }) => (
              <div key={l} style={{ display: 'flex', alignItems: 'center', gap: 4, fontSize: 11, color: 'var(--text-secondary)' }}>
                <div style={{ width: 8, height: 8, borderRadius: '50%', background: col }} />
                {l}
              </div>
            ))}
          </div>
        </div>

        <svg viewBox="0 0 540 290" width="100%" style={{ cursor: 'default' }}>
          {/* Edges */}
          {edges.map((e, i) => (
            pos[e.a] && pos[e.b] && (
              <line key={i}
                x1={pos[e.a].x} y1={pos[e.a].y}
                x2={pos[e.b].x} y2={pos[e.b].y}
                stroke={e.col} strokeWidth={e.w || 1}
                strokeDasharray={e.dash || undefined} opacity={0.7}
              />
            )
          ))}
          {/* Nodes */}
          {nodes.map(n => (
            <g key={n.id} transform={`translate(${n.x},${n.y})`}
              onClick={() => setSelected(selected === n.id ? null : n.id)}
              style={{ cursor: 'pointer' }}>
              <circle r={n.r} fill={n.fill} opacity={selected === n.id ? 1 : 0.85}
                stroke={selected === n.id ? '#F59E0B' : 'none'} strokeWidth={2} />
              <text textAnchor="middle" dy={4} fontSize={n.r > 18 ? 10 : 9} fill="white" fontWeight="500">
                {n.label}
              </text>
              <text textAnchor="middle" dy={n.r + 13} fontSize={10} fill="var(--text-secondary)">
                {n.sub}
              </text>
            </g>
          ))}
        </svg>

        {/* Legend */}
        <div style={{ display: 'flex', gap: 16, marginTop: 8 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 4, fontSize: 12, color: 'var(--text-secondary)' }}>
            <div style={{ width: 24, height: 1, borderTop: '2px dashed #CBD5E1' }} />
            No custody chain
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 4, fontSize: 12, color: 'var(--text-secondary)' }}>
            <div style={{ width: 24, height: 1, background: '#1E3A5F' }} />
            Confirmed link
          </div>
        </div>
      </div>

      {/* Detail panel */}
      <div className="card">
        {selItem ? (
          <>
            <p style={{ fontWeight: 500, marginBottom: 10 }}>Entity detail</p>
            <div className="mono" style={{ fontSize: 18, fontWeight: 500, marginBottom: 8 }}>
              {selItem.evidence_id || selItem.id}
            </div>
            {Object.entries({
              Type: selItem.type || selItem.status || '—',
              Title: selItem.title || selItem.name || selItem.description || '—',
              Source: selItem.source || '—',
              'Collected by': selItem.collected_by || '—',
              Admissibility: selItem.admissibility_status || '—',
              'Custody entries': selItem.chain_of_custody?.length ?? '—',
              Contact: selItem.contact || (selItem.id?.startsWith('W') ? 'None' : '—'),
            }).filter(([, v]) => v !== '—').map(([k, v]) => (
              <div key={k} style={{ display: 'flex', justifyContent: 'space-between', padding: '6px 0', borderBottom: '0.5px solid var(--border)', fontSize: 12 }}>
                <span style={{ color: 'var(--text-secondary)' }}>{k}</span>
                <span className="mono" style={{ fontWeight: 500, maxWidth: 140, textAlign: 'right', wordBreak: 'break-all' }}>{String(v)}</span>
              </div>
            ))}
            {selItem.chain_of_custody?.length === 0 && (
              <div style={{ marginTop: 10, background: '#FEF2F2', borderRadius: 6, padding: '8px 10px' }}>
                <p style={{ fontSize: 12, color: '#DC2626', fontWeight: 500 }}>⚠ No chain-of-custody</p>
                <p style={{ fontSize: 12, color: '#DC2626' }}>This evidence item is currently not admissible.</p>
              </div>
            )}
          </>
        ) : (
          <>
            <p style={{ fontWeight: 500, marginBottom: 12 }}>Evidence summary</p>
            {[
              { label: 'Total items', v: evidence.length, col: 'var(--text-primary)' },
              { label: 'Admissible', v: admissible, col: '#16A34A' },
              { label: 'Missing custody chain', v: noCustody, col: '#DC2626' },
              { label: 'Suspects', v: suspects.length, col: SUSPECT_COL },
              { label: 'Witnesses', v: witnesses.length, col: WITNESS_COL },
            ].map(({ label, v, col }) => (
              <div key={label} style={{ display: 'flex', justifyContent: 'space-between', padding: '7px 0', borderBottom: '0.5px solid var(--border)', fontSize: 13 }}>
                <span style={{ color: 'var(--text-secondary)' }}>{label}</span>
                <span className="mono" style={{ fontWeight: 500, color: col }}>{v}</span>
              </div>
            ))}
            <p style={{ fontSize: 12, color: 'var(--text-secondary)', marginTop: 14 }}>Click a node to inspect it</p>
          </>
        )}
      </div>
    </div>
  )
}
