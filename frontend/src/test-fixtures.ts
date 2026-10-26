import { type Snapshot } from './api'

export function fixture(): Snapshot {
  return {
    title: 'Revenue',
    question: 'Show revenue',
    summary: 'Revenue from completed payments.',
    result: {
      sql: 'SELECT travel_class, revenue FROM airline.bookings',
      columns: ['travel_class', 'revenue'],
      rows: [
        { travel_class: 'Economy', revenue: 900 },
        { travel_class: 'Business', revenue: 1200 },
      ],
      row_count: 2,
      duration_ms: 5,
      truncated: false,
      warnings: [],
    },
    presentation: null,
    generated_at: '2026-10-26T10:00:00Z',
    reference_date: '2026-10-26',
    model: 'test-provider',
    ui: [
      {
        version: 'v0.9',
        createSurface: { surfaceId: 'report', catalogId: 'aerovista://analytics/v1' },
      },
      {
        version: 'v0.9',
        updateComponents: {
          surfaceId: 'report',
          components: [
            { id: 'root', component: 'Stack', items: ['kpi', 'table'] },
            {
              id: 'kpi',
              component: 'Metric',
              title: 'Revenue',
              description: 'Completed payments',
              value: 2100,
              format: 'currency',
            },
            {
              id: 'table',
              component: 'DataTable',
              title: 'Revenue by class',
              description: '',
              columns: ['travel_class', 'revenue'],
              rows: [
                { travel_class: 'Economy', revenue: 900 },
                { travel_class: 'Business', revenue: 1200 },
              ],
            },
          ],
        },
      },
    ],
  }
}
