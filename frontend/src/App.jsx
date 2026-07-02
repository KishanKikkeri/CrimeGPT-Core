import { Routes, Route, Navigate, useParams } from 'react-router-dom'
import Sidebar from './components/layout/Sidebar'
import Banner  from './components/layout/Banner'
import { useCase } from './hooks/useCase'
import DashboardPage from './pages/Dashboard'
import GapsPage      from './pages/Gaps'
import TimelinePage  from './pages/Timeline'
import CopilotPage   from './pages/Copilot'
import EvidencePage  from './pages/Evidence'
import ReportsPage   from './pages/Reports'

/* ── Demo case ID — auto-seeded by the backend on startup ── */
const DEMO_CASE_ID = import.meta.env.VITE_DEMO_CASE_ID || 'demo'

/* ── Page title map ─────────────────────────────────────── */
const PAGE_TITLE = {
  dashboard: 'Dashboard',
  gaps:      'Investigation gaps',
  timeline:  'Timeline',
  copilot:   'AI copilot',
  evidence:  'Evidence board',
  reports:   'Reports',
}

/* ── Case workspace: fetches the case and passes data down ─ */
function CaseWorkspace({ caseId }) {
  const { caseData, loading, error, refresh } = useCase(caseId)

  const gaps   = caseData?.investigation_gaps ?? []
  const active = window.location.pathname.split('/').pop() || 'dashboard'
  const title  = PAGE_TITLE[active] || 'Dashboard'

  const pageProps = { caseData, loading, error, refresh }

  return (
    <div style={{ display: 'flex', height: '100vh', overflow: 'hidden' }}>
      <Sidebar caseData={caseData} />

      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden', background: 'var(--bg)' }}>
        {/* Critical issue banner */}
        <Banner gaps={gaps} />

        {/* Page header */}
        <div style={{
          padding: '11px 20px',
          background: 'var(--card-bg)',
          borderBottom: '0.5px solid var(--border)',
          display: 'flex', justifyContent: 'space-between', alignItems: 'center',
          flexShrink: 0,
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
            <h1 style={{ fontSize: 15, fontWeight: 500 }}>{title}</h1>
            {caseData?.current_stage && caseData.current_stage !== 'done' && (
              <span className="badge badge-info" style={{ fontSize: 10 }}>
                <i className="ti ti-loader-2" style={{ fontSize: 10, animation: 'spin .7s linear infinite', marginRight: 2 }} aria-hidden="true" />
                Analysing…
              </span>
            )}
          </div>
          <div style={{ display: 'flex', gap: 6 }}>
            <span className="badge badge-ai">
              <i className="ti ti-sparkles" style={{ fontSize: 10 }} aria-hidden="true" /> AI-powered
            </span>
            <span className="badge" style={{ background: 'var(--gray-100)', color: 'var(--text-secondary)' }}>
              27/27 tests ✓
            </span>
            {caseData && (
              <span className="badge badge-active">
                {caseData.status?.replace('_', ' ')}
              </span>
            )}
          </div>
        </div>

        {/* Scrollable page content */}
        <div className="page-scroll">
          <Routes>
            <Route index element={<Navigate to="dashboard" replace />} />
            <Route path="dashboard" element={<DashboardPage {...pageProps} />} />
            <Route path="gaps"      element={<GapsPage      {...pageProps} />} />
            <Route path="timeline"  element={<TimelinePage  {...pageProps} />} />
            <Route path="copilot"   element={<CopilotPage   {...pageProps} />} />
            <Route path="evidence"  element={<EvidencePage  {...pageProps} />} />
            <Route path="reports"   element={<ReportsPage   {...pageProps} />} />
          </Routes>
        </div>
      </div>

      <style>{`@keyframes spin { to { transform: rotate(360deg) } }`}</style>
    </div>
  )
}

/* ── App root ────────────────────────────────────────────── */
export default function App() {
  return (
    <Routes>
      {/* Root → demo case */}
      <Route path="/" element={<Navigate to={`/case/${DEMO_CASE_ID}`} replace />} />

      {/* Case workspace — all nested page routes live here */}
      <Route path="/case/:caseId/*" element={<CaseRouteWrapper />} />
    </Routes>
  )
}

function CaseRouteWrapper() {
  const { caseId } = useParams()
  return <CaseWorkspace caseId={caseId} />
}
