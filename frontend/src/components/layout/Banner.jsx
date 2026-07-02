import { useNavigate } from 'react-router-dom'

export default function Banner({ gaps = [] }) {
  const navigate = useNavigate()
  const critical = gaps.filter(g => g.severity === 'critical' || g.severity === 'high')
  if (!critical.length) return null

  const top = critical[0]

  return (
    <div style={{
      background: '#FEF2F2',
      borderBottom: '0.5px solid #FECACA',
      padding: '9px 14px',
      display: 'flex', alignItems: 'center', gap: 10,
      flexShrink: 0,
    }}>
      <div style={{ width: 7, height: 7, borderRadius: '50%', background: '#DC2626', flexShrink: 0 }} />
      <i className="ti ti-alert-triangle" style={{ fontSize: 15, color: '#DC2626', flexShrink: 0 }} aria-hidden="true" />
      <span style={{ fontSize: 13, color: '#DC2626', fontWeight: 500, flex: 1 }}>
        AI found {critical.length} critical issue{critical.length > 1 ? 's' : ''} — {top.description.slice(0, 110)}{top.description.length > 110 ? '…' : ''}
      </span>
      <button
        onClick={() => navigate('gaps')}
        style={{
          background: '#DC2626', color: '#fff',
          border: 'none', borderRadius: 6,
          padding: '4px 12px', fontSize: 12, cursor: 'pointer',
          fontWeight: 500, flexShrink: 0,
        }}
      >
        View analysis
      </button>
    </div>
  )
}
