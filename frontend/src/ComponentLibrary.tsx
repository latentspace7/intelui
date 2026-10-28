import { useState } from 'react'
import { useMutation, useQuery } from '@tanstack/react-query'
import {
  ArrowRight,
  Building2,
  Calculator,
  ChartNoAxesCombined,
  CheckSquare,
  CircleDollarSign,
  Columns3,
  FileSearch,
  Flag,
  GitCompareArrows,
  History,
  LayoutGrid,
  LoaderCircle,
  Network,
  RefreshCw,
  ShieldCheck,
  Sparkles,
} from 'lucide-react'
import { api, type Analysis } from './api'
import ReportRenderer from './ReportRenderer'
import type { crmKinds } from './crm/schemas'

const icons = {
  record_overview: Building2,
  checklist: CheckSquare,
  document_review: FileSearch,
  quote_simulator: Calculator,
  budget_planner: CircleDollarSign,
  comparison: GitCompareArrows,
  cash_flow: ChartNoAxesCombined,
  activity_timeline: History,
  rule_assessment: ShieldCheck,
  relationship_graph: Network,
  milestone_tracker: Flag,
  pipeline: Columns3,
}

export default function ComponentLibrary({
  openAnalysis,
  askQuestion,
}: {
  openAnalysis: (analysis: Analysis) => void
  askQuestion: (question: string) => void
}) {
  const [selected, setSelected] = useState<(typeof crmKinds)[number]>('pipeline')
  const catalog = useQuery({ queryKey: ['catalog'], queryFn: api.catalog })
  const preview = useQuery({
    queryKey: ['catalog-preview', selected],
    queryFn: () => api.catalogPreview(selected),
  })
  const open = useMutation({
    mutationFn: () => api.catalogAnalysis(selected),
    onSuccess: openAnalysis,
  })
  const active = catalog.data?.find((item) => item.id === selected)
  return (
    <div className="component-library">
      <div className="library-intro">
        <div>
          <h1>Component library</h1>
          <p>Twelve interactive views, each running real read-only SQL against the demo data.</p>
        </div>
        <span className="library-count">
          <LayoutGrid size={18} />
          <strong>12</strong>components
        </span>
      </div>
      <div className="library-layout">
        <nav className="library-nav" aria-label="Analytics components">
          <h2 className="eyebrow">Components</h2>
          {catalog.isPending ? (
            <div className="skeleton" />
          ) : catalog.error ? (
            <div className="error-box" role="alert">
              {catalog.error.message}
              <button className="text-button" onClick={() => catalog.refetch()}>
                Retry catalog
              </button>
            </div>
          ) : (
            catalog.data?.map((item) => {
              const Icon = icons[item.id]
              return (
                <button
                  key={item.id}
                  className={item.id === selected ? 'active' : ''}
                  aria-current={item.id === selected ? 'page' : undefined}
                  disabled={open.isPending}
                  onClick={() => {
                    setSelected(item.id)
                    open.reset()
                  }}
                >
                  <Icon size={17} />
                  <span>{item.title}</span>
                </button>
              )
            })
          )}
          <div className="library-data-note">
            <span className="connection-dot" />
            <p>Examples query PostgreSQL directly. No model call is needed to explore.</p>
          </div>
        </nav>
        <div className="library-preview">
          <div className="library-preview-tools">
            <span className="demo-badge">Synthetic data</span>
            <button
              className="text-button"
              onClick={() => preview.refetch()}
              disabled={preview.isFetching}
            >
              <RefreshCw size={14} className={preview.isFetching ? 'spin' : ''} />
              Reload data
            </button>
          </div>
          {preview.isPending ? (
            <div className="skeleton" />
          ) : preview.error ? (
            <div className="error-box" role="alert">
              {preview.error.message}
              <button className="text-button" onClick={() => preview.refetch()}>
                Retry example
              </button>
            </div>
          ) : (
            preview.data && <ReportRenderer key={selected} snapshot={preview.data} />
          )}
          {active && (
            <div className="library-followup">
              <div>
                <Sparkles size={19} />
                <span>
                  <strong>Use this component in a conversation</strong>
                  <small>{active.prompt}</small>
                </span>
              </div>
              <div>
                <button
                  className="secondary-button"
                  onClick={() => askQuestion(active.prompt)}
                  disabled={open.isPending}
                >
                  Ask AI about this
                </button>
                <button
                  className="primary-button"
                  onClick={() => open.mutate()}
                  disabled={open.isPending || !preview.data}
                >
                  {open.isPending ? (
                    <LoaderCircle className="spin" size={15} />
                  ) : (
                    <ArrowRight size={15} />
                  )}
                  Open as report
                </button>
              </div>
              {open.error && (
                <p className="error-box" role="alert">
                  {open.error.message}
                </p>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
