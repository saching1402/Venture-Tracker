import { useMemo, useState } from 'react'
import DataTable, { type Col } from '../components/DataTable'
import { GpChips, Select, Star, StatusPill } from '../components/ui'
import { clip, downloadCsv, money, num, uniq, xmult } from '../lib/format'
import { go } from '../lib/route'
import { useData } from '../store/data'
import type { CompanyRow } from '../types'

export function companyCols(): Col<CompanyRow>[] {
  return [
    { key: 'w', header: '', cell: c => <Star kind="company" id={c.id} /> },
    { key: 'name', header: 'Company', sort: c => c.name, wrap: true,
      cell: c => <><div className="nm">{c.name}</div><div className="sub">{clip(c.description, 90)}</div></> },
    { key: 'sector', header: 'Sector', sort: c => c.sector, cell: c => <>{c.sector}<div className="sub">{c.focus_tags[0] ?? ''}</div></> },
    { key: 'status', header: 'Status', sort: c => c.status, cell: c => <StatusPill status={c.status} /> },
    { key: 'val', header: 'Valuation', numeric: true, sort: c => c.latest_valuation_usd_bn,
      cell: c => <>{money(c.latest_valuation_usd_bn)}<div className="sub">{c.valuation_stale && <span className="stale">stale</span>}{c.valuation_date}</div></> },
    { key: 'step', header: 'Step-up', numeric: true, title: 'Latest valuation ÷ earliest recorded post-money',
      sort: c => (c.legacy ? null : c.step_up_x),
      cell: c => c.legacy ? <span className="sub">legacy</span> : c.step_up_x ? <><span className="pos">{xmult(c.step_up_x)}</span><div className="sub">since {(c.first_mark_date || '').slice(0, 4)}</div></> : '—' },
    { key: 'rev', header: 'ARR / Rev.', numeric: true, sort: c => c.revenue_usd_bn,
      cell: c => num(c.revenue_usd_bn) !== null ? <>{money(c.revenue_usd_bn)}<div className="sub">{clip(c.revenue_metric, 26)} {c.revenue_date}</div></> : '—' },
    { key: 'evrev', header: 'Val / Rev', numeric: true, sort: c => c.ev_rev_x, cell: c => xmult(c.ev_rev_x) },
    { key: 'growth', header: 'Growth', wrap: true, cell: c => <span title={c.growth}>{clip(c.growth, 60) || '—'}</span> },
    { key: 'raised', header: 'Raised', numeric: true, sort: c => c.total_raised_usd_bn, cell: c => money(c.total_raised_usd_bn) },
    { key: 'gps', header: 'Tracked managers', wrap: true, sort: c => c.tracked_gp_ids.length, cell: c => <GpChips ids={c.tracked_gp_ids} /> },
  ]
}

const VAL_OPTS: [string, string][] = [['1', '≥ $1B'], ['5', '≥ $5B'], ['10', '≥ $10B'], ['50', '≥ $50B'], ['100', '≥ $100B']]

export default function Companies() {
  const { companies, managers, watch, meta } = useData()
  const [f, setF] = useState({ q: '', sector: '', focus: '', status: '', gp: '', minv: '', w: false, legacy: false })
  const set = (k: keyof typeof f) => (v: string | boolean) => setF(s => ({ ...s, [k]: v }))

  const rows = useMemo(() => {
    const q = f.q.toLowerCase(), minv = num(f.minv)
    return companies.filter(c =>
      (!f.sector || c.sector === f.sector) && (!f.focus || c.focus_tags.includes(f.focus)) &&
      (!f.status || (c.status || 'Private').toLowerCase().startsWith(f.status.toLowerCase())) &&
      (!f.gp || c.tracked_gp_ids.includes(f.gp)) && (minv === null || (c.latest_valuation_usd_bn ?? 0) >= minv) &&
      (!f.w || watch.companies.includes(c.id)) && (f.legacy || !c.legacy || !!q) &&
      (!q || [c.name, c.description, c.ceo, c.hq, c.other_investors.join(' ')].join(' ').toLowerCase().includes(q)))
  }, [companies, f, watch.companies])

  const total = rows.reduce((s, c) => s + (c.valuation_stale || c.legacy ? 0 : c.latest_valuation_usd_bn ?? 0), 0)
  const mgrName = Object.fromEntries(managers.map(m => [m.id, m.name]))

  function exportCsv() {
    downloadCsv(`gp-atlas-companies-${meta?.asof ?? 'export'}.csv`,
      ['Company', 'Sector', 'Focus', 'Status', 'Valuation $bn', 'Valuation date', 'Label', 'ARR/Rev $bn', 'Metric', 'Rev date', 'Growth',
        'Profitability', 'Raised $bn', 'Step-up x', 'Val/Rev x', 'Tracked managers', 'Other investors', 'CEO', 'HQ', 'Founded', 'Description'],
      rows.map(c => [c.name, c.sector, c.focus_tags.join('; '), c.status, c.latest_valuation_usd_bn, c.valuation_date, c.valuation_label,
        c.revenue_usd_bn, c.revenue_metric, c.revenue_date, c.growth, c.profitability, c.total_raised_usd_bn, c.step_up_x, c.ev_rev_x,
        c.tracked_gp_ids.map(id => mgrName[id] ?? id).join('; '), c.other_investors.join('; '), c.ceo, c.hq, c.founded, c.description]))
  }

  return (
    <>
      <div className="tbl-wrap" style={{ marginBottom: 0, borderBottomLeftRadius: 0, borderBottomRightRadius: 0, borderBottom: 'none' }}>
        <div className="tbl-bar">
          <input id="cq" className="tbl-search" type="search" placeholder="Search company, CEO or investor" value={f.q} onChange={e => set('q')(e.target.value)} />
          <Select id="csec" value={f.sector} onChange={set('sector')} options={uniq(companies.map(c => c.sector))} all="All sectors" />
          <Select id="cfoc" value={f.focus} onChange={set('focus')} options={uniq(companies.flatMap(c => c.focus_tags))} all="All focus tags" />
          <Select id="cst" value={f.status} onChange={set('status')} options={['Private', 'Public', 'Acquired', 'Shut down']} all="Any status" />
          <Select id="cgp" value={f.gp} onChange={set('gp')} all="Any tracked manager"
            options={managers.filter(m => !m.is_stub).map(m => [m.id, m.name] as [string, string]).sort((a, b) => a[1].localeCompare(b[1]))} />
          <Select id="cmin" value={f.minv} onChange={set('minv')} options={VAL_OPTS} all="Any valuation" />
          <label className="chk"><input id="cw" type="checkbox" checked={f.w} onChange={e => set('w')(e.target.checked)} /> Watchlist only</label>
          <label className="chk" title="Pre-2010 holdings long since listed or sold (Apple, Amazon, Alphabet…)">
            <input id="cl" type="checkbox" checked={f.legacy} onChange={e => set('legacy')(e.target.checked)} /> Include legacy exits
          </label>
          <button className="btn" onClick={exportCsv}>Export CSV</button>
          <span className="tbl-ct">{rows.length} companies · {money(total)}</span>
        </div>
      </div>
      <DataTable rows={rows} cols={companyCols()} rowKey={c => c.id} onRowClick={c => go(`co-${c.id}`)} initialSort={{ key: 'val', dir: -1 }} />
    </>
  )
}
