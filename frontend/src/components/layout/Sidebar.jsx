import { NavLink } from 'react-router-dom'

const NAV = [
  { to: 'dashboard',  icon: 'ti-layout-dashboard',   label: 'Dashboard' },
  { to: 'gaps',       icon: 'ti-alert-circle',        label: 'Investigation gaps' },
  { to: 'timeline',   icon: 'ti-timeline',            label: 'Timeline' },
  { to: 'copilot',    icon: 'ti-brain',               label: 'AI copilot' },
  { to: 'evidence',   icon: 'ti-topology-ring',       label: 'Evidence board' },
  { to: 'reports',    icon: 'ti-file-description',    label: 'Reports' },
]

export default function Sidebar({ caseData }) {
  return (
    <aside style={{ width: 210, background: '#0F2240', display: 'flex', flexDirection: 'column', flexShrink: 0 }}>
      {/* Logo */}
      <div style={{ padding: '18px 14px 14px', borderBottom: '0.5px solid rgba(255,255,255,.1)', display: 'flex', alignItems: 'center', gap: 10 }}>
        <div style={{ width: 30, height: 30, borderRadius: 6, background: '#F59E0B', display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0 }}>
          <i className="ti ti-shield-search" style={{ color: '#0F2240', fontSize: 16 }} aria-hidden="true" />
        </div>
        <span style={{ color: '#fff', fontSize: 15, fontWeight: 500 }}>CrimeGPT</span>
      </div>

      {/* Active case */}
      <div style={{ padding: '10px 14px', borderBottom: '0.5px solid rgba(255,255,255,.1)' }}>
        <div style={{ fontSize: 10, color: 'rgba(255,255,255,.4)', textTransform: 'uppercase', letterSpacing: '.06em', marginBottom: 3 }}>
          Active case
        </div>
        <div style={{ fontSize: 12, color: 'rgba(255,255,255,.8)', lineHeight: 1.4 }}>
          {caseData?.title || 'Loading…'}
        </div>
        <div className="mono" style={{ fontSize: 10, color: 'rgba(255,255,255,.35)', marginTop: 2 }}>
          {caseData?.case_id || '—'}
        </div>
      </div>

      {/* Navigation */}
      <nav style={{ flex: 1, padding: '6px 0' }}>
        {NAV.map(({ to, icon, label }) => (
          <NavLink
            key={to}
            to={to}
            style={({ isActive }) => ({
              display: 'flex', alignItems: 'center', gap: 10,
              padding: '9px 14px', textDecoration: 'none',
              background: isActive ? 'rgba(255,255,255,.11)' : 'transparent',
              borderLeft: `2px solid ${isActive ? '#F59E0B' : 'transparent'}`,
            })}
          >
            {({ isActive }) => (
              <>
                <i className={`ti ${icon}`} style={{ fontSize: 15, color: isActive ? '#fff' : 'rgba(255,255,255,.5)' }} aria-hidden="true" />
                <span style={{ fontSize: 13, color: isActive ? '#fff' : 'rgba(255,255,255,.6)' }}>{label}</span>
              </>
            )}
          </NavLink>
        ))}
      </nav>

      {/* Footer */}
      <div style={{ padding: '10px 14px', borderTop: '0.5px solid rgba(255,255,255,.1)' }}>
        <div style={{ fontSize: 11, color: 'rgba(255,255,255,.3)' }}>CrimeGPT v0.1.0</div>
        <div style={{ fontSize: 11, color: 'rgba(255,255,255,.3)', marginTop: 1 }}>Claude Sonnet 4.6</div>
      </div>
    </aside>
  )
}
