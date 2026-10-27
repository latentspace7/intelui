import type { Row } from '../api'

export type CrmProps = { title: string; description: string; rows: Row[]; referenceDate: string }
export const label = (value: unknown) =>
  value === null || value === undefined ? '—' : String(value)
export const number = (value: unknown) => (typeof value === 'number' ? value : 0)
export const money = (value: number) =>
  new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    maximumFractionDigits: 2,
  }).format(value)
export const dateLabel = (value: unknown) => {
  const date = new Date(String(value))
  return Number.isNaN(date.getTime())
    ? '—'
    : date.toLocaleDateString('en-US', {
        month: 'short',
        day: 'numeric',
        year: 'numeric',
        timeZone: 'UTC',
      })
}
