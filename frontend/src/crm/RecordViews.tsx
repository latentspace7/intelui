import { label, money, number, dateLabel, type CrmProps } from './format'
import { useState } from 'react'
import type { Row } from '../api'
import {
  Building2,
  CalendarDays,
  CheckCircle2,
  ChevronRight,
  FileText,
  Flag,
  MessageSquare,
  UserRound,
} from 'lucide-react'
import { Badge, Empty, Filter, Panel, SearchField, Stat, StatusControl } from './shared'

export function RecordOverview(props: CrmProps) {
  const [search, setSearch] = useState('')
  const [status, setStatus] = useState('')
  const [selected, setSelected] = useState<number | null>(null)
  const rows = props.rows.filter(
    (row) =>
      (!status || row.status === status) &&
      `${row.label} ${row.owner}`.toLowerCase().includes(search.toLowerCase()),
  )
  const active = rows.find((row) => row.id === selected) ?? rows[0]
  return (
    <Panel
      {...props}
      toolbar={
        <>
          <SearchField value={search} change={setSearch} name="Search accounts" />
          <Filter
            name="Account status"
            value={status}
            options={[...new Set(props.rows.map((row) => label(row.status)))]}
            change={setStatus}
          />
          <span className="crm-count">{rows.length} accounts</span>
        </>
      }
    >
      {!active ? (
        <Empty />
      ) : (
        <div className="crm-master-detail">
          <div className="crm-record-list">
            {rows.map((row) => (
              <button
                key={number(row.id)}
                className={row.id === active.id ? 'selected' : ''}
                onClick={() => setSelected(number(row.id))}
              >
                <Building2 size={18} />
                <span>
                  <strong>{label(row.label)}</strong>
                  <small>{label(row.owner)}</small>
                </span>
                <ChevronRight size={14} />
              </button>
            ))}
          </div>
          <div className="crm-record-detail">
            <span className="crm-large-icon">
              <Building2 size={27} />
            </span>
            <Badge value={active.status} />
            <h4>{label(active.label)}</h4>
            <p>{label(active.description)}</p>
            <dl>
              <dt>Account owner</dt>
              <dd>{label(active.owner)}</dd>
              <dt>Record ID</dt>
              <dd>#{label(active.id)}</dd>
              <dt>Reported value · USD</dt>
              <dd>{money(number(active.amount))}</dd>
            </dl>
            <small>
              Measure and scope follow the report description. Select another account to inspect its
              record.
            </small>
          </div>
        </div>
      )}
    </Panel>
  )
}

export function Checklist(props: CrmProps) {
  const [status, setStatus] = useState('')
  const [search, setSearch] = useState('')
  const [changes, setChanges] = useState<Record<number, string>>({})
  const data: (Row & { status: string })[] = props.rows.map((row) => ({
    ...row,
    status: changes[number(row.id)] ?? label(row.status),
  }))
  const rows = data.filter(
    (row) =>
      (!status || row.status === status) &&
      label(row.label).toLowerCase().includes(search.toLowerCase()),
  )
  const complete = data.filter((row) => row.status === 'Complete').length
  return (
    <Panel
      {...props}
      toolbar={
        <>
          <SearchField value={search} change={setSearch} name="Search tasks" />
          <Filter
            name="Task status"
            value={status}
            options={['Outstanding', 'In progress', 'Complete']}
            change={setStatus}
          />
        </>
      }
    >
      <div className="crm-progress">
        <span>
          <CheckCircle2 size={16} />
          {complete} of {data.length} complete
        </span>
        <progress aria-label="Task completion" value={complete} max={data.length || 1} />
      </div>
      <div className="crm-task-list">
        {rows.map((row) => (
          <div className="crm-task" key={number(row.id)}>
            <span className={`crm-task-indicator ${row.status === 'Complete' ? 'done' : ''}`}>
              <CheckCircle2 size={18} />
            </span>
            <div className="crm-task-info">
              <strong>{label(row.label)}</strong>
              <span>
                {label(row.owner)} · Due {dateLabel(row.date)}
              </span>
              <Badge
                value={
                  row.status !== 'Complete' && label(row.date) < props.referenceDate
                    ? 'Overdue'
                    : row.status
                }
              />
            </div>
            <StatusControl
              entity="tasks"
              id={number(row.id)}
              status={row.status}
              recordLabel={label(row.label)}
              onSaved={(value) =>
                setChanges((previous) => ({ ...previous, [number(row.id)]: value }))
              }
            />
          </div>
        ))}
      </div>
      {!rows.length && <Empty />}
      <p className="crm-note">
        Status changes are saved to the source data with an audit entry. Dates are compared with{' '}
        {props.referenceDate}.
      </p>
    </Panel>
  )
}

