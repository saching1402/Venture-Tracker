import { useMemo, useState } from 'react'
import DataTable, { type Col } from '../components/DataTable'
import { Kpi, Select, Star, Tags } from '../components/ui'
import { money, uniq } from '../lib/format'
import { go } from '../lib/route'
import { useData } from '../store/data'
import type { ManagerRow } from '../types'

export default function Managers() {
  const { managers, companies, coById, meta } = useData()
  const [q, setQ] = useState('')
  const [type, setType] = useState('')
  const [stage, setStage] = useState('')
  const [focus, setFocus] = useState('')

  const real = useMemo(() => managers.filter(m => !m.is_stub), [managers])
  const topByMgr = useMemo(() => {
    const out: Record<string, string[]> = {}
    for (const c of companies) {
      if (c.legacy) continue
      for (const id of c.tracked_gp_ids) (out[id] ??= []).push(c.id)
    }
    return out // companies are already sorted by valuation desc
  }, [companies])

  const rows = real.filter(m =>
    (!type || m.type === type) && (!stage || m.stages.includes(stage)) && (!focus || m.focus_areas.includes(focus)) &&
    (!q || [m.name, m.hq, m.type, ...m.key_people_names].join(' ').toLowerCase().includes(q.toLowerCase())))

  const cols: Col<ManagerRow>[] = [
    { key: 'w', header: '', cell: m => <Star kind="manager" id={m.id} /> },
    { key: 'name', header: 'Manager', sort: m => m.name, cell: m => <><div className="nm">{m.name}</div><div className="sub">{m.type}</div></> },
    { key: 'hq', header: 'HQ', sort: m => m.hq, cell: m => m.hq.replace(/, USA$/, '') },
    { key: 'aum', header: 'AUM', numeric: true, sort: m => m.aum_usd_bn, cell: m => money(m.aum_usd_bn) },
    { key: 'fund', header: 'Latest fund', numeric: true, sort: m => m.latest_fund?.size_usd_bn,
      cell: m => m.latest_fund ? <>{money(m.latest_fund.size_usd_bn)}<div className="sub">{m.latest_fund.vintage ?? ''}</div></> : '—' },
    { key: 'stages', header: 'Stages', wrap: true, cell: m => <Tags items={m.stages} /> },
    { key: 'focus', header: 'Focus', wrap: true, cell: m => <Tags items={m.focus_areas} max={4} cls="focus" /> },
    { key: 'n', header: 'Cos.', numeric: true, sort: m => m.n_companies, cell: m => m.n_companies },
    { key: 'top', header: 'Largest holdings', wrap: true,
      cell: m => (topByMgr[m.id] ?? []).slice(0, 3).map(id => (
        <span key={id} className="tag gp" onClick={e => { e.stopPropagation(); go(`co-${id}`) }}>{coById[id]?.name}</span>)) },
  ]

  return (
    <>
      <div className="atl-kpis">
        <Kpi label="Managers tracked" value={real.length} sub="Seed to crossover growth" />
        <Kpi label="Combined AUM" value={money(meta?.combined_aum_usd_bn)} sub="Where disclosed or reported" />
        <Kpi label="Portfolio companies" value={companies.length} sub="Deduplicated across managers" />
        <Kpi label="Held by 5+ tracked managers" value={meta?.consensus_names ?? '—'} sub="Consensus names" dark gold />
      </div>
      <div className="tbl-wrap" style={{ marginBottom: 0, borderBottom: 'none', borderBottomLeftRadius: 0, borderBottomRightRadius: 0 }}>
        <div className="tbl-bar">
          <input id="mq" className="tbl-search" type="search" placeholder="Search manager, person or city" value={q} onChange={e => setQ(e.target.value)} />
          <Select id="mtype" value={type} onChange={setType} options={uniq(real.map(m => m.type))} all="All types" />
          <Select id="mstage" value={stage} onChange={setStage} options={uniq(real.flatMap(m => m.stages))} all="All stages" />
          <Select id="mfocus" value={focus} onChange={setFocus} options={uniq(real.flatMap(m => m.focus_areas))} all="All focus areas" />
          <span className="tbl-ct">{rows.length} managers</span>
        </div>
      </div>
      <DataTable rows={rows} cols={cols} rowKey={m => m.id} onRowClick={m => go(`gp-${m.id}`)} initialSort={{ key: 'aum', dir: -1 }} />
    </>
  )
}
