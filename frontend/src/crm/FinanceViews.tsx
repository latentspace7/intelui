import { label, money, number, dateLabel, type CrmProps } from './format'
import { useMemo, useState } from 'react'
import { ArrowDownLeft, ArrowUpRight, RotateCcw } from 'lucide-react'
import {
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import type { Row } from '../api'
import { boundedNumber, quoteTotals } from './calculations'
import { Badge, Empty, Filter, Panel, Stat } from './shared'

function QuoteScenario({ row }: { row: Row }) {
  const initial = {
    quantity: label(row.quantity),
    months: label(row.months),
    discount: label(row.discount),
  }
  const [inputs, setInputs] = useState(initial)
  const quantity = boundedNumber(inputs.quantity, 1, 10000, true)
  const months = boundedNumber(inputs.months, 1, 120, true)
  const discount = boundedNumber(inputs.discount, 0, 100)
  const valid = quantity !== null && months !== null && discount !== null
  const baseline = quoteTotals(
    number(row.unit_price),
    number(row.quantity),
    number(row.months),
    number(row.discount),
    number(row.setup_fee),
  )
  const totals = valid
    ? quoteTotals(number(row.unit_price), quantity, months, discount, number(row.setup_fee))
    : null
  return (
    <>
      <div className="crm-scenario">
        <div className="crm-scenario-controls">
          <span className="eyebrow">Explore a scenario</span>
          <h4>{label(row.label)}</h4>
          <p>
            {money(number(row.unit_price))} per seat / month
            <br />
            {money(number(row.setup_fee))} one-time setup
          </p>
          {(
            [
              ['quantity', 'Seats', 1, 10000, 1],
              ['months', 'Term in months', 1, 120, 1],
              ['discount', 'Discount (%)', 0, 100, 0.5],
            ] as const
          ).map(([key, title, min, max, step]) => (
            <label className="crm-number-field" key={key}>
              <span>{title}</span>
              <input
                type="number"
                min={min}
                max={max}
                step={step}
                value={inputs[key]}
                onChange={(event) =>
                  setInputs((previous) => ({ ...previous, [key]: event.target.value }))
                }
              />
            </label>
          ))}
          <button className="text-button" onClick={() => setInputs(initial)}>
            <RotateCcw size={14} />
            Reset to saved quote
          </button>
        </div>
        <div className="crm-scenario-result">
          {totals ? (
            <>
              <span className="eyebrow">Scenario total (USD)</span>
              <strong className="crm-hero-value">{money(totals.total)}</strong>
              <span>
                {months} months · {quantity} seats · taxes excluded
              </span>
              <div className="crm-stat-grid">
                <Stat title="Recurring monthly" value={money(totals.monthly)} />
                <Stat title="First month incl. setup" value={money(totals.firstMonth)} />
              </div>
              <div className="crm-baseline">
                <span>Saved quote total</span>
                <b>{money(baseline.total)}</b>
                <span>Scenario difference</span>
                <b>{money(totals.total - baseline.total)}</b>
              </div>
              <details className="crm-formula">
                <summary>How this is calculated</summary>
                <p>
                  Monthly = unit price × seats × (1 − discount / 100), rounded to cents.
                  <br />
                  Contract total = monthly × term + one-time setup fee.
                </p>
              </details>
            </>
          ) : (
            <p className="error-box" role="alert">
              Enter 1–10,000 whole seats, a term of 1–120 whole months, and a discount from 0–100%.
            </p>
          )}
        </div>
      </div>
      <p className="crm-note">
        Scenario controls do not change the saved quote. The product price and setup fee come from
        the database.
      </p>
    </>
  )
}

export function QuoteSimulator(props: CrmProps) {
  const [selected, setSelected] = useState(number(props.rows[0]?.id))
  const row = props.rows.find((row) => row.id === selected) ?? props.rows[0]
  return (
    <Panel
      {...props}
      toolbar={
        <label className="crm-filter">
          <span>Saved quote</span>
          <select
            aria-label="Saved quote"
            value={row ? number(row.id) : ''}
            onChange={(event) => setSelected(Number(event.target.value))}
          >
            {props.rows.map((row) => (
              <option value={number(row.id)} key={number(row.id)}>
                {label(row.label)} · #{label(row.id)}
              </option>
            ))}
          </select>
        </label>
      }
    >
      {row ? <QuoteScenario key={number(row.id)} row={row} /> : <Empty />}
    </Panel>
  )
}

function BudgetScenario({ row }: { row: Row }) {
  const [incomeChange, setIncomeChange] = useState(0)
  const [expenseChange, setExpenseChange] = useState(0)
  const [spend, setSpend] = useState(number(row.budget))
  const income = number(row.income) * (1 + incomeChange / 100)
  const expenses = number(row.expenses) * (1 + expenseChange / 100)
  const surplus = income - expenses - spend
  return (
    <>
      <div className="crm-scenario">
        <div className="crm-scenario-controls">
          <h4>{label(row.label)}</h4>
          <p>Adjust monthly assumptions to explore capacity for additional recurring spend.</p>
          <label className="crm-range">
            <span>
              Income change <b>{incomeChange}%</b>
            </span>
            <input
              aria-label="Income change"
              type="range"
              min={-50}
              max={50}
              step={5}
              value={incomeChange}
              onChange={(event) => setIncomeChange(Number(event.target.value))}
            />
          </label>
          <label className="crm-range">
            <span>
              Expense change <b>{expenseChange}%</b>
            </span>
            <input
              aria-label="Expense change"
              type="range"
              min={-50}
              max={50}
              step={5}
              value={expenseChange}
              onChange={(event) => setExpenseChange(Number(event.target.value))}
            />
          </label>
          <label className="crm-range">
            <span>
              Additional monthly spend <b>{money(spend)}</b>
            </span>
            <input
              aria-label="Additional monthly spend"
              type="range"
              min={0}
              max={Math.max(number(row.budget) * 3, 1000)}
              step={25}
              value={spend}
              onChange={(event) => setSpend(Number(event.target.value))}
            />
          </label>
          <button
            className="text-button"
            onClick={() => {
              setIncomeChange(0)
              setExpenseChange(0)
              setSpend(number(row.budget))
            }}
          >
            <RotateCcw size={14} />
            Reset assumptions
          </button>
        </div>
        <div className="crm-scenario-result">
          <span className="eyebrow">Monthly surplus (USD)</span>
          <strong className={`crm-hero-value ${surplus < 0 ? 'crm-negative' : ''}`}>
            {money(surplus)}
          </strong>
          <span>Income − existing expenses − additional spend</span>
          <div className="crm-stat-grid">
            <Stat title="Scenario income" value={money(income)} />
            <Stat title="Scenario expenses" value={money(expenses)} />
          </div>
          <div className="crm-baseline">
            <span>Recorded spending budget</span>
            <b>{money(number(row.budget))}</b>
            <span>Budget remaining after scenario spend</span>
            <b>{money(number(row.budget) - spend)}</b>
          </div>
          <Badge value={surplus < 0 ? 'Deficit in this scenario' : 'Surplus in this scenario'} />
        </div>
      </div>
      <p className="crm-note">
        Uses the account’s recorded planning assumptions, separately from its cash ledger. Changes
        stay in this view.
      </p>
    </>
  )
}

export function BudgetPlanner(props: CrmProps) {
  const [selected, setSelected] = useState(number(props.rows[0]?.id))
  const row = props.rows.find((row) => row.id === selected) ?? props.rows[0]
  return (
    <Panel
      {...props}
      toolbar={
        <label className="crm-filter">
          <span>Account</span>
          <select
            aria-label="Budget account"
            value={row ? number(row.id) : ''}
            onChange={(event) => setSelected(Number(event.target.value))}
          >
            {props.rows.map((row) => (
              <option key={number(row.id)} value={number(row.id)}>
                {label(row.label)}
              </option>
            ))}
          </select>
        </label>
      }
    >
      {row ? <BudgetScenario key={number(row.id)} row={row} /> : <Empty />}
    </Panel>
  )
}

export function Comparison(props: CrmProps) {
  const [selected, setSelected] = useState(props.rows.slice(0, 3).map((row) => number(row.id)))
  const [order, setOrder] = useState('ascending')
  const rows = props.rows
    .filter((row) => selected.includes(number(row.id)))
    .sort((a, b) => (number(a.amount) - number(b.amount)) * (order === 'ascending' ? 1 : -1))
  const lowest = Math.min(...rows.map((row) => number(row.amount)))
  return (
    <Panel
      {...props}
      toolbar={
        <>
          <div className="crm-option-picker">
            {props.rows.map((row) => (
              <label key={number(row.id)}>
                <input
                  type="checkbox"
                  checked={selected.includes(number(row.id))}
                  onChange={(event) =>
                    setSelected((previous) =>
                      event.target.checked
                        ? [...previous, number(row.id)]
                        : previous.filter((id) => id !== row.id),
                    )
                  }
                />
                {label(row.label)}
              </label>
            ))}
          </div>
          <label className="crm-filter">
            <span>Sort by value</span>
            <select
              aria-label="Comparison order"
              value={order}
              onChange={(event) => setOrder(event.target.value)}
            >
              <option value="ascending">Lowest first</option>
              <option value="descending">Highest first</option>
            </select>
          </label>
        </>
      }
    >
      <div className="crm-comparison-grid">
        {rows.map((row) => (
          <article className="crm-option-card" key={number(row.id)}>
            <Badge value={row.category} />
            <h4>{label(row.label)}</h4>
            <strong>{money(number(row.amount))}</strong>
            <span>Total value · USD</span>
            <p>{label(row.description)}</p>
            <small>
              {number(row.amount) === lowest
                ? 'Lowest value among selected options'
                : `${money(number(row.amount) - lowest)} above the lowest selected value`}
            </small>
          </article>
        ))}
      </div>
      {!rows.length && <Empty>Select an option above to compare it.</Empty>}
    </Panel>
  )
}

export function CashFlow(props: CrmProps) {
  const [category, setCategory] = useState('')
  const [month, setMonth] = useState('')
  const months = [...new Set(props.rows.map((row) => label(row.date).slice(0, 7)))].sort()
  const rows = props.rows.filter(
    (row) =>
      (!category || row.category === category) && (!month || label(row.date).startsWith(month)),
  )
  const monthly = useMemo(() => {
    const groups = new Map<string, { month: string; Inflow: number; Outflow: number }>()
    for (const row of rows) {
      const key = label(row.date).slice(0, 7)
      const point = groups.get(key) ?? { month: key, Inflow: 0, Outflow: 0 }
      if (row.direction === 'Inflow') point.Inflow += number(row.amount)
      if (row.direction === 'Outflow') point.Outflow += number(row.amount)
      groups.set(key, point)
    }
    return [...groups.values()].sort((a, b) => a.month.localeCompare(b.month))
  }, [rows])
  const inflow = monthly.reduce((sum, row) => sum + row.Inflow, 0)
  const outflow = monthly.reduce((sum, row) => sum + row.Outflow, 0)
  return (
    <Panel
      {...props}
      toolbar={
        <>
          <Filter
            name="Cash-flow category"
            value={category}
            options={[...new Set(props.rows.map((row) => label(row.category)))]}
            change={setCategory}
          />
          <Filter name="Cash-flow month" value={month} options={months} change={setMonth} />
        </>
      }
    >
      <div className="crm-stat-grid">
        <Stat title="Recorded inflows" value={money(inflow)} />
        <Stat title="Recorded outflows" value={money(outflow)} />
        <Stat title="Net cash flow" value={money(inflow - outflow)} />
      </div>
      {rows.length ? (
        <>
          <div
            className="crm-cash-chart"
            role="img"
            aria-label="Monthly inflows and outflows; exact entries appear below"
          >
            <ResponsiveContainer width="100%" height={230} minWidth={0}>
              <BarChart data={monthly}>
                <CartesianGrid stroke="var(--border)" vertical={false} />
                <XAxis dataKey="month" tick={{ fill: 'var(--muted)', fontSize: 11 }} />
                <YAxis
                  width={60}
                  tick={{ fill: 'var(--muted)', fontSize: 11 }}
                  tickFormatter={(value) => `${Math.round(Number(value) / 1000)}k`}
                />
                <Tooltip
                  formatter={(value) => money(Number(value))}
                  contentStyle={{
                    background: 'var(--panel)',
                    borderColor: 'var(--border)',
                    borderRadius: 8,
                  }}
                />
                <Legend />
                <Bar dataKey="Inflow" fill="var(--chart-2)" radius={[4, 4, 0, 0]} />
                <Bar dataKey="Outflow" fill="var(--chart-1)" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
          <details className="crm-ledger">
            <summary>Inspect {rows.length} source entries</summary>
            <div className="crm-table-scroll">
              <table>
                <thead>
                  <tr>
                    <th>Date</th>
                    <th>Entry</th>
                    <th>Direction</th>
                    <th>Amount</th>
                  </tr>
                </thead>
                <tbody>
                  {rows.map((row) => (
                    <tr key={number(row.id)}>
                      <td>{dateLabel(row.date)}</td>
                      <td>{label(row.label)}</td>
                      <td>
                        {row.direction === 'Inflow' ? (
                          <ArrowDownLeft size={14} />
                        ) : (
                          <ArrowUpRight size={14} />
                        )}
                        {label(row.direction)}
                      </td>
                      <td>{money(number(row.amount))}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </details>
        </>
      ) : (
        <Empty />
      )}
      <p className="crm-note">
        Totals reflect the selected categories and months within the returned records.
      </p>
    </Panel>
  )
}