export function DocumentReview(props: CrmProps) {
  const documents = [...new Set(props.rows.map((row) => label(row.label)))]
  const [selected, setSelected] = useState(documents[0] ?? '')
  const rows = props.rows.filter((row) => row.label === selected)
  const [focused, setFocused] = useState<number | null>(null)
  const active = rows.find((row) => row.id === focused) ?? rows[0]
  return (
    <Panel
      {...props}
      toolbar={
        <label className="crm-filter">
          <span>Document</span>
          <select
            aria-label="Document"
            value={selected}
            onChange={(event) => {
              setSelected(event.target.value)
              setFocused(null)
            }}
          >
            {documents.map((name) => (
              <option key={name}>{name}</option>
            ))}
          </select>
        </label>
      }
    >
      {!active ? (
        <Empty />
      ) : (
        <div className="crm-document-layout">
          <div className="crm-document-source">
            <div>
              <FileText size={18} />
              <span>Synthetic source document</span>
            </div>
            <h4>{selected}</h4>
            <div className="crm-source-lines">
              {label(active.source)
                .split('\n')
                .map((line, index) => (
                  <p
                    key={index}
                    className={line.startsWith(`${label(active.field)}:`) ? 'highlighted' : ''}
                  >
                    {line}
                  </p>
                ))}
            </div>
            <small>
              Text and extracted fields are seeded examples. No OCR or external document service is
              used.
            </small>
          </div>
          <div className="crm-field-list">
            {rows.map((row) => {
              const mismatch = row.expected !== row.actual
              return (
                <div key={number(row.id)} className={`crm-field ${mismatch ? 'mismatch' : ''}`}>
                  <button className="crm-field-heading" onClick={() => setFocused(number(row.id))}>
                    <strong>{label(row.field)}</strong>
                    <span>
                      {mismatch ? 'Values differ' : 'Values match'}
                      <ChevronRight size={13} />
                    </span>
                  </button>
                  <dl>
                    <dt>Declared</dt>
                    <dd>{label(row.expected)}</dd>
                    <dt>In document</dt>
                    <dd>{label(row.actual)}</dd>
                  </dl>
                  <StatusControl
                    key={`${row.id}-${row.status}`}
                    entity="document_fields"
                    id={number(row.id)}
                    status={label(row.status)}
                    recordLabel={label(row.label)}
                    field={label(row.field)}
                    mismatch={mismatch}
                  />
                </div>
              )
            })}
          </div>
        </div>
      )}
    </Panel>
  )
}

