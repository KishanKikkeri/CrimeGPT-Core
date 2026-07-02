/**
 * CrimeGPT API service layer.
 * All calls go through /api which Vite proxies to http://localhost:8000.
 * In production, set VITE_API_URL env var and update the base URL.
 */

const BASE = import.meta.env.VITE_API_URL || '/api'

async function request(method, path, body) {
  const res = await fetch(`${BASE}${path}`, {
    method,
    headers: { 'Content-Type': 'application/json' },
    body: body ? JSON.stringify(body) : undefined,
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }))
    throw new Error(err.detail || `Request failed: ${res.status}`)
  }
  if (res.status === 204) return null
  return res.json()
}

const get  = (path)        => request('GET', path)
const post = (path, body)  => request('POST', path, body)
const del  = (path)        => request('DELETE', path)

// ── Cases ──────────────────────────────────────────────────────────────

export const createCase = (title, rawInput, jurisdiction, crimeType) =>
  post('/cases', { title, raw_input: rawInput, jurisdiction, crime_type: crimeType })

export const listCases = (skip = 0, limit = 50) =>
  get(`/cases?skip=${skip}&limit=${limit}`)

export const getCase = (caseId) =>
  get(`/cases/${caseId}`)

export const deleteCase = (caseId) =>
  del(`/cases/${caseId}`)

// ── Analysis ────────────────────────────────────────────────────────────

export const analyzeCase = (caseId, rawInput, reportTypes = ['investigation_report']) =>
  post(`/cases/${caseId}/analyze`, { raw_input: rawInput, report_types: reportTypes })

export const reanalyzeCase = (caseId, reportTypes = ['investigation_report']) =>
  post(`/cases/${caseId}/reanalyze`, { report_types: reportTypes })

// ── Investigation data ──────────────────────────────────────────────────

export const getTimeline = (caseId) =>
  get(`/cases/${caseId}/timeline`)

export const getGaps = (caseId, severity, category) => {
  const params = new URLSearchParams()
  if (severity) params.append('severity', severity)
  if (category) params.append('category', category)
  const qs = params.toString()
  return get(`/cases/${caseId}/gaps${qs ? '?' + qs : ''}`)
}

export const getHealth = (caseId) =>
  get(`/cases/${caseId}/health`)

// ── Reports ─────────────────────────────────────────────────────────────

export const listReports = (caseId) =>
  get(`/cases/${caseId}/reports`)

export const generateReport = (caseId, reportType) =>
  post(`/cases/${caseId}/reports`, { report_type: reportType })

export const getReport = (caseId, reportId) =>
  get(`/cases/${caseId}/reports/${reportId}`)
