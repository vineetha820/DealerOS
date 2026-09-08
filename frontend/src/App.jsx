import { useEffect, useMemo, useState } from 'react'
import './App.css'

const ORGS = ['ORG-A', 'ORG-B']
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
  const [orgId, setOrgId] = useState('ORG-A')
  const [reason, setReason] = useState('')
  const [sortByValue, setSortByValue] = useState(false)
  const [data, setData] = useState({ count: 0, results: [] })
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState('')

  const apiUrl = useMemo(() => {
    const params = new URLSearchParams({ org_id: orgId })

    if (reason) {
      params.set('reason', reason)
    }

    if (sortByValue) {
      params.set('sort', 'value')
    }

    return `/api/disagreements/?${params.toString()}`
  }, [orgId, reason, sortByValue])

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
          setData({ count: 0, results: [] })
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

  return (
    <main className="page-shell">
      <header className="page-header">
        <div>
          <h1>DealerOS Reconciliation</h1>
          <p>{data.count} disagreements for {orgId}</p>
        </div>
      </header>

      <section className="toolbar" aria-label="Disagreement filters">
        <label>
          Org
          <select value={orgId} onChange={(event) => setOrgId(event.target.value)}>
            {ORGS.map((org) => (
              <option value={org} key={org}>{org}</option>
            ))}
          </select>
        </label>

        <label>
          Reason
          <select value={reason} onChange={(event) => setReason(event.target.value)}>
            <option value="">All reasons</option>
            {REASONS.map((reasonOption) => (
              <option value={reasonOption} key={reasonOption}>{REASON_LABELS[reasonOption]}</option>
            ))}
          </select>
        </label>

        <label className="checkbox-label">
          <input
            checked={sortByValue}
            onChange={(event) => setSortByValue(event.target.checked)}
            type="checkbox"
          />
          Sort by value
        </label>
      </section>

      {error && <p className="status error">{error}</p>}
      {isLoading && <p className="status">Loading disagreements...</p>}

      {!isLoading && !error && (
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Reason</th>
                <th>Record</th>
                <th>Location</th>
                <th>System A value</th>
                <th>System B value</th>
                <th>System B entries</th>
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
                  <td>{formatEntries(item.b_entry_ids)}</td>
                  <td>{item.message}</td>
                </tr>
              ))}
              {data.results.length === 0 && (
                <tr>
                  <td colSpan="7" className="empty-state">No disagreements found.</td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
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

function formatEntries(entries) {
  if (!entries || entries.length === 0) {
    return '-'
  }

  return entries.join(', ')
}

export default App
