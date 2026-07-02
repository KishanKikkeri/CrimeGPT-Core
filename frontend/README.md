# CrimeGPT Frontend

React 18 + Vite investigation workspace. Six-page UI connected live to the FastAPI backend.

## Pages

| Page | Route | Description |
|------|-------|-------------|
| Dashboard | `/case/:id/dashboard` | Readiness gauge + metrics + "What Happens If?" simulation |
| Investigation Gaps | `/case/:id/gaps` | Expandable AI-enriched gap cards |
| Timeline | `/case/:id/timeline` | Interactive timeline with contradiction detection |
| AI Copilot | `/case/:id/copilot` | Executive summary + priority actions |
| Evidence Board | `/case/:id/evidence` | SVG connection graph |
| Reports | `/case/:id/reports` | Generate + download any report type |

## Quickstart

```bash
npm install
npm run dev       # http://localhost:3000
npm run build     # production build → dist/
```

## Environment

```bash
cp .env.example .env
# Set VITE_API_URL for production deployment
# Set VITE_DEMO_CASE_ID to load a specific case on startup
```

## Architecture

- `src/services/api.js` — all backend calls (proxied via Vite → FastAPI)
- `src/hooks/useCase.js` — fetches & auto-refreshes the Case Object while pipeline runs
- `src/components/ui/index.jsx` — Gauge, ScoreBar, GapCard, Spinner, Empty, ErrorBox
- `src/components/layout/` — Sidebar (navy, persistent) + Banner (critical issue alert)
- `src/pages/` — one file per page, all receive `{ caseData, loading, error, refresh }` from `useCase`

## Deployment

**Vercel (recommended):**
```
Build command: npm run build
Output dir: dist
Environment: VITE_API_URL=https://your-api.railway.app
```
