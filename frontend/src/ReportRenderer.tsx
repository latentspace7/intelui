import { Component, useEffect, useMemo, useState, type ReactNode } from 'react'
import {
  A2UIProvider,
  A2UIRenderer,
  createCatalog,
  useA2UI,
  useA2UIError,
} from '@copilotkit/a2ui-renderer'
import {
  flexRender,
  getCoreRowModel,
  getPaginationRowModel,
  getSortedRowModel,
  useReactTable,
  type SortingState,
} from '@tanstack/react-table'
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Legend,
  Line,
  LineChart,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import { ArrowDownUp, ChevronLeft, ChevronRight, Database, Lightbulb } from 'lucide-react'
import { z } from 'zod'
import { formatSchema, rowSchema, type Row, type Snapshot, type ValueFormat } from './api'

const colors = Array.from({ length: 12 }, (_, index) => `var(--chart-${index + 1})`)
const humanize = (value: string) =>
  value.replaceAll('_', ' ').replace(/\b\w/g, (c) => c.toUpperCase())

function display(value: unknown, format: ValueFormat = 'text'): string {
  if (value === null || value === undefined) return '—'
  if (typeof value !== 'number') return String(value)
  if (format === 'currency')
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      maximumFractionDigits: 2,
    }).format(value)
  if (format === 'percent')
    return `${new Intl.NumberFormat('en-US', { maximumFractionDigits: 2 }).format(value)}%`
  return new Intl.NumberFormat('en-US', { maximumFractionDigits: 2 }).format(value)
}

