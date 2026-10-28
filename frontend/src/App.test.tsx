import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { act, render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import App from './App'
import { api, type Analysis, type Report } from './api'
import { fixture } from './test-fixtures'

const analysis: Analysis = {
  id: '11111111-1111-4111-8111-111111111111',
  parent_id: null,
  question: 'Show revenue',
  snapshot: fixture(),
  created_at: '2026-10-26T10:00:00Z',
}
const report: Report = {
  ...analysis,
  analysis_id: analysis.id,
  title: 'Saved revenue',
  position: 0,
  last_refreshed_at: analysis.created_at,
  last_attempt_at: null,
  refresh_interval_hours: 4,
  next_refresh_at: '2026-10-26T14:00:00Z',
  refresh_status: 'success',
  refresh_error: null,
}

function mount() {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  })
  render(
    <QueryClientProvider client={client}>
      <App />
    </QueryClientProvider>,
  )
}

beforeEach(() => {
  vi.spyOn(api, 'health').mockResolvedValue({
    status: 'ok',
    database: true,
    analytics_database: true,
    model_configured: true,
    model: 'test',
    reference_date: '2026-10-26',
    scheduler_enabled: true,
    booking_count: 100,
  })
  vi.spyOn(api, 'history').mockResolvedValue([])
  vi.spyOn(api, 'reports').mockResolvedValue([])
  vi.spyOn(api, 'thread').mockResolvedValue([analysis])
})
afterEach(() => vi.restoreAllMocks())

describe('Critical workspace interactions', () => {
  it('clears and locks the composer immediately, acknowledges, and unlocks on completion', async () => {
    const user = userEvent.setup()
    let complete!: (value: Analysis) => void
    const ask = vi.spyOn(api, 'ask').mockImplementation(
      () =>
        new Promise<Analysis>((resolve) => {
          complete = resolve
        }),
    )
    mount()
    const question = screen.getByRole('textbox', { name: 'Ask an analytical question' })
    await user.type(question, 'Show revenue{Enter}')
    expect(question).toHaveValue('')
    expect(question).toBeDisabled()
    expect(screen.getByRole('button', { name: 'Send question' })).toBeDisabled()
    expect(screen.getByRole('status')).toHaveTextContent('Preparing your report')
    expect(screen.getByText('Show revenue')).toBeVisible()
    await user.keyboard('{Enter}{Enter}')
    expect(ask).toHaveBeenCalledTimes(1)
    await act(async () => complete(analysis))
    expect(await screen.findByText('$2,100.00')).toBeVisible()
    expect(question).toBeEnabled()
    expect(question).toHaveValue('')
    expect(question).toHaveFocus()
  })

  it('locks the composer for a suggested question and restores it after a failure', async () => {
    const user = userEvent.setup()
    let fail!: (error: Error) => void
    vi.spyOn(api, 'ask').mockImplementation(
      () =>
        new Promise<Analysis>((_resolve, reject) => {
          fail = reject
        }),
    )
    mount()
    await user.click(screen.getByRole('button', { name: /Explore revenue/ }))
    const question = screen.getByRole('textbox', { name: 'Ask an analytical question' })
    expect(question).toBeDisabled()
    expect(question).toHaveValue('')
    await act(async () => fail(new Error('The model provider is unavailable.')))
    expect(await screen.findByRole('alert')).toHaveTextContent('model provider is unavailable')
    expect(question).toBeEnabled()
    expect(question).toHaveValue(
      'Show won deal value by deal creation month over the last six months.',
    )
    expect(question).toHaveFocus()
  })

  it('submits a question, renders a report, and saves a title and schedule', async () => {
    const user = userEvent.setup()
    const ask = vi.spyOn(api, 'ask').mockResolvedValue(analysis)
    const save = vi.spyOn(api, 'save').mockResolvedValue(report)
    mount()
    await user.type(
      screen.getByRole('textbox', { name: 'Ask an analytical question' }),
      'Show revenue',
    )
    await user.click(screen.getByRole('button', { name: 'Send question' }))
    expect(await screen.findByText('$2,100.00')).toBeVisible()
    expect(ask).toHaveBeenCalledWith('Show revenue', null)
    await user.click(screen.getByRole('button', { name: 'Save to dashboard' }))
    const dialog = screen.getByRole('dialog', { name: 'Save to your dashboard' })
    await user.clear(within(dialog).getByLabelText('Report title'))
    await user.type(within(dialog).getByLabelText('Report title'), 'Saved revenue')
    await user.selectOptions(within(dialog).getByLabelText('Refresh schedule'), '4')
    await user.click(within(dialog).getByRole('button', { name: 'Save report' }))
    await waitFor(() => expect(save).toHaveBeenCalledWith(analysis.id, 'Saved revenue', 4))
    expect(await screen.findByText('Saved to your dashboard.')).toBeVisible()
  })

  it('offers the dashboard after saving and marks saved analyses', async () => {
    const user = userEvent.setup()
    vi.spyOn(api, 'ask').mockResolvedValue(analysis)
    vi.spyOn(api, 'save').mockResolvedValue(report)
    mount()
    await user.type(
      screen.getByRole('textbox', { name: 'Ask an analytical question' }),
      'Show revenue{Enter}',
    )
    await user.click(await screen.findByRole('button', { name: 'Save to dashboard' }))
    vi.mocked(api.reports).mockResolvedValue([report])
    await user.click(screen.getByRole('button', { name: 'Save report' }))
    expect(await screen.findByRole('button', { name: 'View on dashboard' })).toBeVisible()
    await user.click(screen.getByRole('button', { name: 'View dashboard' }))
    expect(await screen.findByRole('heading', { name: 'Saved revenue' })).toBeVisible()
  })

  it('puts an earlier question back in the composer', async () => {
    const user = userEvent.setup()
    vi.spyOn(api, 'ask').mockResolvedValue(analysis)
    mount()
    const question = screen.getByRole('textbox', { name: 'Ask an analytical question' })
    await user.type(question, 'Show revenue{Enter}')
    await user.click(await screen.findByRole('button', { name: 'Reuse this question' }))
    expect(question).toHaveValue('Show revenue')
    expect(question).toHaveFocus()
  })

  it('keeps the question when the provider fails', async () => {
    const user = userEvent.setup()
    vi.spyOn(api, 'ask').mockRejectedValue(new Error('The model provider is unavailable.'))
    mount()
    const question = screen.getByRole('textbox', { name: 'Ask an analytical question' })
    await user.type(question, 'Show revenue{Enter}')
    expect(await screen.findByRole('alert')).toHaveTextContent('model provider is unavailable')
    expect(question).toHaveValue('Show revenue')
    expect(screen.getByRole('button', { name: 'Send question' })).toBeEnabled()
  })

  it('loads a persisted dashboard and refreshes its saved report', async () => {
    const user = userEvent.setup()
    vi.mocked(api.reports).mockResolvedValue([report])
    const refresh = vi.spyOn(api, 'refresh').mockResolvedValue(report)
    mount()
    await user.click(screen.getByRole('button', { name: /My dashboard/ }))
    expect(await screen.findByRole('heading', { name: 'Saved revenue' })).toBeVisible()
    expect(screen.getByLabelText('Refresh interval for Saved revenue')).toHaveValue('4')
    await user.click(screen.getByRole('button', { name: 'Refresh' }))
    await waitFor(() => expect(refresh).toHaveBeenCalledWith(report.id))
    expect(await screen.findByText('Report refreshed with the latest data.')).toBeVisible()
  })
})
