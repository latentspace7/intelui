import { render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it } from 'vitest'
import ReportRenderer from './ReportRenderer'
import { fixture } from './test-fixtures'

describe('Official CopilotKit A2UI integration', () => {
  it('renders catalog components through the actual A2UI provider and sorts data', async () => {
    const user = userEvent.setup()
    render(<ReportRenderer snapshot={fixture()} />)
    expect(screen.getByText('Cost not recorded')).toBeVisible()
    expect(await screen.findByText('$2,100.00')).toBeVisible()
    const table = await screen.findByRole('table', { name: 'Revenue by class' })
    expect(table).toHaveTextContent('Economy')
    await user.click(within(table).getByRole('button', { name: /Travel Class/ }))
    expect(table.querySelector('tbody tr')?.textContent).toContain('Business')
    await user.click(screen.getByText('Query details'))
    expect(screen.getByText(/SELECT travel_class/)).toBeVisible()
  })

  it('rejects unsupported generated components', async () => {
    const snapshot = fixture()
    snapshot.ui[1] = {
      version: 'v0.9',
      updateComponents: {
        surfaceId: 'report',
        components: [{ id: 'root', component: 'Script', code: 'alert(1)' }],
      },
    }
    render(<ReportRenderer snapshot={snapshot} />)
    expect(await screen.findByRole('alert')).toHaveTextContent('unsupported presentation')
  })

  it('shows a useful empty state', () => {
    const snapshot = fixture()
    snapshot.result.rows = []
    snapshot.ui = []
    render(<ReportRenderer snapshot={snapshot} />)
    expect(screen.getByText('No matching records')).toBeVisible()
  })

  it('shows fractional-cent model costs beside query details with usage on expansion', async () => {
    const snapshot = fixture()
    snapshot.model_cost = {
      currency: 'USD',
      estimated_usd: 0.002015,
      model_calls: 2,
      input_tokens: 12000,
      cached_input_tokens: 4000,
      cache_write_tokens: 7000,
      output_tokens: 2000,
      pricing_date: '2026-10-26',
      unavailable_reason: null,
    }
    render(<ReportRenderer snapshot={snapshot} />)
    expect(screen.getByText('Est. $0.002015 USD')).toBeVisible()
    await userEvent.click(screen.getByText('Query details'))
    expect(screen.getByText(/2 model calls/)).toHaveTextContent('12,000 input tokens')
    expect(screen.getByText(/4,000 cached input tokens/)).toBeVisible()
  })

  it('distinguishes unavailable pricing from a zero-cost generation', () => {
    const snapshot = fixture()
    snapshot.model_cost = {
      currency: 'USD',
      estimated_usd: null,
      model_calls: 1,
      input_tokens: 100,
      cached_input_tokens: 0,
      cache_write_tokens: 0,
      output_tokens: 50,
      pricing_date: '2026-10-26',
      unavailable_reason: 'Pricing is not configured for this model.',
    }
    const { rerender } = render(<ReportRenderer snapshot={snapshot} />)
    expect(screen.getByText('Cost unavailable')).toBeVisible()
    snapshot.model_cost = { ...snapshot.model_cost, estimated_usd: 0, model_calls: 0 }
    rerender(<ReportRenderer snapshot={snapshot} />)
    expect(screen.getByText('Est. $0.00 USD')).toBeVisible()
  })
})