export function ActivityTimeline(props: CrmProps) {
  const [category, setCategory] = useState('')
  const [search, setSearch] = useState('')
  const rows = props.rows
    .filter(
      (row) =>
        (!category || row.category === category) &&
        `${row.label} ${row.description}`.toLowerCase().includes(search.toLowerCase()),
    )
    .sort((a, b) => label(b.date).localeCompare(label(a.date)))
  return (
    <Panel
      {...props}
      toolbar={
        <>
          <Filter
            name="Activity type"
            value={category}
            options={[...new Set(props.rows.map((row) => label(row.category)))]}
            change={setCategory}
          />
          <SearchField value={search} change={setSearch} name="Search activity" />
          <span className="crm-count">{rows.length} events</span>
        </>
      }
    >
      <div className="crm-timeline">
        {rows.map((row) => (
          <div className="crm-timeline-item" key={number(row.id)}>
            <span className="crm-timeline-dot">
              <MessageSquare size={15} />
            </span>
            <details>
              <summary>
                <span>
                  <small>
                    {dateLabel(row.date)} · {label(row.category)}
                  </small>
                  <strong>{label(row.label)}</strong>
                </span>
                <ChevronRight size={15} />
              </summary>
              <p>{label(row.description)}</p>
              <small>
                Recorded by {label(row.owner)} · Event #{label(row.id)}
              </small>
            </details>
          </div>
        ))}
      </div>
      {!rows.length && <Empty />}
    </Panel>
  )
}

export function MilestoneTracker(props: CrmProps) {
  const groups = [...new Set(props.rows.map((row) => label(row.group)))]
  const [group, setGroup] = useState(groups[0] ?? '')
  const rows = props.rows.filter((row) => row.group === group)
  const complete = rows.filter((row) => row.status === 'Complete').length
  return (
    <Panel
      {...props}
      toolbar={
        <label className="crm-filter">
          <span>Account</span>
          <select
            aria-label="Milestone account"
            value={group}
            onChange={(event) => setGroup(event.target.value)}
          >
            {groups.map((name) => (
              <option key={name}>{name}</option>
            ))}
          </select>
        </label>
      }
    >
      <div className="crm-stat-grid">
        <Stat title="Completed milestones" value={`${complete} / ${rows.length}`} />
        <Stat title="Blocked" value={rows.filter((row) => row.status === 'Blocked').length} />
        <Stat title="Progress" value={`${Math.round((100 * complete) / (rows.length || 1))}%`} />
      </div>
      <ol className="crm-milestones">
        {rows.map((row, index) => (
          <li key={number(row.id)} className={row.status === 'Complete' ? 'complete' : ''}>
            <span className="crm-milestone-number">
              {row.status === 'Complete' ? <CheckCircle2 size={19} /> : index + 1}
            </span>
            <div>
              <strong>{label(row.label)}</strong>
              <span>
                <CalendarDays size={13} />
                {dateLabel(row.date)}
                <UserRound size={13} />
                {label(row.owner)}
              </span>
            </div>
            <Badge value={row.status} />
          </li>
        ))}
      </ol>
      {!rows.length && <Empty />}
    </Panel>
  )
}

