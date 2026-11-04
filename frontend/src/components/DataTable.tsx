import { useMemo, useState, type ReactNode } from 'react'

export interface Col<T> {
  key: string
  header: ReactNode
  cell: (row: T) => ReactNode
  /** Sort value; omit or set `sortable: false` to disable sorting on this column */
  sort?: (row: T) => string | number | null | undefined
  sortable?: boolean
  numeric?: boolean
  wrap?: boolean
  title?: string
}

interface Props<T> {
  rows: T[]
  cols: Col<T>[]
  rowKey: (row: T) => string
  onRowClick?: (row: T) => void
  initialSort?: { key: string; dir: 1 | -1 }
  pageSize?: number
  empty?: string
}

/** Sortable table in the Mindari .tbl-wrap style, with incremental "show more". */
export default function DataTable<T>({ rows, cols, rowKey, onRowClick, initialSort, pageSize = 150, empty }: Props<T>) {
  const [sort, setSort] = useState(initialSort ?? null)
  const [limit, setLimit] = useState(pageSize)

  const sorted = useMemo(() => {
    if (!sort) return rows
    const col = cols.find(c => c.key === sort.key)
    if (!col?.sort) return rows
    const get = col.sort
    return [...rows].sort((a, b) => {
      const x = get(a), y = get(b)
      const nx = x === null || x === undefined || x === '', ny = y === null || y === undefined || y === ''
      if (nx && ny) return 0
      if (nx) return 1
      if (ny) return -1
      if (typeof x === 'string' || typeof y === 'string') return sort.dir * String(x).localeCompare(String(y))
      return sort.dir * ((x as number) - (y as number))
    })
  }, [rows, cols, sort])

  const vis = sorted.slice(0, limit)

  return (
    <div className="tbl-wrap">
      <table>
        <thead>
          <tr>
            {cols.map(c => {
              const can = !!c.sort && c.sortable !== false
              const active = sort?.key === c.key
              return (
                <th key={c.key} title={c.title}
                  className={[c.numeric ? 'n' : '', can ? '' : 'ns', active ? 'sact' : ''].join(' ')}
                  onClick={() => can && setSort(s => s && s.key === c.key ? { key: c.key, dir: (s.dir * -1) as 1 | -1 } : { key: c.key, dir: c.numeric ? -1 : 1 })}
                  aria-sort={active ? (sort!.dir > 0 ? 'ascending' : 'descending') : undefined}>
                  {c.header}
                  {can && <i className={`sarr${active ? '' : ' dim'}`}>{active && sort!.dir > 0 ? '▲' : '▼'}</i>}
                </th>
              )
            })}
          </tr>
        </thead>
        <tbody>
          {vis.map(r => (
            <tr key={rowKey(r)} className={onRowClick ? 'click' : ''}
              onClick={e => { if (onRowClick && !(e.target as HTMLElement).closest('button,a,.tag.gp')) onRowClick(r) }}>
              {cols.map(c => <td key={c.key} className={[c.numeric ? 'n' : '', c.wrap ? 'wrap' : ''].join(' ')}>{c.cell(r)}</td>)}
            </tr>
          ))}
          {!vis.length && (
            <tr><td colSpan={cols.length}><div className="empty-state" style={{ minHeight: 120 }}>{empty ?? 'Nothing matches these filters.'}</div></td></tr>
          )}
        </tbody>
      </table>
      {sorted.length > limit && (
        <div className="tbl-more">
          <button className="pb" onClick={() => setLimit(l => l + pageSize)}>
            Show {Math.min(pageSize, sorted.length - limit)} more of {sorted.length - limit} remaining
          </button>
        </div>
      )}
    </div>
  )
}
