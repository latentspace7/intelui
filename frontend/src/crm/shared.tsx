import { useState, type ReactNode } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { Check, LoaderCircle, Search } from 'lucide-react'
import { api } from '../api'

import { label } from './format'

export function Panel({
  title,
  description,
  children,
  toolbar,
}: {
  title: string
  description: string
  children: ReactNode
  toolbar?: ReactNode
}) {
  return (
    <section className="viz-panel crm-panel">
      <div className="viz-heading">
        <div>
          <h3>{title}</h3>
          <p>{description}</p>
        </div>
      </div>
      {toolbar && <div className="crm-toolbar">{toolbar}</div>}
      <div className="crm-body">{children}</div>
    </section>
  )
}

export function Badge({ value }: { value: unknown }) {
  const text = label(value)
  const tone = ['Complete', 'Accepted', 'Active', 'Won', 'Passed'].includes(text)
    ? 'positive'
    : ['Blocked', 'Needs correction', 'Failed', 'Lost', 'Overdue'].includes(text)
      ? 'negative'
      : 'neutral'
  return <span className={`crm-badge ${tone}`}>{text}</span>
}

export function SearchField({
  value,
  change,
  name = 'Search records',
}: {
  value: string
  change: (value: string) => void
  name?: string
}) {
  return (
    <label className="crm-search">
      <Search size={15} />
      <input
        aria-label={name}
        placeholder={name}
        value={value}
        onChange={(event) => change(event.target.value)}
      />
    </label>
  )
}

export function Filter({
  name,
  value,
  options,
  change,
  all = 'All',
}: {
  name: string
  value: string
  options: string[]
  change: (value: string) => void
  all?: string
}) {
  return (
    <label className="crm-filter">
      <span>{name}</span>
      <select aria-label={name} value={value} onChange={(event) => change(event.target.value)}>
        <option value="">{all}</option>
        {options.map((option) => (
          <option key={option}>{option}</option>
        ))}
      </select>
    </label>
  )
}

export function Empty({ children = 'No records match these filters.' }: { children?: ReactNode }) {
  return <div className="crm-empty">{children}</div>
}

export function Stat({
  title,
  value,
  detail,
}: {
  title: string
  value: string | number
  detail?: string
}) {
  return (
    <div className="crm-stat">
      <span>{title}</span>
      <strong>{value}</strong>
      {detail && <small>{detail}</small>}
    </div>
  )
}

export function StatusControl({
  entity,
  id,
  status,
  recordLabel,
  field = null,
  mismatch = false,
  onSaved,
}: {
  entity: 'tasks' | 'document_fields'
  id: number
  status: string
  recordLabel: string
  field?: string | null
  mismatch?: boolean
  onSaved?: (status: string) => void
}) {
  const client = useQueryClient()
  const [current, setCurrent] = useState(status)
  const [next, setNext] = useState(status)
  const [pending, setPending] = useState(false)
  const [error, setError] = useState('')
  const [saved, setSaved] = useState(false)
  const options =
    entity === 'tasks'
      ? ['Outstanding', 'In progress', 'Complete']
      : ['Pending', 'Accepted', 'Needs correction']
  const save = async () => {
    setPending(true)
    setError('')
    setSaved(false)
    try {
      const result = await api.crmStatus(entity, id, current, next, recordLabel, field)
      setCurrent(result.status)
      setSaved(true)
      onSaved?.(result.status)
      await client.invalidateQueries({ queryKey: ['catalog-preview'], refetchType: 'none' })
    } catch (error) {
      setError(error instanceof Error ? error.message : 'Could not save the status.')
    } finally {
      setPending(false)
    }
  }
  return (
    <div className="crm-status-control">
      <div>
        <select
          aria-label={`Status for record ${id}`}
          value={next}
          disabled={pending}
          onChange={(event) => {
            setNext(event.target.value)
            setSaved(false)
          }}
        >
          {options.map((option) => (
            <option key={option} disabled={option === 'Accepted' && mismatch}>
              {option}
            </option>
          ))}
        </select>
        <button
          className="secondary-button"
          onClick={save}
          disabled={pending || next === current}
          aria-label={`Save status for record ${id}`}
        >
          {pending ? <LoaderCircle className="spin" size={13} /> : <Check size={13} />}Save
        </button>
      </div>
      {saved && <small role="status">Changes saved</small>}
      {error && (
        <p className="error-box" role="alert">
          {error}
        </p>
      )}
    </div>
  )
}
