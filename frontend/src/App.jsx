import { useEffect, useMemo, useState } from 'react'
import './App.css'

const PAGE_SIZE = 10
const REASONS = [
  'data_issue',
  'duplicate_b_entries',
  'missing_in_b',
  'unknown_b_reference',
  'value_mismatch',
]

const REASON_LABELS = {
  data_issue: 'Data issue',
  duplicate_b_entries: 'Duplicate B entries',
  missing_in_b: 'Missing in B',
  unknown_b_reference: 'Unknown B reference',
  value_mismatch: 'Value mismatch',
}

function App() {
  const [reason, setReason] = useState('')
  const [sortByValue, setSortByValue] = useState(false)
  const [page, setPage] = useState(1)
  const [data, setData] = useState({ count: 0, page: 1, page_size: PAGE_SIZE, total_pages: 1, results: [] })
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState('')

  const apiUrl = useMemo(() => {
    const params = new URLSearchParams({
      page: String(page),
      page_size: String(PAGE_SIZE),
    })

    if (reason) {
      params.set('reason', reason)
    }

    if (sortByValue) {
      params.set('sort', 'value')
    }

    return `/api/disagreements/?${params.toString()}`
  }, [page, reason, sortByValue])

  useEffect(() => {
    let shouldIgnore = false

    async function loadDisagreements() {
      setIsLoading(true)
      setError('')

      try {
        const response = await fetch(apiUrl)
        const body = await response.json()

        if (!response.ok) {
          throw new Error(body.error || 'Could not load disagreements.')
        }

        if (!shouldIgnore) {
          setData(body)
        }
      } catch (caughtError) {
        if (!shouldIgnore) {
          setError(caughtError.message)
          setData({ count: 0, page: 1, page_size: PAGE_SIZE, total_pages: 1, results: [] })
        }
      } finally {
        if (!shouldIgnore) {
          setIsLoading(false)
        }
      }
    }

    loadDisagreements()

    return () => {
      shouldIgnore = true
    }
  }, [apiUrl])

  function changeReason(nextReason) {
    setReason(nextReason)
    setPage(1)
  }

  function changeSortByValue(shouldSort) {
    setSortByValue(shouldSort)
    setPage(1)
  }

  function goToPreviousPage() {
    if (page > 1) {
      setPage(page - 1)
    }
  }

  function goToNextPage() {
    if (page < data.total_pages) {
      setPage(page + 1)
    }
  }

  return (
    <main className="page-shell">
      <header className="page-header">
        <div>
          <h1>DealerOS Reconciliation</h1>
          <p>{data.count} disagreements</p>
        </div>
      </header>

      <section className="toolbar" aria-label="Disagreement filters">
        <label>
          Reason
          <select value={reason} onChange={(event) => changeReason(event.target.value)}>
            <option value="">All reasons</option>
            {REASONS.map((reasonOption) => (
              <option value={reasonOption} key={reasonOption}>{REASON_LABELS[reasonOption]}</option>
            ))}
          </select>
        </label>

        <label className="checkbox-label">
          <input
            checked={sortByValue}
            onChange={(event) => changeSortByValue(event.target.checked)}
            type="checkbox"
          />
          Sort by value
        </label>
      </section>

      {error && <p className="status error">{error}</p>}
      {isLoading && <p className="status">Loading disagreements...</p>}

      {!isLoading && !error && (
        <>
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Reason</th>
                  <th>Record</th>
                  <th>Location</th>
                  <th>System A value</th>
                  <th>System B value</th>
                  <th>Message</th>
                </tr>
              </thead>
              <tbody>
                {data.results.map((item) => (
                  <tr key={`${item.reason}-${item.org_id}-${item.record_id}-${item.b_entry_ids.join('-')}`}>
                    <td>{REASON_LABELS[item.reason] || item.reason}</td>
                    <td>{item.record_id}</td>
                    <td>{item.location_name || item.location_id}</td>
                    <td>{formatValue(item.a_value)}</td>
                    <td>{formatValues(item.b_values)}</td>
                    <td>{item.message}</td>
                  </tr>
                ))}
                {data.results.length === 0 && (
                  <tr>
                    <td colSpan="6" className="empty-state">No disagreements found.</td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>

          <div className="pagination" aria-label="Pagination controls">
            <button type="button" onClick={goToPreviousPage} disabled={page <= 1}>
              Previous
            </button>
            <span>Page {data.page} of {data.total_pages}</span>
            <button type="button" onClick={goToNextPage} disabled={page >= data.total_pages}>
              Next
            </button>
          </div>
        </>
      )}
    </main>
  )
}

function formatValues(values) {
  if (!values || values.length === 0) {
    return '-'
  }

  return values.map((value) => formatValue(value)).join(', ')
}

function formatValue(value) {
  if (value === null || value === undefined) {
    return '-'
  }

  return value
}

export default App
