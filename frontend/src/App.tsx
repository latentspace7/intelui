import { useEffect, useId, useRef, useState, type FormEvent, type ReactNode } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  ArrowDown,
  ArrowRight,
  ArrowUp,
  BarChart3,
  Bookmark,
  Check,
  ChevronDown,
  CircleHelp,
  Clock3,
  Database,
  LayoutDashboard,
  LoaderCircle,
  Menu,
  MessageSquare,
  Moon,
  Pencil,
  Plane,
  Plus,
  RefreshCw,
  Settings2,
  Sparkles,
  Sun,
  Trash2,
  TrendingUp,
  X,
} from 'lucide-react'
import { api, type Analysis, type Report } from './api'
import ReportRenderer from './ReportRenderer'

const intervals = [
  { value: 0, label: 'Manual only' },
  { value: 1, label: 'Every hour' },
  { value: 4, label: 'Every 4 hours' },
  { value: 12, label: 'Every 12 hours' },
  { value: 24, label: 'Every 24 hours' },
]
const questions = [
  {
    icon: TrendingUp,
    label: 'Explore revenue',
    text: 'Show revenue by travel class over the last six months.',
    tint: 'blue',
  },
  {
    icon: Plane,
    label: 'Understand operations',
    text: 'How have flight cancellations changed over the last six months?',
    tint: 'green',
  },
  {
    icon: MessageSquare,
    label: 'Listen to customers',
    text: 'Which customers have submitted the most complaints?',
    tint: 'purple',
  },
  {
    icon: BarChart3,
    label: 'See the bigger picture',
    text: 'Generate an executive summary of the airline’s operational performance.',
    tint: 'orange',
  },
]

