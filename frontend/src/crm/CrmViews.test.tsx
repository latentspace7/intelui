import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { api } from '../api'
import ReportRenderer from '../ReportRenderer'
import { fixture } from '../test-fixtures'
import { boundedNumber, quoteTotals } from './calculations'
import { BudgetPlanner, Comparison, QuoteSimulator } from './FinanceViews'
import { Checklist, DocumentReview, RuleAssessment } from './RecordViews'
import { RelationshipGraph } from './RelationshipGraph'

const base = { title: 'CRM example', description: 'Synthetic data', referenceDate: '2026-10-26' }
const quote = {
  id: 1,
  label: 'Essential',
  unit_price: 35,
  quantity: 11,
  months: 12,
  discount: 0,
  setup_fee: 250,
}
const task = {
  id: 7,
  label: 'Review agreement',
  status: 'Outstanding',
  owner: 'Alex',
  date: '2026-10-20',
}

afterEach(() => vi.restoreAllMocks())

function provider(children: React.ReactNode) {
  return (
    <QueryClientProvider
      client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}
    >
      {children}
    </QueryClientProvider>
  )
}

describe('CRM interactions and calculations', () => {
  it('calculates rounded recurring costs, setup once, and rejects invalid scenario inputs', () => {
    expect(quoteTotals(35, 11, 12, 0, 250)).toEqual({ monthly: 385, total: 4870, firstMonth: 635 })
    expect(quoteTotals(19.99, 3, 12, 12.5, 100)).toEqual({
      monthly: 52.47,
      total: 729.64,
      firstMonth: 152.47,
    })
    for (const input of ['', 'Infinity', '-1', '101'])
      expect(boundedNumber(input, 0, 100)).toBeNull()
    expect(boundedNumber('1.5', 1, 120, true)).toBeNull()
  })

  it('changes a quote scenario, validates blank values, and resets to the stored inputs', async () => {
    const user = userEvent.setup()
    render(<QuoteSimulator {...base} rows={[quote]} />)
    expect(screen.getAllByText('$4,870.00')).toHaveLength(2)
    await user.clear(screen.getByLabelText('Seats'))
    expect(screen.getByRole('alert')).toHaveTextContent('whole seats')
    await user.type(screen.getByLabelText('Seats'), '22')
    expect(screen.getByText('$9,490.00')).toBeVisible()
    await user.click(screen.getByRole('button', { name: 'Reset to saved quote' }))
    expect(screen.getByLabelText('Seats')).toHaveValue(11)
    expect(screen.getAllByText('$4,870.00')).toHaveLength(2)
  })

  it('updates budget surplus locally and resets its sliders', async () => {
    const user = userEvent.setup()
    render(
      <BudgetPlanner
        {...base}
        rows={[{ id: 1, label: 'Account', income: 1000, expenses: 600, budget: 200 }]}
      />,
    )
    expect(document.querySelector('.crm-hero-value')).toHaveTextContent('$200.00')
    fireEvent.change(screen.getByRole('slider', { name: 'Expense change' }), {
      target: { value: 50 },
    })
    expect(document.querySelector('.crm-hero-value')).toHaveTextContent('-$100.00')
    expect(screen.getByText('Deficit in this scenario')).toBeVisible()
    await user.click(screen.getByRole('button', { name: 'Reset assumptions' }))
    expect(document.querySelector('.crm-hero-value')).toHaveTextContent('$200.00')
  })

  it('supports deselecting every comparison option', async () => {
    const user = userEvent.setup()
    render(
      <Comparison
        {...base}
        rows={[
          {
            id: 1,
            label: 'Option one',
            amount: 200,
            category: 'Service',
            description: 'Annual service',
          },
        ]}
      />,
    )
    await user.click(screen.getByRole('checkbox', { name: 'Option one' }))
    expect(screen.getByText('Select an option above to compare it.')).toBeVisible()
  })

  it('saves task status with the record identity and updates completion', async () => {
    const user = userEvent.setup()
    const save = vi.spyOn(api, 'crmStatus').mockResolvedValue({ id: 7, status: 'Complete' })
    render(provider(<Checklist {...base} rows={[task]} />))
    await user.selectOptions(screen.getByLabelText('Status for record 7'), 'Complete')
    await user.click(screen.getByRole('button', { name: 'Save status for record 7' }))
    await waitFor(() =>
      expect(save).toHaveBeenCalledWith(
        'tasks',
        7,
        'Outstanding',
        'Complete',
        'Review agreement',
        null,
      ),
    )
    expect(await screen.findByText('1 of 1 complete')).toBeVisible()
    expect(screen.getByText('Changes saved')).toBeVisible()
  })

  it('keeps a failed write visible without claiming it was saved', async () => {
    const user = userEvent.setup()
    vi.spyOn(api, 'crmStatus').mockRejectedValue(new Error('This record changed. Reload its data.'))
    render(provider(<Checklist {...base} rows={[task]} />))
    await user.selectOptions(screen.getByLabelText('Status for record 7'), 'Complete')
    await user.click(screen.getByRole('button', { name: 'Save status for record 7' }))
    expect(await screen.findByRole('alert')).toHaveTextContent('record changed')
    expect(screen.getByText('0 of 1 complete')).toBeVisible()
    expect(screen.queryByText('Changes saved')).not.toBeInTheDocument()
  })

  it('prevents accepting a mismatched document field', () => {
    render(
      provider(
        <DocumentReview
          {...base}
          rows={[
            {
              id: 2,
              label: 'Agreement',
              field: 'Amount',
              expected: '100',
              actual: '200',
              source: 'Amount: 200',
              status: 'Pending',
            },
          ]}
        />,
      ),
    )
    expect(
      within(screen.getByLabelText('Status for record 2')).getByRole('option', {
        name: 'Accepted',
      }),
    ).toBeDisabled()
    expect(screen.getByText('Values differ')).toBeVisible()
  })

  it('distinguishes unknown rule inputs from failed checks', async () => {
    const user = userEvent.setup()
    render(
      <RuleAssessment
        {...base}
        rows={[
          {
            id: 1,
            label: 'Missing observation',
            observed: null,
            threshold: 4,
            operator: 'gte',
            description: 'Recorded demo check',
          },
          {
            id: 2,
            label: 'Spending limit',
            observed: 120,
            threshold: 100,
            operator: 'lte',
            description: 'Recorded demo check',
          },
        ]}
      />,
    )
    await user.selectOptions(screen.getByLabelText('Rule result'), 'Needs information')
    expect(screen.getByText('Missing observation')).toBeVisible()
    expect(screen.queryByText('Spending limit')).not.toBeInTheDocument()
  })

  it('changes graph focus to show actual connected records', async () => {
    const user = userEvent.setup()
    render(
      <RelationshipGraph
        {...base}
        rows={[
          { source: 'Company A', target: 'Company B', relationship: 'Partner' },
          { source: 'Company B', target: 'Contact C', relationship: 'Director' },
        ]}
      />,
    )
    expect(screen.getByText('1 connections in the returned records')).toBeVisible()
    await user.selectOptions(screen.getByLabelText('Relationship focus'), 'Company B')
    expect(screen.getByText('2 connections in the returned records')).toBeVisible()
  })

  it('renders a CRM component through the actual A2UI catalog', () => {
    const snapshot = fixture()
    snapshot.ui = [
      {
        version: 'v0.9',
        createSurface: { surfaceId: 'report', catalogId: 'aerovista://analytics/v1' },
      },
      {
        version: 'v0.9',
        updateComponents: {
          surfaceId: 'report',
          components: [
            { id: 'root', component: 'Stack', items: ['quote'] },
            { id: 'quote', component: 'QuoteSimulator', ...base, rows: [quote] },
          ],
        },
      },
    ]
    render(provider(<ReportRenderer snapshot={snapshot} />))
    expect(screen.getByLabelText('Seats')).toHaveValue(11)
    expect(screen.queryByRole('alert')).not.toBeInTheDocument()
  })
})
