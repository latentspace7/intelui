import { label, type CrmProps } from './format'
import { useMemo, useState } from 'react'
import { Network, RotateCcw } from 'lucide-react'
import { Empty, Panel, SearchField } from './shared'

export function RelationshipGraph(props: CrmProps) {
  const [selected, setSelected] = useState('')
  const [search, setSearch] = useState('')
  const [zoom, setZoom] = useState(1)
  const nodes = useMemo(
    () => [...new Set(props.rows.flatMap((row) => [label(row.source), label(row.target)]))],
    [props.rows],
  )
  const focused = selected || nodes[0]
  const connections = props.rows.filter((row) => row.source === focused || row.target === focused)
  const neighborNames = new Set(
    connections.flatMap((row) => [label(row.source), label(row.target)]),
  )
  const shown = nodes.filter((name) => name === focused || neighborNames.has(name))
  const positions = new Map(
    shown.map((name, index) => {
      const other = shown.filter((node) => node !== focused)
      const angle = (other.indexOf(name) / Math.max(other.length, 1)) * Math.PI * 2 - Math.PI / 2
      return [
        name,
        name === focused
          ? { x: 360, y: 220 }
          : { x: 360 + Math.cos(angle) * 245, y: 220 + Math.sin(angle) * 155, index },
      ]
    }),
  )
  const matches = nodes.filter((name) => name.toLowerCase().includes(search.toLowerCase()))
  return (
    <Panel
      {...props}
      toolbar={
        <>
          <SearchField value={search} change={setSearch} name="Find a relationship node" />
          <label className="crm-filter">
            <span>Focus</span>
            <select
              aria-label="Relationship focus"
              value={focused ?? ''}
              onChange={(event) => setSelected(event.target.value)}
            >
              {nodes.map((name) => (
                <option key={name}>{name}</option>
              ))}
            </select>
          </label>
          <label className="crm-zoom">
            Zoom
            <input
              aria-label="Graph zoom"
              type="range"
              min={0.7}
              max={1.5}
              step={0.1}
              value={zoom}
              onChange={(event) => setZoom(Number(event.target.value))}
            />
          </label>
          <button
            className="text-button"
            onClick={() => {
              setZoom(1)
              setSelected('')
              setSearch('')
            }}
          >
            <RotateCcw size={14} />
            Reset
          </button>
        </>
      }
    >
      {search && (
        <div className="crm-node-matches">
          {matches.map((name) => (
            <button
              className="secondary-button"
              key={name}
              onClick={() => {
                setSelected(name)
                setSearch('')
              }}
            >
              {name}
            </button>
          ))}
          {!matches.length && <Empty>No matching company or contact.</Empty>}
        </div>
      )}
      {!nodes.length ? (
        <Empty />
      ) : (
        <>
          <div
            className="crm-graph-scroll"
            tabIndex={0}
            role="region"
            aria-label="Relationship graph"
          >
            <svg
              viewBox="0 0 720 440"
              style={{ width: `${zoom * 100}%`, minWidth: 560 }}
              role="img"
              aria-label={`Immediate relationships of ${focused}; select nodes below to explore`}
            >
              <title>Relationships around {focused}</title>
              {connections.map((row, index) => {
                const a = positions.get(label(row.source))
                const b = positions.get(label(row.target))
                return (
                  a &&
                  b && (
                    <g key={index}>
                      <line
                        x1={a.x}
                        y1={a.y}
                        x2={b.x}
                        y2={b.y}
                        stroke="var(--muted)"
                        strokeWidth="2"
                      />
                      <rect
                        x={(a.x + b.x) / 2 - 57}
                        y={(a.y + b.y) / 2 - 12}
                        width={114}
                        height={24}
                        rx={12}
                        fill="var(--panel)"
                      />
                      <text
                        x={(a.x + b.x) / 2}
                        y={(a.y + b.y) / 2 + 4}
                        textAnchor="middle"
                        fill="var(--muted)"
                        fontSize="10"
                      >
                        {label(row.relationship).slice(0, 22)}
                      </text>
                    </g>
                  )
                )
              })}
              {shown.map((name) => {
                const position = positions.get(name)!
                const active = name === focused
                return (
                  <g
                    key={name}
                    role="button"
                    tabIndex={0}
                    aria-label={`Focus ${name}`}
                    onClick={() => setSelected(name)}
                    onKeyDown={(event) => {
                      if (event.key === 'Enter' || event.key === ' ') {
                        event.preventDefault()
                        setSelected(name)
                      }
                    }}
                    className="crm-graph-node"
                  >
                    <circle
                      cx={position.x}
                      cy={position.y}
                      r={active ? 38 : 28}
                      fill={active ? 'var(--accent)' : 'var(--accent-soft)'}
                      stroke="var(--accent)"
                      strokeWidth={active ? 0 : 1}
                    />
                    <text
                      x={position.x}
                      y={position.y + 5}
                      textAnchor="middle"
                      fontSize="14"
                      fill={active ? 'var(--panel)' : 'var(--accent)'}
                    >
                      {name
                        .split(' ')
                        .slice(0, 2)
                        .map((word) => word[0])
                        .join('')}
                    </text>
                    <text
                      x={position.x}
                      y={position.y + (active ? 58 : 48)}
                      textAnchor="middle"
                      fill="var(--text)"
                      fontSize="11"
                    >
                      {name.length > 25 ? `${name.slice(0, 23)}…` : name}
                    </text>
                  </g>
                )
              })}
            </svg>
          </div>
          <div className="crm-graph-details">
            <h4>
              <Network size={17} />
              {focused}
            </h4>
            <p>{connections.length} connections in the returned records</p>
            <ul>
              {connections.map((row, index) => (
                <li key={index}>
                  <span>{label(row.relationship)}</span>
                  <button
                    className="text-button"
                    onClick={() =>
                      setSelected(label(row.source === focused ? row.target : row.source))
                    }
                  >
                    {label(row.source === focused ? row.target : row.source)}
                  </button>
                </li>
              ))}
            </ul>
          </div>
        </>
      )}
      <p className="crm-note">
        Shows immediate connections for the selected node. Relationships outside the query result
        are not inferred.
      </p>
    </Panel>
  )
}