function dateLabel(value: string) {
  return new Date(value).toLocaleString(undefined, {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
}
function errorMessage(error: unknown) {
  return error instanceof Error ? error.message : 'Something went wrong. Please try again.'
}

function Modal({
  title,
  children,
  close,
}: {
  title: string
  children: ReactNode
  close: () => void
}) {
  const ref = useRef<HTMLDialogElement>(null)
  const titleId = useId()
  useEffect(() => {
    const dialog = ref.current
    dialog?.showModal()
    return () => dialog?.close()
  }, [])
  return (
    <dialog
      ref={ref}
      className="modal"
      aria-labelledby={titleId}
      onCancel={close}
      onClick={(event) => {
        if (event.target === event.currentTarget) close()
      }}
    >
      <div className="modal-heading">
        <h2 id={titleId}>{title}</h2>
        <button className="icon-button" onClick={close} aria-label="Close dialog">
          <X size={19} />
        </button>
      </div>
      {children}
    </dialog>
  )
}

function SaveDialog({
  analysis,
  close,
  saved,
}: {
  analysis: Analysis
  close: () => void
  saved: () => void
}) {
  const [title, setTitle] = useState(analysis.snapshot.title)
  const [interval, setInterval] = useState(0)
  const mutation = useMutation({
    mutationFn: () => api.save(analysis.id, title, interval),
    onSuccess: saved,
  })
  return (
    <Modal title="Save to your dashboard" close={close}>
      <p className="muted">Keep this analysis close, and choose when its data should refresh.</p>
      <form
        onSubmit={(event) => {
          event.preventDefault()
          mutation.mutate()
        }}
      >
        <label>
          Report title
          <input
            value={title}
            onChange={(event) => setTitle(event.target.value)}
            maxLength={120}
            required
            autoFocus
          />
        </label>
        <label>
          Refresh schedule
          <select value={interval} onChange={(event) => setInterval(Number(event.target.value))}>
            {intervals.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        </label>
        <p className="field-help">
          <Clock3 size={14} />
          Scheduled reports update even when your browser is closed.
        </p>
        {mutation.error && (
          <p className="error-box" role="alert">
            {errorMessage(mutation.error)}
          </p>
        )}
        <div className="modal-actions">
          <button type="button" className="secondary-button" onClick={close}>
            Cancel
          </button>
          <button className="primary-button" disabled={!title.trim() || mutation.isPending}>
            {mutation.isPending ? (
              <LoaderCircle size={16} className="spin" />
            ) : (
              <Bookmark size={16} />
            )}
            Save report
          </button>
        </div>
      </form>
    </Modal>
  )
}

function DashboardCard({
  report,
  index,
  total,
  move,
  notify,
}: {
  report: Report
  index: number
  total: number
  move: (direction: number) => void
  notify: (message: string) => void
}) {
  const client = useQueryClient()
  const [editing, setEditing] = useState(false)
  const [title, setTitle] = useState(report.title)
  const [confirmDelete, setConfirmDelete] = useState(false)
  const invalidate = () => client.invalidateQueries({ queryKey: ['reports'] })
  const update = useMutation({
    mutationFn: (changes: { title?: string; refresh_interval_hours?: number }) =>
      api.update(report.id, changes),
    onSuccess: () => {
      setEditing(false)
      invalidate()
    },
    onError: (error) => notify(errorMessage(error)),
  })
  const remove = useMutation({
    mutationFn: () => api.remove(report.id),
    onSuccess: () => {
      invalidate()
      notify('Report removed from your dashboard.')
    },
    onError: (error) => notify(errorMessage(error)),
  })
  const refresh = useMutation({
    mutationFn: () => api.refresh(report.id),
    onSuccess: (value) => {
      invalidate()
      notify(
        value.refresh_status === 'error'
          ? value.refresh_error || 'Refresh failed.'
          : 'Report refreshed with the latest data.',
      )
    },
    onError: (error) => notify(errorMessage(error)),
  })
  return (
    <article className="dashboard-card">
      <div className="dashboard-card-header">
        <div className="report-heading">
          <span className="eyebrow">SAVED ANALYSIS</span>
          {editing ? (
            <form
              className="inline-edit"
              onSubmit={(event) => {
                event.preventDefault()
                update.mutate({ title })
              }}
            >
              <input
                autoFocus
                aria-label="Report title"
                value={title}
                onChange={(event) => setTitle(event.target.value)}
                maxLength={120}
                required
              />
              <button
                className="icon-button"
                disabled={update.isPending || !title.trim()}
                aria-label="Save report title"
              >
                <Check size={17} />
              </button>
              <button
                className="icon-button"
                type="button"
                onClick={() => setEditing(false)}
                aria-label="Cancel rename"
              >
                <X size={17} />
              </button>
            </form>
          ) : (
            <h2>{report.title}</h2>
          )}
          <p>{report.question}</p>
        </div>
        <div className="card-tools">
          <button
            className="icon-button"
            onClick={() => move(-1)}
            disabled={index === 0}
            aria-label={`Move ${report.title} up`}
          >
            <ArrowUp size={15} />
          </button>
          <button
            className="icon-button"
            onClick={() => move(1)}
            disabled={index === total - 1}
            aria-label={`Move ${report.title} down`}
          >
            <ArrowDown size={15} />
          </button>
          <button
            className="icon-button"
            onClick={() => {
              setTitle(report.title)
              setEditing(true)
            }}
            aria-label={`Rename ${report.title}`}
          >
            <Pencil size={15} />
          </button>
          <button
            className="icon-button"
            onClick={() => setConfirmDelete(true)}
            aria-label={`Delete ${report.title}`}
          >
            <Trash2 size={15} />
          </button>
        </div>
      </div>
      <ReportRenderer snapshot={report.snapshot} />
      <div className="refresh-footer">
        <div>
          <span>
            <Clock3 size={13} />
            Updated {dateLabel(report.last_refreshed_at)}
          </span>
          {report.next_refresh_at && <small>Next update {dateLabel(report.next_refresh_at)}</small>}
        </div>
        <div className="refresh-controls">
          <select
            aria-label={`Refresh interval for ${report.title}`}
            value={report.refresh_interval_hours}
            disabled={update.isPending}
            onChange={(event) =>
              update.mutate({ refresh_interval_hours: Number(event.target.value) })
            }
          >
            {intervals.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
          <button
            className="secondary-button"
            onClick={() => refresh.mutate()}
            disabled={refresh.isPending}
          >
            <RefreshCw size={14} className={refresh.isPending ? 'spin' : ''} />
            {refresh.isPending ? 'Refreshing…' : 'Refresh'}
          </button>
        </div>
      </div>
      {report.refresh_error && (
        <div className="error-box" role="alert">
          {report.refresh_error} The last successful report is shown above.
        </div>
      )}
      {confirmDelete && (
        <Modal title="Delete this saved report?" close={() => setConfirmDelete(false)}>
          <p className="muted">Your original conversation will still be available.</p>
          <div className="modal-actions">
            <button className="secondary-button" onClick={() => setConfirmDelete(false)}>
              Cancel
            </button>
            <button
              className="danger-button"
              onClick={() => remove.mutate()}
              disabled={remove.isPending}
            >
              Delete report
            </button>
          </div>
        </Modal>
      )}
    </article>
  )
}

export default function App() {
  const client = useQueryClient()
  const [page, setPage] = useState<'analysis' | 'dashboard'>('analysis')
  const [currentId, setCurrentId] = useState<string | null>(null)
  const [draft, setDraft] = useState('')
  const [pendingQuestion, setPendingQuestion] = useState('')
  const [sidebar, setSidebar] = useState(false)
  const [saveAnalysis, setSaveAnalysis] = useState<Analysis | null>(null)
  const [settings, setSettings] = useState(false)
  const [toast, setToast] = useState('')
  const [theme, setTheme] = useState(() => localStorage.getItem('aerovista-theme') || 'light')
  const bottom = useRef<HTMLDivElement>(null)
  const input = useRef<HTMLTextAreaElement>(null)
  const submitting = useRef(false)
  const health = useQuery({ queryKey: ['health'], queryFn: api.health, refetchInterval: 30000 })
  const history = useQuery({ queryKey: ['history'], queryFn: api.history })
  const reports = useQuery({ queryKey: ['reports'], queryFn: api.reports, refetchInterval: 30000 })
  const thread = useQuery({
    queryKey: ['thread', currentId],
    queryFn: () => api.thread(currentId!),
    enabled: !!currentId,
  })
  const analyses = currentId ? thread.data || [] : []
  const ask = useMutation({
    mutationFn: ({ question, parent }: { question: string; parent: string | null }) =>
      api.ask(question, parent),
    onSuccess: (analysis) => {
      client.setQueryData(['thread', analysis.id], [...analyses, analysis])
      setCurrentId(analysis.id)
      setDraft('')
      setPendingQuestion('')
      client.invalidateQueries({ queryKey: ['history'] })
    },
    onError: (_error, { question }) => {
      setDraft(question)
      setPendingQuestion('')
    },
    onSettled: () => {
      submitting.current = false
    },
  })
  useEffect(() => {
    document.documentElement.dataset.theme = theme
    localStorage.setItem('aerovista-theme', theme)
  }, [theme])
  useEffect(() => {
    if (toast) {
      const id = setTimeout(() => setToast(''), 6000)
      return () => clearTimeout(id)
    }
  }, [toast])
  useEffect(() => {
    if (pendingQuestion || analyses.length)
      bottom.current?.scrollIntoView({ behavior: 'smooth', block: 'end' })
  }, [pendingQuestion, analyses.length])
  useEffect(() => {
    if (!ask.isPending && (ask.isSuccess || ask.isError) && page === 'analysis')
      input.current?.focus()
  }, [ask.isPending, ask.isSuccess, ask.isError, page])
  const newAnalysis = () => {
    if (ask.isPending) return
    setPage('analysis')
    setCurrentId(null)
    setDraft('')
    setSidebar(false)
    ask.reset()
    input.current?.focus()
  }
  const submit = (event?: FormEvent, question = draft) => {
    event?.preventDefault()
    if (question.trim().length < 3 || submitting.current) return
    submitting.current = true
    setPage('analysis')
    setDraft('')
    setPendingQuestion(question.trim())
    ask.mutate({ question: question.trim(), parent: currentId })
  }
  const moveReport = async (index: number, direction: number) => {
    const items = reports.data || []
    const other = index + direction
    if (!items[other]) return
    try {
      await api.update(items[index].id, { position: other })
      await api.update(items[other].id, { position: index })
      await client.invalidateQueries({ queryKey: ['reports'] })
    } catch (error) {
      setToast(errorMessage(error))
    }
  }
  const ready =
    health.data?.database && health.data?.analytics_database && health.data?.model_configured
  const landing = page === 'analysis' && !currentId && !ask.isPending
  return (
    <div className="app-shell">
      {sidebar && (
        <button
          className="sidebar-scrim"
          onClick={() => setSidebar(false)}
          aria-label="Close navigation"
        />
      )}
      <aside className={`sidebar ${sidebar ? 'is-open' : ''}`}>
        <button className="brand" onClick={newAnalysis} aria-label="AeroVista home">
          <span className="brand-mark">
            <Plane size={20} strokeWidth={1.8} />
          </span>
          <span>
            AeroVista<small>INTELLIGENCE</small>
          </span>
        </button>
        <button className="new-analysis" onClick={newAnalysis} disabled={ask.isPending}>
          <Plus size={17} />
          New analysis
        </button>
        <nav aria-label="Main navigation">
          <button
            className={page === 'analysis' ? 'nav-item active' : 'nav-item'}
            onClick={() => {
              setPage('analysis')
              setSidebar(false)
            }}
          >
            <MessageSquare size={17} />
            Analysis workspace
          </button>
          <button
            className={page === 'dashboard' ? 'nav-item active' : 'nav-item'}
            onClick={() => {
              setPage('dashboard')
              setSidebar(false)
            }}
          >
            <LayoutDashboard size={17} />
            My dashboard
            {reports.data?.length ? (
              <span className="count-badge">{reports.data.length}</span>
            ) : null}
          </button>
        </nav>
        <div className="history-heading">RECENT ANALYSES</div>
        <div className="history-list">
          {history.isLoading ? (
            <div className="history-empty">Loading conversations…</div>
          ) : history.error ? (
            <button className="text-button" onClick={() => history.refetch()}>
              Retry history
            </button>
          ) : !history.data?.length ? (
            <div className="history-empty">Your explorations will appear here.</div>
          ) : (
            history.data.map((item) => (
              <button
                key={item.id}
                title={item.question}
                disabled={ask.isPending}
                className={`history-item ${item.id === currentId && page === 'analysis' ? 'selected' : ''}`}
                onClick={() => {
                  setCurrentId(item.id)
                  setPage('analysis')
                  setSidebar(false)
                  ask.reset()
                }}
              >
                <MessageSquare size={13} />
                <span>{item.title}</span>
              </button>
            ))
          )}
        </div>
        <div className="sidebar-bottom">
          <div className="dataset-card">
            <span className="dataset-icon">
              <Database size={16} />
            </span>
            <div>
              <strong>AeroVista demo data</strong>
              <span>{health.data?.booking_count ?? '—'} bookings · PostgreSQL</span>
            </div>
            <i className={health.data?.database ? 'connection-dot' : 'connection-dot offline'} />
          </div>
          <button className="profile" onClick={() => setSettings(true)}>
            <span className="avatar">AV</span>
            <span>
              <strong>Demo workspace</strong>
              <small>Your personal analytics</small>
            </span>
            <Settings2 size={16} />
          </button>
        </div>
      </aside>
      <main className="main-panel">
        <header className="topbar">
          <div>
            <button
              className="icon-button mobile-menu"
              onClick={() => setSidebar(true)}
              aria-label="Open navigation"
            >
              <Menu size={20} />
            </button>
            <span className="workspace-title">
              {page === 'dashboard' ? 'My dashboard' : 'Analysis workspace'}
            </span>
            <span className="demo-badge">DEMO</span>
          </div>
          <div>
            <span className="connection-label">
              <i className={health.data?.database ? 'connection-dot' : 'connection-dot offline'} />
              {health.data?.database
                ? 'Data connected'
                : health.isLoading
                  ? 'Connecting…'
                  : 'Data unavailable'}
            </span>
            <button
              className="icon-button"
              onClick={() => setTheme(theme === 'light' ? 'dark' : 'light')}
              aria-label={`Switch to ${theme === 'light' ? 'dark' : 'light'} mode`}
            >
              {theme === 'light' ? <Moon size={18} /> : <Sun size={18} />}
            </button>
            <button
              className="icon-button"
              onClick={() => setSettings(true)}
              aria-label="Workspace information"
            >
              <CircleHelp size={18} />
            </button>
          </div>
        </header>
        {page === 'dashboard' ? (
          <div className="dashboard-content">
            <div className="page-intro">
              <span className="eyebrow">YOUR PERSONAL VIEW</span>
              <h1>A little clarity, always on hand.</h1>
              <p>Saved insights from your conversations, ready when you need them.</p>
            </div>
            <div className="dashboard-toolbar">
              <span>{reports.data?.length || 0} saved reports</span>
              <button className="secondary-button" onClick={newAnalysis}>
                <Plus size={15} />
                New analysis
              </button>
            </div>
            {reports.isLoading ? (
              <div className="skeleton" />
            ) : reports.error ? (
              <div className="error-box" role="alert">
                {errorMessage(reports.error)}
                <button onClick={() => reports.refetch()}>Retry</button>
              </div>
            ) : !reports.data?.length ? (
              <div className="dashboard-empty">
                <span className="empty-icon">
                  <Bookmark size={27} />
                </span>
                <h2>Your insights belong here.</h2>
                <p>
                  Ask a question, then save the report to build a dashboard around what matters to
                  you.
                </p>
                <button className="primary-button" onClick={newAnalysis}>
                  Start an analysis
                  <ArrowRight size={16} />
                </button>
              </div>
            ) : (
              <div className="dashboard-reports">
                {reports.data.map((report, index) => (
                  <DashboardCard
                    key={report.id}
                    report={report}
                    index={index}
                    total={reports.data.length}
                    move={(direction) => moveReport(index, direction)}
                    notify={setToast}
                  />
                ))}
              </div>
            )}
          </div>
        ) : (
          <div className={`analysis-workspace ${landing ? 'landing' : ''}`}>
            {landing ? (
              <div className="welcome">
                <div className="welcome-symbol">
                  <Plane size={30} strokeWidth={1.4} />
                  <span className="sparkle-small">✦</span>
                </div>
                <div className="eyebrow">AEROVISTA INTELLIGENCE</div>
                <h1>Where will your curiosity take you?</h1>
                <p>
                  Turn your airline data into a clearer picture.
                  <br />
                  Ask a question. Find a pattern. Make your next move.
                </p>
                <div className="suggestions">
                  {questions.map(({ icon: Icon, label, text, tint }) => (
                    <button
                      key={label}
                      className="suggestion"
                      onClick={() => submit(undefined, text)}
                    >
                      <span className={`suggestion-icon ${tint}`}>
                        <Icon size={19} />
                      </span>
                      <strong>{label}</strong>
                      <span>{text}</span>
                      <ArrowRight size={15} className="suggestion-arrow" />
                    </button>
                  ))}
                </div>
                <div className="source-note">
                  <Database size={13} />
                  Synthetic airline data<span>·</span>
                  <span>Reference date {health.data?.reference_date || '2026-10-26'}</span>
                </div>
              </div>
            ) : (
              <div className="conversation" aria-label="Analysis conversation">
                {thread.isLoading && currentId && <div className="skeleton" />}
                {thread.error && (
                  <div className="error-box">
                    {errorMessage(thread.error)}
                    <button onClick={() => thread.refetch()}>Retry</button>
                  </div>
                )}
                {analyses.map((analysis) => (
                  <div className="conversation-turn" key={analysis.id}>
                    <div className="user-message">{analysis.question}</div>
                    <article className="assistant-message">
                      <div className="assistant-label">
                        <span className="assistant-mark">
                          <Sparkles size={16} />
                        </span>
                        <strong>AeroVista</strong>
                        <span>Analysis</span>
                      </div>
                      <h2>{analysis.snapshot.title}</h2>
                      <ReportRenderer snapshot={analysis.snapshot} />
                      <div className="report-actions">
                        <button
                          className="secondary-button"
                          onClick={() => setSaveAnalysis(analysis)}
                        >
                          <Bookmark size={14} />
                          Save to dashboard
                        </button>
                        <span>Generated {dateLabel(analysis.created_at)}</span>
                      </div>
                    </article>
                  </div>
                ))}
                {ask.isPending && (
                  <div className="conversation-turn">
                    <div className="user-message">{pendingQuestion}</div>
                    <div className="generation-state" role="status" aria-live="polite">
                      <span className="assistant-mark">
                        <Sparkles size={17} className="pulse" />
                      </span>
                      <div>
                        <strong>I’ll look into that for you.</strong>
                        <p>
                          I’m checking the airline data and preparing your report. This may take a
                          minute or two.
                        </p>
                        <div className="loading-track">
                          <span />
                        </div>
                      </div>
                    </div>
                  </div>
                )}
                <div ref={bottom} />
              </div>
            )}
            <div className="composer-area">
              {ask.error && (
                <div className="error-box" role="alert">
                  {errorMessage(ask.error)} Your question is kept below so you can adjust it and
                  retry.
                </div>
              )}
              {!health.isLoading && !ready && (
                <div className="setup-note">
                  {health.error || !health.data?.database
                    ? 'Start the backend and PostgreSQL to connect the airline dataset.'
                    : !health.data?.model_configured
                      ? 'Add your OpenAI key to the server .env and restart the backend to begin.'
                      : 'The read-only analytics connection needs attention.'}
                </div>
              )}
              <form className="composer" onSubmit={submit} aria-busy={ask.isPending}>
                <textarea
                  ref={input}
                  value={draft}
                  disabled={ask.isPending}
                  onChange={(event) => setDraft(event.target.value)}
                  maxLength={2000}
                  rows={2}
                  placeholder={
                    ask.isPending
                      ? 'Preparing your report… You can ask another question when it’s ready.'
                      : currentId
                        ? 'Ask a follow-up about this analysis…'
                        : 'Ask anything about your airline data…'
                  }
                  aria-label="Ask an analytical question"
                  onKeyDown={(event) => {
                    if (
                      event.key === 'Enter' &&
                      !event.shiftKey &&
                      !event.nativeEvent.isComposing
                    ) {
                      event.preventDefault()
                      submit()
                    }
                  }}
                />
                <div className="composer-bottom">
                  <span>
                    <Sparkles size={14} />
                    Airline analyst
                    <ChevronDown size={12} />
                  </span>
                  <button
                    className="send-button"
                    disabled={draft.trim().length < 3 || ask.isPending}
                    aria-label="Send question"
                  >
                    {ask.isPending ? (
                      <LoaderCircle size={17} className="spin" />
                    ) : (
                      <ArrowUp size={19} />
                    )}
                  </button>
                </div>
              </form>
              <p className="composer-caption">
                AI-generated insights. Check the underlying data before making decisions.
              </p>
            </div>
          </div>
        )}
      </main>
      {saveAnalysis && (
        <SaveDialog
          analysis={saveAnalysis}
          close={() => setSaveAnalysis(null)}
          saved={() => {
            setSaveAnalysis(null)
            client.invalidateQueries({ queryKey: ['reports'] })
            setToast('Saved to your dashboard.')
          }}
        />
      )}
      {settings && (
        <Modal title="Your AeroVista workspace" close={() => setSettings(false)}>
          <div className="settings-body">
            <p>
              A personal workspace for exploring a fictional airline. Every analysis runs against
              the seeded PostgreSQL dataset.
            </p>
            <dl>
              <dt>Model</dt>
              <dd>{health.data?.model || 'Not connected'}</dd>
              <dt>Demo reference date</dt>
              <dd>{health.data?.reference_date || '2026-10-26'}</dd>
              <dt>Background refresh</dt>
              <dd>
                {health.data?.scheduler_enabled
                  ? 'Enabled while the backend is running'
                  : 'Disabled'}
              </dd>
              <dt>Appearance</dt>
              <dd>
                <button
                  className="text-button"
                  onClick={() => setTheme(theme === 'light' ? 'dark' : 'light')}
                >
                  {theme === 'light' ? <Moon size={14} /> : <Sun size={14} />}
                  {theme === 'light' ? 'Use dark mode' : 'Use light mode'}
                </button>
              </dd>
            </dl>
            <p className="field-help">
              Revenue defaults to completed payments in USD. The demo reference date keeps
              time-based questions reproducible. Refreshing updates reports from the current
              database; it does not generate new airline records.
            </p>
          </div>
        </Modal>
      )}
      {toast && (
        <div className="toast" role="status">
          <span>{toast}</span>
          <button onClick={() => setToast('')} aria-label="Dismiss notification">
            <X size={15} />
          </button>
        </div>
      )}
    </div>
  )
}