export function Pipeline(props: CrmProps) {
  const [owner, setOwner] = useState('')
  const [search, setSearch] = useState('')
  const [selected, setSelected] = useState<number | null>(null)
  const rows = props.rows.filter(
    (row) =>
      (!owner || row.owner === owner) &&
      label(row.label).toLowerCase().includes(search.toLowerCase()),
  )
  const knownStages = ['Lead', 'Qualified', 'Proposal', 'Negotiation', 'Won', 'Lost']
  const stages = [
    ...knownStages,
    ...new Set(
      rows.map((row) => label(row.status)).filter((status) => !knownStages.includes(status)),
    ),
  ]
  const active = rows.find((row) => row.id === selected)
  const open = rows.filter((row) => !['Won', 'Lost'].includes(label(row.status)))
  return (
    <Panel
      {...props}
      toolbar={
        <>
          <SearchField value={search} change={setSearch} name="Search deals" />
          <Filter
            name="Deal owner"
            value={owner}
            options={[...new Set(props.rows.map((row) => label(row.owner)))]}
            change={setOwner}
          />
        </>
      }
    >
      <div className="crm-stat-grid">
        <Stat
          title="Open pipeline"
          value={money(open.reduce((sum, row) => sum + number(row.amount), 0))}
          detail={`${open.length} open deals`}
        />
        <Stat
          title="Won contract value"
          value={money(
            rows
              .filter((row) => row.status === 'Won')
              .reduce((sum, row) => sum + number(row.amount), 0),
          )}
          detail="Contract value, not cash received"
        />
        <Stat
          title="Past expected close"
          value={open.filter((row) => label(row.date) < props.referenceDate).length}
          detail={`As of ${props.referenceDate}`}
        />
      </div>
      <div className="crm-pipeline" role="region" aria-label="Deal stages" tabIndex={0}>
        {stages.map((stage) => {
          const deals = rows.filter((row) => row.status === stage)
          return (
            <section className="crm-stage" key={stage}>
              <div className="crm-stage-heading">
                <strong>{stage}</strong>
                <span>{deals.length}</span>
                <small>{money(deals.reduce((sum, row) => sum + number(row.amount), 0))}</small>
              </div>
              {deals.map((row) => (
                <button
                  key={number(row.id)}
                  className={`crm-deal ${selected === row.id ? 'selected' : ''}`}
                  onClick={() => setSelected(number(row.id))}
                >
                  <strong>{label(row.label)}</strong>
                  <b>{money(number(row.amount))}</b>
                  <span>{label(row.owner)}</span>
                  <small>
                    <CalendarDays size={12} />
                    {dateLabel(row.date)}
                  </small>
                </button>
              ))}
              {!deals.length && <small className="crm-stage-empty">No deals</small>}
            </section>
          )
        })}
      </div>
      {active && (
        <div className="crm-selected-record" role="status">
          <Flag size={18} />
          <div>
            <strong>{label(active.label)}</strong>
            <p>
              {label(active.status)} · {label(active.owner)} · Expected close{' '}
              {dateLabel(active.date)}
            </p>
          </div>
          <b>{money(number(active.amount))}</b>
          <button className="text-button" onClick={() => setSelected(null)}>
            Close details
          </button>
        </div>
      )}
      <p className="crm-note">
        Totals cover the returned records. Select a deal to inspect it; stage changes are not made
        from this view.
      </p>
    </Panel>
  )
}

export function RuleAssessment(props: CrmProps) {
  const [status, setStatus] = useState('')
  const evaluated = props.rows.map((row) => ({
    row,
    outcome:
      row.observed === null
        ? 'Needs information'
        : (
              row.operator === 'gte'
                ? number(row.observed) >= number(row.threshold)
                : row.operator === 'lte'
                  ? number(row.observed) <= number(row.threshold)
                  : row.observed === row.threshold
            )
          ? 'Passed'
          : 'Failed',
  }))
  const rows = evaluated.filter((item) => !status || item.outcome === status)
  return (
    <Panel
      {...props}
      toolbar={
        <>
          <Filter
            name="Rule result"
            value={status}
            options={['Passed', 'Failed', 'Needs information']}
            change={setStatus}
          />
          <span className="crm-count">Recorded demo rules</span>
        </>
      }
    >
      <div className="crm-stat-grid">
        {['Passed', 'Failed', 'Needs information'].map((outcome) => (
          <Stat
            key={outcome}
            title={outcome}
            value={evaluated.filter((item) => item.outcome === outcome).length}
          />
        ))}
      </div>
      <div className="crm-rule-list">
        {rows.map(({ row, outcome }) => (
          <details key={number(row.id)} className="crm-rule">
            <summary>
              <strong>{label(row.label)}</strong>
              <Badge value={outcome} />
              <ChevronRight size={15} />
            </summary>
            <div>
              <p>{label(row.description)}</p>
              <dl>
                <dt>Recorded observation</dt>
                <dd>{label(row.observed)}</dd>
                <dt>Comparison</dt>
                <dd>
                  {{ gte: 'At least', lte: 'At most', eq: 'Equal to' }[label(row.operator)]}{' '}
                  {label(row.threshold)}
                </dd>
              </dl>
            </div>
          </details>
        ))}
      </div>
      {!rows.length && <Empty />}
      <p className="crm-note">
        Results are calculated from the recorded observation and threshold. These demo checks do not
        make approval or compliance decisions.
      </p>
    </Panel>
  )
}
