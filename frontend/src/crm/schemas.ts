import { z } from 'zod'

export const crmKinds = [
  'record_overview',
  'checklist',
  'document_review',
  'quote_simulator',
  'budget_planner',
  'comparison',
  'cash_flow',
  'activity_timeline',
  'rule_assessment',
  'relationship_graph',
  'milestone_tracker',
  'pipeline',
] as const

const text = z.string().max(2000)
const id = z.number().int().positive()
const amount = z.number().finite()
const record = { id, label: text }
const makeDefinition = <T extends z.ZodRawShape>(shape: T) => ({
  props: z.object({
    title: z.string().max(120),
    description: z.string().max(700),
    rows: z.array(z.object(shape).strict()).max(200),
    referenceDate: z.string(),
  }),
})

export const crmDefinitions = {
  RecordOverview: makeDefinition({
    ...record,
    status: text,
    owner: text,
    description: text,
    amount,
  }),
  Checklist: makeDefinition({ ...record, status: text, owner: text, date: text }),
  DocumentReview: makeDefinition({
    ...record,
    field: text,
    expected: text,
    actual: text,
    source: text,
    status: text,
  }),
  QuoteSimulator: makeDefinition({
    ...record,
    unit_price: amount.nonnegative(),
    quantity: id.max(10000),
    months: id.max(120),
    discount: amount.min(0).max(100),
    setup_fee: amount.nonnegative(),
  }),
  BudgetPlanner: makeDefinition({
    ...record,
    income: amount.nonnegative(),
    expenses: amount.nonnegative(),
    budget: amount.nonnegative(),
  }),
  Comparison: makeDefinition({ ...record, amount, category: text, description: text }),
  CashFlow: makeDefinition({
    ...record,
    date: text,
    amount: amount.nonnegative(),
    category: text,
    direction: z.enum(['Inflow', 'Outflow']),
  }),
  ActivityTimeline: makeDefinition({
    ...record,
    date: text,
    description: text,
    category: text,
    owner: text,
  }),
  RuleAssessment: makeDefinition({
    ...record,
    observed: amount.nullable(),
    threshold: amount,
    operator: z.enum(['gte', 'lte', 'eq']),
    description: text,
  }),
  RelationshipGraph: makeDefinition({ source: text, target: text, relationship: text }),
  MilestoneTracker: makeDefinition({
    ...record,
    status: text,
    date: text,
    owner: text,
    group: text,
  }),
  Pipeline: makeDefinition({ ...record, status: text, amount, owner: text, date: text }),
}
