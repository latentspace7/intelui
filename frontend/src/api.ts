import { z } from 'zod'
import { crmKinds } from './crm/schemas'

export const scalar = z.union([z.string(), z.number(), z.boolean(), z.null()])
export const rowSchema = z.record(scalar)
export type Row = z.infer<typeof rowSchema>
export const formatSchema = z.enum(['number', 'currency', 'percent', 'text'])
export type ValueFormat = z.infer<typeof formatSchema>
const sectionSchema = z.object({
  kind: z.enum(['metric', 'table', 'bar', 'line', 'donut', 'insight', ...crmKinds]),
  title: z.string(),
  description: z.string(),
  columns: z.array(z.string()),
  x: z.string().nullable(),
  y: z.array(z.string()),
  value_column: z.string().nullable(),
  row_index: z.number().nullable(),
  format: formatSchema,
  bindings: z.array(z.object({ field: z.string(), column: z.string() })).optional(),
})
export const snapshotSchema = z.object({
  title: z.string(),
  question: z.string(),
  summary: z.string(),
  result: z.object({
    sql: z.string(),
    columns: z.array(z.string()),
    rows: z.array(rowSchema),
    row_count: z.number(),
    duration_ms: z.number(),
    truncated: z.boolean(),
    warnings: z.array(z.string()),
  }),
  presentation: z
    .object({ title: z.string(), summary: z.string(), sections: z.array(sectionSchema) })
    .nullable(),
  ui: z.array(z.record(z.unknown())),
  generated_at: z.string(),
  reference_date: z.string(),
  model: z.string(),
  catalog_example: z.string().nullish(),
  model_cost: z
    .object({
      currency: z.literal('USD'),
      estimated_usd: z.number().nonnegative().nullable(),
      model_calls: z.number().int().nonnegative(),
      input_tokens: z.number().int().nonnegative(),
      cached_input_tokens: z.number().int().nonnegative(),
      cache_write_tokens: z.number().int().nonnegative(),
      output_tokens: z.number().int().nonnegative(),
      pricing_date: z.string(),
      unavailable_reason: z.string().nullable(),
    })
    .nullish(),
})
export const analysisSchema = z.object({
  id: z.string(),
  parent_id: z.string().nullable(),
  question: z.string(),
  snapshot: snapshotSchema,
  created_at: z.string(),
})
export const historySchema = z.array(
  z.object({
    id: z.string(),
    parent_id: z.string().nullable(),
    question: z.string(),
    title: z.string(),
    created_at: z.string(),
  }),
)
export const reportSchema = z.object({
  id: z.string(),
  analysis_id: z.string(),
  title: z.string(),
  question: z.string(),
  snapshot: snapshotSchema,
  position: z.number(),
  created_at: z.string(),
  last_refreshed_at: z.string(),
  last_attempt_at: z.string().nullable(),
  refresh_interval_hours: z.union([
    z.literal(0),
    z.literal(1),
    z.literal(4),
    z.literal(12),
    z.literal(24),
  ]),
  next_refresh_at: z.string().nullable(),
  refresh_status: z.string(),
  refresh_error: z.string().nullable(),
})
export const healthSchema = z.object({
  status: z.enum(['ok', 'degraded']),
  database: z.boolean(),
  analytics_database: z.boolean(),
  model_configured: z.boolean(),
  model: z.string(),
  reference_date: z.string(),
  scheduler_enabled: z.boolean(),
  booking_count: z.number().nullable(),
  company_count: z.number().nullish(),
  contact_count: z.number().nullish(),
  deal_count: z.number().nullish(),
})
const catalogSchema = z.array(
  z.object({
    id: z.enum(crmKinds),
    title: z.string(),
    description: z.string(),
    prompt: z.string(),
  }),
)
export type Analysis = z.infer<typeof analysisSchema>
export type Snapshot = z.infer<typeof snapshotSchema>
export type Report = z.infer<typeof reportSchema>

async function request<T>(path: string, schema: z.ZodType<T>, options?: RequestInit): Promise<T> {
  let response: Response
  try {
    response = await fetch(`/api${path}`, {
      ...options,
      headers: { 'Content-Type': 'application/json' },
    })
  } catch {
    throw new Error('Could not reach IntelUI. Check the backend service and try again.')
  }
  if (!response.ok) {
    const body = await response.json().catch(() => null)
    throw new Error(body?.error?.message || 'Something went wrong. Please try again.')
  }
  const body = response.status === 204 ? undefined : await response.json()
  const parsed = schema.safeParse(body)
  if (!parsed.success)
    throw new Error(
      'The server returned an unsupported report. Please retry or update the application.',
    )
  return parsed.data
}

export const api = {
  catalog: () => request('/catalog', catalogSchema),
  catalogPreview: (kind: string) => request(`/catalog/${encodeURIComponent(kind)}`, snapshotSchema),
  catalogAnalysis: (kind: string) =>
    request(`/catalog/${encodeURIComponent(kind)}/analyses`, analysisSchema, { method: 'POST' }),
  crmStatus: (
    entity: 'tasks' | 'document_fields',
    id: number,
    expected_status: string,
    status: string,
    expected_label: string,
    expected_field: string | null = null,
  ) =>
    request(`/crm/${entity}/${id}`, z.object({ id: z.number(), status: z.string() }), {
      method: 'PATCH',
      body: JSON.stringify({ expected_status, status, expected_label, expected_field }),
    }),
  health: () => request('/health', healthSchema),
  history: () => request('/analyses', historySchema),
  thread: (id: string) => request(`/analyses/${id}/thread`, z.array(analysisSchema)),
  ask: (question: string, parent_id: string | null) =>
    request('/analyses', analysisSchema, {
      method: 'POST',
      body: JSON.stringify({ question, parent_id }),
    }),
  reports: () => request('/reports', z.array(reportSchema)),
  save: (analysis_id: string, title: string, refresh_interval_hours: number) =>
    request('/reports', reportSchema, {
      method: 'POST',
      body: JSON.stringify({ analysis_id, title, refresh_interval_hours }),
    }),
  update: (
    id: string,
    changes: { title?: string; refresh_interval_hours?: number; position?: number },
  ) => request(`/reports/${id}`, reportSchema, { method: 'PATCH', body: JSON.stringify(changes) }),
  remove: (id: string) => request(`/reports/${id}`, z.undefined(), { method: 'DELETE' }),
  refresh: (id: string) => request(`/reports/${id}/refresh`, reportSchema, { method: 'POST' }),
}
