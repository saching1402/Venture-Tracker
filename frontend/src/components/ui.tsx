import type { ReactNode } from 'react'
import { useData } from '../store/data'
import { shortName, statusKind } from '../lib/format'
import { go } from '../lib/route'
import { Logo } from './Logo'

export function Lbl({ l }: { l?: string | null }) {
  if (!l) return null
  return <span className={`lbl lbl-${l === 'N/A' ? 'NA' : l}`}>{l}</span>
}

export function StatusPill({ status }: { status: string }) {
  const k = statusKind(status)
  const cls = { priv: 'badge-gray', pub: 'badge-green', acq: 'badge-gold', dead: 'badge-red' }[k]
  const main = (status || 'Private').split('(')[0].trim()
  const extra = k !== 'priv' && status.includes('(') ? status.slice(status.indexOf('(') + 1).replace(/\)$/, '') : ''
  return <><span className={`badge ${cls}`}>{main}</span>{extra && <div className="sub">{extra}</div>}</>
}

export function Star({ kind, id }: { kind: 'manager' | 'company'; id: string }) {
  const on = useData(s => (kind === 'manager' ? s.watch.managers : s.watch.companies).includes(id))
  const toggle = useData(s => s.toggleWatch)
  return (
    <button className={`star${on ? ' on' : ''}`} aria-pressed={on} title={on ? 'Remove from watchlist' : 'Add to watchlist'}
      onClick={e => { e.stopPropagation(); void toggle(kind, id) }}>★</button>
  )
}

export function GpChips({ ids, max = 4 }: { ids: string[]; max?: number }) {
  const mgr = useData(s => s.mgrById)
  return (
    <>
      {ids.slice(0, max).map(id => (
        <span key={id} className="tag gp tag-logo" onClick={e => { e.stopPropagation(); go(`gp-${id}`) }}>
          <Logo url={mgr[id]?.website} name={mgr[id]?.name ?? id} size={14} />{shortName(mgr[id]?.name ?? id)}
        </span>
      ))}
      {ids.length > max && <span className="tag">+{ids.length - max}</span>}
    </>
  )
}

export function Tags({ items, max, cls = '' }: { items: string[]; max?: number; cls?: string }) {
  const list = max ? items.slice(0, max) : items
  return <>{list.map(t => <span key={t} className={`tag ${cls}`}>{t}</span>)}{max && items.length > max && <span className="tag">+{items.length - max}</span>}</>
}

export function Kpi({ label, value, sub, dark, gold }: { label: string; value: ReactNode; sub?: string; dark?: boolean; gold?: boolean }) {
  return (
    <div className={`kpi-card${dark ? ' dk' : ''}${gold ? ' gold-val' : ''}`}>
      <div className="kpi-lbl">{label}</div>
      <div className="kpi-val">{value}</div>
      {sub && <div className="kpi-sub">{sub}</div>}
    </div>
  )
}

export function Fact({ k, v, big }: { k: string; v: ReactNode; big?: boolean }) {
  return <div><div className="k">{k}</div><div className={`v${big ? ' big' : ''}`}>{v}</div></div>
}

export function Card({ title, children, right }: { title?: ReactNode; children: ReactNode; right?: ReactNode }) {
  return (
    <div className="card">
      {title && <div style={{ display: 'flex', alignItems: 'baseline', gap: 8 }}><div className="card-title">{title}</div>{right && <div style={{ marginLeft: 'auto' }}>{right}</div>}</div>}
      {children}
    </div>
  )
}

export function Sources({ list, verified }: { list?: string[]; verified?: string }) {
  return (
    <div className="card">
      {!!list?.length && (
        <details>
          <summary className="note" style={{ cursor: 'pointer' }}>Sources ({list.length})</summary>
          <ul className="srcs" style={{ marginTop: 6 }}>
            {list.map(u => <li key={u}>{/^https?:/.test(u) ? <a href={u} target="_blank" rel="noopener noreferrer">{u}</a> : <span className="note">{u}</span>}</li>)}
          </ul>
        </details>
      )}
      <p className="note" style={{ marginTop: 6 }}>Last verified {verified || '—'}</p>
    </div>
  )
}

export function Select({ id, value, onChange, options, all }: { id: string; value: string; onChange: (v: string) => void; options: (string | [string, string])[]; all: string }) {
  return (
    <select id={id} className="tbl-sel" value={value} onChange={e => onChange(e.target.value)}>
      <option value="">{all}</option>
      {options.map(o => { const [v, l] = Array.isArray(o) ? o : [o, o]; return <option key={v} value={v}>{l}</option> })}
    </select>
  )
}