function DataTable({ columns, rows, title }: { columns: string[]; rows: Row[]; title: string }) {
  const [sorting, setSorting] = useState<SortingState>([])
  const definitions = useMemo(
    () =>
      columns.map((key) => ({
        accessorKey: key,
        header: humanize(key),
        cell: (info: { getValue: () => unknown }) => display(info.getValue()),
      })),
    [columns],
  )
  const table = useReactTable({
    data: rows,
    columns: definitions,
    state: { sorting },
    onSortingChange: setSorting,
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
    getPaginationRowModel: getPaginationRowModel(),
    initialState: { pagination: { pageSize: 8 } },
  })
  return (
    <div className="table-block">
      <div className="table-scroll" tabIndex={0} role="region" aria-label={`${title} data`}>
        <table>
          <caption className="sr-only">{title}</caption>
          <thead>
            {table.getHeaderGroups().map((group) => (
              <tr key={group.id}>
                {group.headers.map((header) => (
                  <th
                    key={header.id}
                    scope="col"
                    aria-sort={
                      header.column.getIsSorted() === 'asc'
                        ? 'ascending'
                        : header.column.getIsSorted() === 'desc'
                          ? 'descending'
                          : 'none'
                    }
                  >
                    <button onClick={header.column.getToggleSortingHandler()}>
                      {flexRender(header.column.columnDef.header, header.getContext())}
                      <ArrowDownUp size={12} />
                    </button>
                  </th>
                ))}
              </tr>
            ))}
          </thead>
          <tbody>
            {table.getRowModel().rows.map((row) => (
              <tr key={row.id}>
                {row.getVisibleCells().map((cell) => (
                  <td key={cell.id}>{flexRender(cell.column.columnDef.cell, cell.getContext())}</td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div className="table-footer">
        <span>{rows.length} records</span>
        <div>
          <button
            aria-label="Previous table page"
            disabled={!table.getCanPreviousPage()}
            onClick={() => table.previousPage()}
          >
            <ChevronLeft size={15} />
          </button>
          <span>
            {table.getState().pagination.pageIndex + 1} / {Math.max(1, table.getPageCount())}
          </span>
          <button
            aria-label="Next table page"
            disabled={!table.getCanNextPage()}
            onClick={() => table.nextPage()}
          >
            <ChevronRight size={15} />
          </button>
        </div>
      </div>
    </div>
  )
}

const common = { title: z.string().max(120), description: z.string().max(700) }
const definitions = {
  Stack: { props: z.object({ items: z.array(z.string()).max(8) }) },
  Metric: {
    props: z.object({
      ...common,
      value: z.union([z.number(), z.string(), z.boolean(), z.null()]),
      format: formatSchema,
    }),
  },
  Narrative: { props: z.object(common) },
  DataTable: {
    props: z.object({
      ...common,
      columns: z.array(z.string()).min(1).max(12),
      rows: z.array(rowSchema).max(500),
    }),
  },
  Chart: {
    props: z.object({
      ...common,
      chartType: z.enum(['bar', 'line', 'donut']),
      x: z.string(),
      y: z.array(z.string()).min(1).max(4),
      rows: z.array(rowSchema).max(60),
      format: formatSchema,
    }),
  },
}

function CategoryTick({
  x = 0,
  y = 0,
  payload,
}: {
  x?: number
  y?: number
  payload?: { value: unknown }
}) {
  const words = String(payload?.value ?? '').split(' ')
  const lines = words.length > 1 ? [words[0], words.slice(1).join(' ')] : words
  return (
    <text x={x} y={y} textAnchor="middle" fill="var(--muted)" fontSize={13}>
      {lines.map((line, index) => (
        <tspan x={x} dy={index === 0 ? 14 : 16} key={index}>
          {line.length > 14 ? `${line.slice(0, 13)}…` : line}
        </tspan>
      ))}
    </text>
  )
}

function ChartPanel(props: z.infer<typeof definitions.Chart.props>) {
  const [showTable, setShowTable] = useState(false)
  const { title, description, rows, x, y, format, chartType } = props
  const categories = [...new Set(rows.map((row) => String(row[x])))].sort()
  const categoryColor = (value: unknown) =>
    colors[categories.indexOf(String(value)) % colors.length]
  const axis = { tick: { fill: 'var(--muted)', fontSize: 13 }, axisLine: false, tickLine: false }
  const legend = (
    <Legend wrapperStyle={{ fontSize: 13 }} formatter={(value) => humanize(String(value))} />
  )
  const tooltip = (
    <Tooltip
      contentStyle={{
        border: '1px solid var(--border)',
        borderRadius: 10,
        background: 'var(--panel)',
        color: 'var(--text)',
        fontSize: 14,
      }}
      formatter={(value) => display(value, format)}
    />
  )
  return (
    <section className="viz-panel chart-panel">
      <div className="viz-heading">
        <div>
          <h3>{title}</h3>
          {description && <p>{description}</p>}
        </div>
        <span className="chart-label">{format === 'currency' ? 'USD' : 'RESULTS'}</span>
      </div>
      <div
        className="chart-container"
        role="img"
        aria-label={`${title}. ${rows.length} data points. Use View data below for exact values.`}
      >
        <ResponsiveContainer width="100%" height={280} minWidth={0}>
          {chartType === 'donut' ? (
            <PieChart>
              {tooltip}
              <Pie
                data={rows}
                dataKey={y[0]}
                nameKey={x}
                innerRadius={70}
                outerRadius={105}
                paddingAngle={3}
              >
                {rows.map((row, i) => (
                  <Cell key={i} fill={categoryColor(row[x])} />
                ))}
              </Pie>
              {legend}
            </PieChart>
          ) : chartType === 'line' ? (
            <LineChart data={rows} margin={{ top: 16, right: 18, left: 8, bottom: 8 }}>
              <CartesianGrid stroke="var(--border)" vertical={false} />
              <XAxis
                dataKey={x}
                {...axis}
                minTickGap={30}
                tickFormatter={(value) => String(value).slice(0, 10)}
              />
              <YAxis
                {...axis}
                width={65}
                tickFormatter={(value) =>
                  new Intl.NumberFormat('en', { notation: 'compact' }).format(value)
                }
              />
              {tooltip}
              {legend}
              {y.map((key, i) => (
                <Line
                  type="monotone"
                  key={key}
                  dataKey={key}
                  stroke={colors[i % colors.length]}
                  strokeWidth={2.5}
                  dot={{ r: 4 }}
                  connectNulls={false}
                />
              ))}
            </LineChart>
          ) : (
            <BarChart data={rows} margin={{ top: 16, right: 8, left: 0, bottom: 8 }}>
              <CartesianGrid stroke="var(--border)" vertical={false} />
              <XAxis
                dataKey={x}
                {...axis}
                tick={<CategoryTick />}
                interval={rows.length <= 6 ? 0 : 'preserveStartEnd'}
                height={48}
                minTickGap={15}
              />
              <YAxis
                {...axis}
                width={45}
                tickFormatter={(value) =>
                  new Intl.NumberFormat('en', { notation: 'compact' }).format(value)
                }
              />
              {tooltip}
              {y.length > 1 && legend}
              {y.map((key, i) => (
                <Bar
                  key={key}
                  dataKey={key}
                  fill={colors[i % colors.length]}
                  radius={[5, 5, 0, 0]}
                  maxBarSize={64}
                >
                  {y.length === 1 &&
                    rows.map((row, index) => <Cell key={index} fill={categoryColor(row[x])} />)}
                </Bar>
              ))}
            </BarChart>
          )}
        </ResponsiveContainer>
      </div>
      <button
        className="text-button"
        onClick={() => setShowTable(!showTable)}
        aria-expanded={showTable}
      >
        <Database size={13} />
        {showTable ? 'Hide data' : 'View data'}
      </button>
      {showTable && <DataTable columns={[x, ...y]} rows={rows} title={title} />}
    </section>
  )
}

const catalog = createCatalog(
  definitions,
  {
    Stack: ({ props, children }) => (
      <div className="report-grid">
        {props.items.map((id: string) => (
          <div className="report-section" key={id}>
            {children(id)}
          </div>
        ))}
      </div>
    ),
    Metric: ({ props }) => (
      <section className="viz-panel metric-panel">
        <span>{props.title}</span>
        <strong>{display(props.value, props.format)}</strong>
        <p>{props.description}</p>
      </section>
    ),
    Narrative: ({ props }) => (
      <section className="insight-panel">
        <Lightbulb size={18} />
        <div>
          <h3>{props.title}</h3>
          <p>{props.description}</p>
        </div>
      </section>
    ),
    DataTable: ({ props }) => (
      <section className="viz-panel">
        <div className="viz-heading">
          <div>
            <h3>{props.title}</h3>
            {props.description && <p>{props.description}</p>}
          </div>
        </div>
        <DataTable {...props} />
      </section>
    ),
    Chart: ({ props }) => <ChartPanel {...props} />,
  },
  { catalogId: 'aerovista://analytics/v1', includeBasicCatalog: false },
)

const componentSchema = z.discriminatedUnion('component', [
  definitions.Stack.props.extend({ id: z.string(), component: z.literal('Stack') }).strict(),
  definitions.Metric.props.extend({ id: z.string(), component: z.literal('Metric') }).strict(),
  definitions.Narrative.props
    .extend({ id: z.string(), component: z.literal('Narrative') })
    .strict(),
  definitions.DataTable.props
    .extend({ id: z.string(), component: z.literal('DataTable') })
    .strict(),
  definitions.Chart.props.extend({ id: z.string(), component: z.literal('Chart') }).strict(),
])
const messagesSchema = z.tuple([
  z
    .object({
      version: z.literal('v0.9'),
      createSurface: z
        .object({
          surfaceId: z.literal('report'),
          catalogId: z.literal('aerovista://analytics/v1'),
        })
        .strict(),
    })
    .strict(),
  z
    .object({
      version: z.literal('v0.9'),
      updateComponents: z
        .object({
          surfaceId: z.literal('report'),
          components: z.array(componentSchema).min(2).max(9),
        })
        .strict(),
    })
    .strict(),
])

function Surface({ messages }: { messages: Record<string, unknown>[] }) {
  const { processMessages, clearSurfaces } = useA2UI()
  const error = useA2UIError()
  const parsed = useMemo(() => messagesSchema.safeParse(messages), [messages])
  useEffect(() => {
    clearSurfaces()
    if (parsed.success) processMessages(parsed.data)
  }, [parsed, processMessages, clearSurfaces])
  if (!parsed.success || error)
    return (
      <div role="alert" className="error-box">
        This report contains an unsupported presentation. Refresh it to generate a new one.
      </div>
    )
  return <A2UIRenderer surfaceId="report" fallback={<div className="skeleton" />} />
}

class RendererBoundary extends Component<{ children: ReactNode }, { failed: boolean }> {
  state = { failed: false }
  static getDerivedStateFromError() {
    return { failed: true }
  }
  render() {
    return this.state.failed ? (
      <div className="error-box" role="alert">
        The report could not be displayed. Its query and saved data are still available below.
      </div>
    ) : (
      this.props.children
    )
  }
}

export default function ReportRenderer({ snapshot }: { snapshot: Snapshot }) {
  const cost = snapshot.model_cost
  const costLabel = !cost
    ? 'Cost not recorded'
    : cost.estimated_usd === null
      ? 'Cost unavailable'
      : `Est. ${new Intl.NumberFormat('en-US', {
          style: 'currency',
          currency: 'USD',
          minimumFractionDigits: 2,
          maximumFractionDigits: 6,
        }).format(cost.estimated_usd)} USD`
  return (
    <div className="generated-report">
      <p className="analysis-summary">{snapshot.summary}</p>
      {snapshot.result.rows.length === 0 ? (
        <div className="empty-data">
          <Database size={24} />
          <strong>No matching records</strong>
          <span>Try widening the date range or changing a filter.</span>
        </div>
      ) : (
        <RendererBoundary key={snapshot.generated_at}>
          <A2UIProvider catalog={catalog}>
            <Surface messages={snapshot.ui} />
          </A2UIProvider>
        </RendererBoundary>
      )}
      <details className="query-details">
        <summary>
          <Database size={13} />
          Query details
          <span className="query-cost">{costLabel}</span>
          <span className="query-stats">
            {snapshot.result.row_count} rows · {snapshot.result.duration_ms.toFixed(0)} ms
          </span>
        </summary>
        <div className="query-inner">
          <div className="query-meta">
            <span className="status-pill">Executed successfully</span>
            <span>{snapshot.model}</span>
            <span>Reference date: {snapshot.reference_date}</span>
          </div>
          {cost && (
            <div className="cost-details">
              <p>
                {cost.model_calls} model {cost.model_calls === 1 ? 'call' : 'calls'} ·{' '}
                {cost.input_tokens.toLocaleString()} input tokens ·{' '}
                {cost.output_tokens.toLocaleString()} output tokens
              </p>
              <p>
                {cost.cached_input_tokens.toLocaleString()} cached input tokens ·{' '}
                {cost.cache_write_tokens.toLocaleString()} cache-write tokens
              </p>
              <p>
                {cost.estimated_usd === null
                  ? cost.unavailable_reason
                  : `Estimated model cost for this generation, including any SQL repair. Uses API token usage and published prices as of ${cost.pricing_date}; excludes hosting, database costs, and taxes. A report refresh replaces this with the latest refresh cost.`}
              </p>
            </div>
          )}
          <pre>
            <code>{snapshot.result.sql}</code>
          </pre>
          {snapshot.result.warnings.map((warning, i) => (
            <p key={i}>{warning}</p>
          ))}
          <details>
            <summary>Returned data</summary>
            <DataTable
              title="Query results"
              columns={snapshot.result.columns}
              rows={snapshot.result.rows}
            />
          </details>
        </div>
      </details>
    </div>
  )
}
