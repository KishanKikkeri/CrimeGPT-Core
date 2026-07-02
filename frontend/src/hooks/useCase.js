import { useState, useEffect, useCallback } from 'react'
import { getCase } from '../services/api'

/**
 * Fetches the full Case Object and auto-refreshes while analysis is running.
 *
 * Usage:
 *   const { caseData, loading, error, refresh } = useCase(caseId)
 */
export function useCase(caseId) {
  const [caseData, setCaseData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  const fetch = useCallback(async () => {
    if (!caseId) return
    try {
      setError(null)
      const data = await getCase(caseId)
      setCaseData(data)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }, [caseId])

  useEffect(() => {
    fetch()
  }, [fetch])

  // Auto-refresh every 3 seconds while the pipeline is running
  useEffect(() => {
    if (!caseData) return
    const running = caseData.current_stage &&
      caseData.current_stage !== 'done' &&
      caseData.current_stage !== 'case_created'
    if (!running) return

    const timer = setInterval(fetch, 3000)
    return () => clearInterval(timer)
  }, [caseData, fetch])

  return { caseData, loading, error, refresh: fetch }
}
