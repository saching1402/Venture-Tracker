/**
 * Shortlisted: companies (directs / co-investments) and funds tracked closely across rounds.
 * Two priority tracks (mine vs Claude's, L1-L3) with a full change log, web refresh per item or for all,
 * news feed, progress marks and notes.
 */
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { useEffect, useMemo, useRef, useState } from 'react'
import { PointsView } from '../components/Commentary'
import DataTable, { type Col } from '../components/DataTable'
import Drawer from '../components/Drawer'
import { Card, Fact, Kpi, Lbl, StatusPill } from '../components/ui'
import ValuationChart from '../components/ValuationChart'
import { api, errorText } from '../lib/api'
import { clip, money, usdm, xmult } from '../lib/format'
import { closeDrawer, go } from '../lib/route'
import { useData } from '../store/data'
import { useResearch } from '../store/research'
import type { Level, ShortlistData, SlItem, SlNews } from '../types'

const KEY = ['shortlist']
const LEVELS: Level[] = ['L1', 'L2', 'L3']
const LV_RANK: Record<string, number> = { L1: 1, L2: 2, L3: 3, '': 9 }
const KIND_LABEL = { company: 'Direct / co-investment', fund: 'Fund / GP' }

export function useShortlist() {
  const q = useQuery({
    queryKey: KEY,
    queryFn: () => api.get<ShortlistData>('/shortlist/').then(r => r.data),
    refetchInterval: query => {
      const d = query.state.data
      return d && (d.active > 0 || d.items.some(i => i.research_status === 'queued' || i.research_status === 'running')) ? 6000 : false
    },
  })
  // when refreshes finish, reload the tracker so new marks show on the other tabs too
  const wasActive = useRef(false)
  const active = q.data?.active ?? 0
  useEffect(() => {
    if (wasActive.current && active === 0) { void useData.getState().load(); void useResearch.getState().refresh() }
    wasActive.current = active > 0
  }, [active])
  return q
}

const day = (iso: string | null | undefined) =>
  iso ? new Date(iso).toLocaleDateString('en-GB', { day: '2-digit', month: 'short', year: 'numeric' }) : '—'

function ago(iso: string | null): string {
  if (!iso) return 'never'
  const d = Math.floor((Date.now() - new Date(iso).getTime()) / 86_400_000)
  return d <= 0 ? 'today' : d === 1 ? 'yesterday' : d < 60 ? `${d}d ago` : day(iso)
}

export function LevelPill({ level, title }: { level: Level; title?: string }) {
  return <span className={`lv lv-${level || 'none'}`} title={title}>{level || '—'}</span>
}

function Momentum({ m }: { m: SlItem['momentum'] }) {
  if (!m) return <span className="note">—</span>
  const [sym, cls, t] = { up: ['▲', 'mo-up', 'Improving'], flat: ['▬', 'mo-flat', 'Steady'], down: ['▼', 'mo-down', 'Deteriorating'] }[m]
  return <span className={cls} title={t}>{sym}</span>
}

function RefreshState({ i }: { i: SlItem }) {
  if (i.research_status === 'queued' || i.research_status === 'running')
    return <span className="badge badge-gold">{i.research_status === 'running' ? 'refreshing' : 'queued'}</span>
  if (i.research_status === 'failed') return <span className="badge badge-red" title={i.last_error}>failed</span>
  return <span className="note">{ago(i.last_refreshed_at)}</span>
}

const latestNews = (i: SlItem): SlNews | undefined => i.news[0]
const lastRound = (i: SlItem) => {
  const r = (i.company?.rounds ?? []).filter(x => x.post_money_usd_bn)
  return r[r.length - 1]
}
const latestFund = (i: SlItem) => [...(i.manager?.funds ?? [])].sort((a, b) => (b.vintage ?? 0) - (a.vintage ?? 0))[0]

function useMutations() {
  const qc = useQueryClient()
  const inval = () => qc.invalidateQueries({ queryKey: KEY })
  return {
    async setMine(id: number, level: Level, note = '') { await api.patch(`/shortlist/${id}/`, { my_priority: level, note }); await inval() },
    async save(id: number, body: Record<string, unknown>) { await api.patch(`/shortlist/${id}/`, body); await inval() },
    async refresh(id: number, model: string) { await api.post(`/shortlist/${id}/refresh/`, { model }); await inval(); void useResearch.getState().refresh() },
    async refreshAll(body: Record<string, unknown>) {
      const { data } = await api.post<{ queued: number; skipped: number }>('/shortlist/refresh/', body)
      await inval(); void useResearch.getState().refresh(); return data
    },
    async remove(id: number) { await api.delete(`/shortlist/${id}/`); await inval() },
    async dismiss(newsId: number) { await api.delete(`/shortlist/news/${newsId}/`); await inval() },
    inval,
  }
}

function MineSelect({ i, canEdit }: { i: SlItem; canEdit: boolean }) {
  const { setMine } = useMutations()
  const [busy, setBusy] = useState(false)
  if (!canEdit) return <LevelPill level={i.my_priority} title={i.my_priority_since ? `Since ${day(i.my_priority_since)}` : undefined} />
  return (
    <select aria-label={`My priority for ${i.name}`} className={`lv-sel lv-${i.my_priority || 'none'}`} value={i.my_priority} disabled={busy}
      title={i.my_priority_since ? `Since ${day(i.my_priority_since)}` : 'Not set'}
      onClick={e => e.stopPropagation()}
      onChange={async e => { setBusy(true); try { await setMine(i.id, e.target.value as Level) } finally { setBusy(false) } }}>
      <option value="">—</option>
      {LEVELS.map(l => <option key={l} value={l}>{l}</option>)}
    </select>
  )
}

function RefreshBtn({ i, model, canEdit, enabled }: { i: SlItem; model: string; canEdit: boolean; enabled: boolean }) {
  const { refresh } = useMutations()
  if (!canEdit || !enabled) return null
  const busy = i.research_status === 'queued' || i.research_status === 'running'
  return (
    <button className="pb" disabled={busy} title="Search the web for the latest valuation, performance and news"
      onClick={e => { e.stopPropagation(); void refresh(i.id, model) }}>{busy ? '…' : 'Refresh'}</button>
  )
}

function priorityCols(canEdit: boolean): Col<SlItem>[] {
  return [
    { key: 'mine', header: 'My priority', sort: i => LV_RANK[i.my_priority], cell: i => <MineSelect i={i} canEdit={canEdit} /> },
    {
      key: 'claude', header: "Claude's", sort: i => LV_RANK[i.claude_priority], title: "Claude's priority, set on each refresh",
      cell: i => (
        <span style={{ display: 'inline-flex', gap: 4, alignItems: 'center' }}>
          <LevelPill level={i.claude_priority} title={i.claude_rationale} />
          {i.my_priority && i.claude_priority && i.my_priority !== i.claude_priority && <span className="diff-dot" title="Your priority and Claude's differ">≠</span>}
        </span>
      ),
    },
  ]
}

function newsCol(): Col<SlItem> {
  return {
    key: 'news', header: 'Latest news', wrap: true, sort: i => latestNews(i)?.date ?? '',
    cell: i => {
      const n = latestNews(i)
      return n ? <span>{n.importance === 'high' && <span className="hi-dot" title="High importance" />}<span className="note">{n.date} · </span>{clip(n.headline, 90)}</span> : <span className="note">—</span>
    },
  }
}

function companyCols(canEdit: boolean, enabled: boolean, model: string): Col<SlItem>[] {
  return [
    { key: 'name', header: 'Company', sort: i => i.name, cell: i => <><span className="nm">{i.name}</span><div className="sub">{i.company?.sector || ''}{i.company && i.company.status !== 'Private' ? ` · ${i.company.status}` : ''}</div></> },
    ...priorityCols(canEdit),
    { key: 'val', header: 'Valuation', numeric: true, sort: i => i.company?.latest_valuation_usd_bn, cell: i => <>{money(i.company?.latest_valuation_usd_bn)}<Lbl l={i.company?.valuation_label} /><div className="sub">{i.company?.valuation_date}</div></> },
    { key: 'round', header: 'Last round', sort: i => lastRound(i)?.date, cell: i => { const r = lastRound(i); return r ? <>{r.round}<div className="sub">{r.date} · {money(r.post_money_usd_bn)}</div></> : '—' } },
    { key: 'rev', header: 'ARR / revenue', numeric: true, sort: i => i.company?.revenue_usd_bn, cell: i => <>{money(i.company?.revenue_usd_bn)}<div className="sub">{i.company?.revenue_metric} {i.company?.revenue_date}</div></> },
    { key: 'evr', header: 'Val / rev', numeric: true, sort: i => i.company?.ev_rev_x, cell: i => xmult(i.company?.ev_rev_x) },
    { key: 'mo', header: 'Trend', sort: i => ({ up: 1, flat: 2, down: 3, '': 4 }[i.momentum]), cell: i => <Momentum m={i.momentum} /> },
    newsCol(),
    { key: 'ref', header: 'Refreshed', sort: i => i.last_refreshed_at ?? '', cell: i => <RefreshState i={i} /> },
    { key: 'act', header: '', sortable: false, cell: i => <RefreshBtn i={i} model={model} canEdit={canEdit} enabled={enabled} /> },
  ]
}

function fundCols(canEdit: boolean, enabled: boolean, model: string): Col<SlItem>[] {
  return [
    { key: 'name', header: 'Manager / fund', sort: i => i.name, cell: i => <><span className="nm">{i.name}</span><div className="sub">{i.manager?.type || ''}{i.manager?.hq ? ` · ${i.manager.hq}` : ''}</div></> },
    ...priorityCols(canEdit),
    { key: 'aum', header: 'AUM', numeric: true, sort: i => i.manager?.aum_usd_bn, cell: i => <>{money(i.manager?.aum_usd_bn)}<Lbl l={i.manager?.aum_label} /><div className="sub">{i.manager?.aum_date}</div></> },
    { key: 'fund', header: 'Latest fund', sort: i => latestFund(i)?.vintage, cell: i => { const f = latestFund(i); return f ? <>{f.name}<div className="sub">{f.vintage ?? ''} · {money(f.size_usd_bn)}</div></> : '—' } },
    { key: 'perf', header: 'Performance', wrap: true, cell: i => clip(i.performance || i.manager?.performance, 120) || '—' },
    { key: 'mo', header: 'Trend', sort: i => ({ up: 1, flat: 2, down: 3, '': 4 }[i.momentum]), cell: i => <Momentum m={i.momentum} /> },
    newsCol(),
    { key: 'ref', header: 'Refreshed', sort: i => i.last_refreshed_at ?? '', cell: i => <RefreshState i={i} /> },
    { key: 'act', header: '', sortable: false, cell: i => <RefreshBtn i={i} model={model} canEdit={canEdit} enabled={enabled} /> },
  ]
}

type Section = 'all' | 'company' | 'fund'

export default function Shortlist() {
  const { data, isLoading, error } = useShortlist()
  const { refreshAll } = useMutations()
  const [section, setSection] = useState<Section>('all')
  const [lv, setLv] = useState<Level>('')
  const [by, setBy] = useState<'mine' | 'claude' | 'either'>('either')
  const [q, setQ] = useState('')
  const [model, setModel] = useState('')
  const [adding, setAdding] = useState(false)
  const [msg, setMsg] = useState<string | null>(null)

  useEffect(() => { if (data && !model) setModel(data.defaults.company) }, [data, model])

  const items = useMemo(() => (data?.items ?? []).filter(i => {
    if (lv) {
      const hit = by === 'mine' ? i.my_priority === lv : by === 'claude' ? i.claude_priority === lv : i.my_priority === lv || i.claude_priority === lv
      if (!hit) return false
    }
    const s = q.trim().toLowerCase()
    return !s || `${i.name} ${i.company?.sector ?? ''} ${i.manager?.type ?? ''} ${i.thesis}`.toLowerCase().includes(s)
  }), [data, lv, by, q])

  if (isLoading) return <p className="note">Loading shortlist…</p>
  if (error || !data) return <div className="err-box">{errorText(error)}</div>

  const all = data.items
  const cos = items.filter(i => i.kind === 'company')
  const funds = items.filter(i => i.kind === 'fund')
  const week = new Date(Date.now() - 7 * 86_400_000).toISOString().slice(0, 10)
  const fresh = all.reduce((n, i) => n + i.news.filter(x => x.date >= week).length, 0)
  const differ = all.filter(i => i.my_priority && i.claude_priority && i.my_priority !== i.claude_priority).length
  const running = all.filter(i => i.research_status === 'queued' || i.research_status === 'running').length
  const sort = { key: 'mine', dir: 1 as const }

  const doRefreshAll = async () => {
    setMsg(null)
    try {
      const r = await refreshAll({ model, kind: section === 'all' ? undefined : section, priority: lv || undefined })
      setMsg(r.queued ? `Refreshing ${r.queued} item${r.queued > 1 ? 's' : ''}… this takes a few minutes; results appear as each one finishes.` : 'Everything in view is already refreshing.')
    } catch (e) { setMsg(errorText(e)) }
  }
  const est = data.models.find(m => m.id === model)?.est_company
  const scope = (section === 'all' ? all : all.filter(i => i.kind === section)).filter(i => !lv || i.my_priority === lv || i.claude_priority === lv).length

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
      <div style={{ display: 'flex', flexWrap: 'wrap', gap: 10, alignItems: 'flex-end' }}>
        <div style={{ flex: '1 1 320px' }}>
          <div className="sec-title">Shortlisted</div>
          <div className="sec-sub" style={{ marginBottom: 0 }}>Companies and funds you track closely and plan to back across several rounds or vintages. Each has your priority and Claude's (L1 = most important), with every change logged. Refresh searches the web for the latest valuation, performance and news.</div>
        </div>
        {data.can_edit && (
          <div style={{ display: 'flex', gap: 6, alignItems: 'center', flexWrap: 'wrap' }}>
            {data.enabled && (
              <>
                <select aria-label="Model for refresh" className="tbl-sel" value={model} onChange={e => setModel(e.target.value)}>
                  {data.models.map(m => <option key={m.id} value={m.id}>{m.label.split(' · ')[0]}</option>)}
                </select>
                <button className="btn" disabled={!scope} onClick={() => void doRefreshAll()}
                  title={est ? `About $${(est * scope).toFixed(2)} for ${scope} item${scope === 1 ? '' : 's'}` : undefined}>
                  Refresh {section === 'all' && !lv ? 'all' : 'in view'} ({scope})
                </button>
              </>
            )}
            <button className="btn btn-primary" onClick={() => setAdding(true)}>+ Add to shortlist</button>
          </div>
        )}
      </div>
      {msg && <div className="note" role="status">{msg}</div>}
      {!data.enabled && data.can_edit && <div className="note">Refresh is off until ANTHROPIC_API_KEY is set on Railway.</div>}

      <div className="atl-kpis">
        <Kpi label="Shortlisted" value={all.length} sub={`${all.filter(i => i.kind === 'company').length} directs · ${all.filter(i => i.kind === 'fund').length} funds`} dark />
        <Kpi label="My L1" value={all.filter(i => i.my_priority === 'L1').length} sub={`Claude L1: ${all.filter(i => i.claude_priority === 'L1').length}`} gold />
        <Kpi label="Priorities differ" value={differ} sub="Mine vs Claude's" />
        <Kpi label="Headlines, last 7 days" value={fresh} sub={`${all.reduce((n, i) => n + i.news.filter(x => x.date >= week && x.importance === 'high').length, 0)} high importance`} />
        <Kpi label="Refreshing" value={running} sub={running ? 'Updates as each finishes' : 'Idle'} />
      </div>

      <div style={{ display: 'flex', flexWrap: 'wrap', gap: 10, alignItems: 'center' }}>
        <div className="toggle-bar" role="tablist" aria-label="Section" style={{ marginBottom: 0 }}>
          {([['all', 'All', all.length], ['company', 'Directs / Co-investments', all.filter(i => i.kind === 'company').length], ['fund', 'Funds', all.filter(i => i.kind === 'fund').length]] as const).map(([k, l, n]) => (
            <button key={k} role="tab" aria-selected={section === k} className={`tog-btn${section === k ? ' on' : ''}`} onClick={() => setSection(k)}>{l} <span className="note">{n}</span></button>
          ))}
        </div>
        <div className="chips" role="group" aria-label="Priority filter">
          <button className={`chip${!lv ? ' on' : ''}`} onClick={() => setLv('')}>Any priority</button>
          {LEVELS.map(l => <button key={l} className={`chip${lv === l ? ' on' : ''}`} onClick={() => setLv(lv === l ? '' : l)}>{l}</button>)}
        </div>
        <select aria-label="Priority filter applies to" className="tbl-sel" value={by} onChange={e => setBy(e.target.value as typeof by)} disabled={!lv}>
          <option value="either">Mine or Claude's</option><option value="mine">My priority</option><option value="claude">Claude's priority</option>
        </select>
        <input type="search" className="tbl-search" placeholder="Search…" aria-label="Search shortlist" value={q} onChange={e => setQ(e.target.value)} />
      </div>

      {section !== 'fund' && (
        <Card title={`Directs / Co-investments (${cos.length})`}>
          <DataTable rows={cos} rowKey={i => String(i.id)} cols={companyCols(data.can_edit, data.enabled, model)} onRowClick={i => go(`sl-${i.id}`)}
            initialSort={sort} empty="No companies on the shortlist match. Use “+ Add to shortlist”." />
        </Card>
      )}
      {section !== 'company' && (
        <Card title={`Funds (${funds.length})`}>
          <DataTable rows={funds} rowKey={i => String(i.id)} cols={fundCols(data.can_edit, data.enabled, model)} onRowClick={i => go(`sl-${i.id}`)}
            initialSort={sort} empty="No funds on the shortlist yet. Use “+ Add to shortlist” and pick Fund / GP." />
        </Card>
      )}
      {adding && <AddDialog onClose={() => setAdding(false)} model={model} enabled={data.enabled} models={data.models} />}
    </div>
  )
}

// ── Add dialog ───────────────────────────────────────────────────────────────
function AddDialog({ onClose, model: model0, enabled, models }: { onClose: () => void; model: string; enabled: boolean; models: ShortlistData['models'] }) {
  const { companies, managers } = useData()
  const { inval } = useMutations()
  const [kind, setKind] = useState<'company' | 'fund'>('company')
  const [text, setText] = useState('')
  const [pick, setPick] = useState<{ id: string; name: string } | null>(null)
  const [website, setWebsite] = useState('')
  const [level, setLevel] = useState<Level>('L2')
  const [thesis, setThesis] = useState('')
  const [model, setModel] = useState(model0)
  const [err, setErr] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)
  const pool = kind === 'company' ? companies.map(c => ({ id: c.id, name: c.name, sub: c.sector })) : managers.map(m => ({ id: m.id, name: m.name, sub: m.type }))
  const s = text.trim().toLowerCase()
  const hits = !s || pick ? [] : pool.filter(p => p.name.toLowerCase().includes(s)).slice(0, 8)

  const submit = async (e: React.FormEvent) => {
    e.preventDefault()
    setBusy(true); setErr(null)
    try {
      const { data } = await api.post<SlItem>('/shortlist/', { kind, id: pick?.id, name: pick ? undefined : text.trim(), website, my_priority: level, thesis, model })
      await inval()
      if (!pick) void useData.getState().load()
      void useResearch.getState().refresh()
      onClose(); go(`sl-${data.id}`)
    } catch (ex) { setErr(errorText(ex)) } finally { setBusy(false) }
  }

  return (
    <div className="modal-overlay" onClick={onClose}>
      <form className="modal-panel" onClick={e => e.stopPropagation()} onSubmit={submit}>
        <div className="modal-header"><div className="modal-title">Add to shortlist</div><button type="button" className="btn" onClick={onClose}>Cancel</button></div>
        <div className="modal-body">
          <div className="toggle-bar" role="tablist" aria-label="Type">
            {(['company', 'fund'] as const).map(k => (
              <button key={k} type="button" role="tab" aria-selected={kind === k} className={`tog-btn${kind === k ? ' on' : ''}`}
                onClick={() => { setKind(k); setPick(null); setText('') }}>{k === 'company' ? 'Direct / co-investment' : 'Fund / GP'}</button>
            ))}
          </div>
          <div className="form-group">
            <label className="form-label" htmlFor="sl-name">{kind === 'company' ? 'Company' : 'Manager'}</label>
            <input id="sl-name" className="form-input" style={{ width: '100%' }} autoFocus autoComplete="off" required
              placeholder={kind === 'company' ? 'Search tracked companies or type a new name' : 'Search tracked managers or type a new name'}
              value={pick ? pick.name : text} onChange={e => { setPick(null); setText(e.target.value) }} />
            {hits.length > 0 && (
              <div className="sl-suggest" role="listbox">
                {hits.map(h => <button type="button" key={h.id} role="option" aria-selected={false} onClick={() => setPick(h)}><b>{h.name}</b> <span className="note">{h.sub}</span></button>)}
              </div>
            )}
            {pick ? <p className="note">In the tracker: the refresh will update its profile.</p>
              : s ? <p className="note">{hits.length ? 'Pick a match, or keep typing to add a new name.' : 'Not tracked yet: it will be researched first (full profile), then refreshed.'}</p> : null}
          </div>
          {!pick && s && (
            <div className="form-group">
              <label className="form-label" htmlFor="sl-web">Website (optional, helps research)</label>
              <input id="sl-web" className="form-input" style={{ width: '100%' }} placeholder="https://…" value={website} onChange={e => setWebsite(e.target.value)} />
            </div>
          )}
          <div className="form-group">
            <span className="form-label">My priority</span>
            <div className="chips">{LEVELS.map(l => <button type="button" key={l} className={`chip${level === l ? ' on' : ''}`} onClick={() => setLevel(l)}>{l}</button>)}</div>
          </div>
          <div className="form-group">
            <label className="form-label" htmlFor="sl-thesis">Why it's on the shortlist</label>
            <textarea id="sl-thesis" className="form-textarea" rows={3} style={{ width: '100%' }} value={thesis} onChange={e => setThesis(e.target.value)} placeholder="Thesis, rounds you want to back, access route…" />
          </div>
          {enabled && (
            <div className="form-group">
              <label className="form-label" htmlFor="sl-model">Research model</label>
              <select id="sl-model" className="form-select" value={model} onChange={e => setModel(e.target.value)}>
                {models.map(m => <option key={m.id} value={m.id}>{m.label}</option>)}
              </select>
            </div>
          )}
          {err && <div className="err-box">{err}</div>}
        </div>
        <div className="modal-footer"><button className="btn btn-primary" type="submit" disabled={busy || (!pick && !s)}>{busy ? 'Adding…' : 'Add'}</button></div>
      </form>
    </div>
  )
}

// ── Drawer ───────────────────────────────────────────────────────────────────
export function ShortlistDrawer({ id }: { id: string }) {
  const { data } = useShortlist()
  const m = useMutations()
  const item = data?.items.find(i => String(i.id) === id)
  const [model, setModel] = useState('')
  const [lvl, setLvl] = useState<Level>('')
  const [note, setNote] = useState('')
  const [notes, setNotes] = useState({ thesis: '', rounds_plan: '', target: '' })
  const [newsF, setNewsF] = useState<'all' | 'high'>('all')
  const [err, setErr] = useState<string | null>(null)
  const [saved, setSaved] = useState(false)

  useEffect(() => { if (data && !model) setModel(data.defaults.company) }, [data, model])
  useEffect(() => {
    if (item) {
      setLvl(item.my_priority)
      setNotes({ thesis: item.thesis, rounds_plan: item.rounds_plan, target: item.target_allocation_usd_m == null ? '' : String(item.target_allocation_usd_m) })
    }
  }, [item?.id, item?.my_priority]) // eslint-disable-line react-hooks/exhaustive-deps

  if (!data) return <Drawer title="Loading…"><p className="note">Loading…</p></Drawer>
  if (!item) return <Drawer title="Not found"><p className="note">This item is no longer on the shortlist.</p></Drawer>
  const can = data.can_edit
  const co = item.company, mg = item.manager
  const busy = item.research_status === 'queued' || item.research_status === 'running'
  const news = newsF === 'high' ? item.news.filter(n => n.importance === 'high') : item.news
  const run = async (f: () => Promise<void>) => { setErr(null); try { await f() } catch (e) { setErr(errorText(e)) } }

  return (
    <Drawer eyebrow={`Shortlisted · ${KIND_LABEL[item.kind]}`} title={item.name} link={co?.website || mg?.website || undefined}
      actions={<>
        {can && data.enabled && (
          <>
            {!busy && <select aria-label="Model for refresh" className="tbl-sel" value={model} onChange={e => setModel(e.target.value)}>
              {data.models.map(x => <option key={x.id} value={x.id}>{x.label.split(' · ')[0]}</option>)}
            </select>}
            <button className="btn btn-primary" disabled={busy} onClick={() => void run(() => m.refresh(item.id, model))}>{busy ? 'Refreshing…' : 'Refresh now'}</button>
          </>
        )}
        {co && <button className="btn" onClick={() => go(`co-${co.id}`)}>Full profile</button>}
        {mg && <button className="btn" onClick={() => go(`gp-${mg.id}`)}>Full profile</button>}
      </>}>
      {err && <div className="err-box" style={{ marginBottom: 10 }}>{err}</div>}
      {item.research_status === 'failed' && item.last_error && <div className="err-box" style={{ marginBottom: 10 }}>Last refresh failed: {item.last_error}</div>}
      <p className="note" style={{ marginTop: 0 }}>Added {day(item.added_at)}{item.added_by ? ` by ${item.added_by}` : ''} · last refreshed {ago(item.last_refreshed_at)}{(co?.research_status || mg?.research_status) ? ' · profile research in progress' : ''}</p>

      <div className="grid2" style={{ marginBottom: 12 }}>
        <div className="sl-prio">
          <div className="card-title">My priority</div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>
            <LevelPill level={item.my_priority} />
            <span className="note">{item.my_priority_since ? `since ${day(item.my_priority_since)}` : 'not set'}</span>
          </div>
          {can && (
            <div style={{ marginTop: 8, display: 'flex', flexDirection: 'column', gap: 6 }}>
              <div className="chips">{LEVELS.map(l => <button key={l} className={`chip${lvl === l ? ' on' : ''}`} onClick={() => setLvl(l)}>{l}</button>)}
                <button className={`chip${lvl === '' ? ' on' : ''}`} onClick={() => setLvl('')}>Clear</button></div>
              <input className="form-input" aria-label="Reason for the change" placeholder="Reason for the change (logged)" value={note} onChange={e => setNote(e.target.value)} />
              <div><button className="pb" disabled={lvl === item.my_priority} onClick={() => void run(async () => { await m.setMine(item.id, lvl, note); setNote('') })}>Save priority</button></div>
            </div>
          )}
        </div>
        <div className="sl-prio">
          <div className="card-title">Claude's priority</div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>
            <LevelPill level={item.claude_priority} />
            <span className="note">{item.claude_priority_since ? `since ${day(item.claude_priority_since)}` : 'set on first refresh'}</span>
            {item.my_priority && item.claude_priority && item.my_priority !== item.claude_priority && <span className="badge badge-gold">differs from yours</span>}
          </div>
          {item.claude_rationale && <p style={{ margin: '8px 0 0', fontSize: 12.5 }}>{item.claude_rationale}</p>}
        </div>
      </div>

      {item.brief && <Card title={<>Latest status <Momentum m={item.momentum} /></>}><p style={{ margin: 0 }}>{item.brief}</p></Card>}

      {co && (
        <div className="facts" style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit,minmax(140px,1fr))', gap: 10, margin: '12px 0' }}>
          <Fact k="Valuation" v={<>{money(co.latest_valuation_usd_bn)}<Lbl l={co.valuation_label} /><div className="sub">{co.valuation_date} {co.valuation_basis}</div></>} big />
          <Fact k="Last round" v={lastRound(item) ? <>{lastRound(item)!.round}<div className="sub">{lastRound(item)!.date} · {lastRound(item)!.lead}</div></> : '—'} />
          <Fact k={co.revenue_metric || 'Revenue'} v={<>{money(co.revenue_usd_bn)}<Lbl l={co.revenue_label} /><div className="sub">{co.revenue_date}</div></>} />
          <Fact k="Val / revenue" v={xmult(co.ev_rev_x)} />
          <Fact k="Step-up since first mark" v={xmult(co.step_up_x)} />
          <Fact k="Status" v={<StatusPill status={co.status} />} />
        </div>
      )}
      {mg && (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit,minmax(140px,1fr))', gap: 10, margin: '12px 0' }}>
          <Fact k="AUM" v={<>{money(mg.aum_usd_bn)}<Lbl l={mg.aum_label} /><div className="sub">{mg.aum_date}</div></>} big />
          <Fact k="Latest fund" v={latestFund(item) ? <>{latestFund(item)!.name}<div className="sub">{latestFund(item)!.vintage} · {money(latestFund(item)!.size_usd_bn)}</div></> : '—'} />
          <Fact k="Type" v={mg.type || '—'} />
          <Fact k="HQ" v={mg.hq || '—'} />
        </div>
      )}

      <div className="grid2" style={{ marginBottom: 12 }}>
        {(item.performance || co?.growth || mg?.performance) && <Card title={item.kind === 'fund' ? 'Performance' : 'Revenue, growth & margins'}>
          <p style={{ margin: 0 }}>{item.performance || (item.kind === 'fund' ? mg?.performance : [co?.growth, co?.profitability].filter(Boolean).join(' · '))}</p></Card>}
        {item.next_round && <Card title={item.kind === 'fund' ? 'Next fund & re-up window' : 'Next round & access'}><p style={{ margin: 0 }}>{item.next_round}</p></Card>}
      </div>

      {co && co.rounds.length > 1 && <Card title="Valuation progression"><ValuationChart rounds={co.rounds} latest={co.latest_valuation_usd_bn} latestDate={co.valuation_date} /></Card>}

      {(item.catalysts.length > 0 || item.risks.length > 0) && (
        <div className="grid2" style={{ margin: '12px 0' }}>
          <Card><PointsView title="Catalysts" points={item.catalysts} /></Card>
          <Card><PointsView title="Risks" points={item.risks} /></Card>
        </div>
      )}

      <Card title={`News (${item.news.length})`} right={
        <div className="toggle-bar" style={{ marginBottom: 0 }}>
          {(['all', 'high'] as const).map(k => <button key={k} className={`tog-btn${newsF === k ? ' on' : ''}`} onClick={() => setNewsF(k)}>{k === 'all' ? 'All' : 'High importance'}</button>)}
        </div>}>
        {news.length ? (
          <ul className="sl-news">
            {news.map(n => (
              <li key={n.id}>
                <div className="sl-news-hd">
                  <span className="note">{n.date || '—'}</span>
                  <span className={`badge ${n.importance === 'high' ? 'badge-red' : n.importance === 'medium' ? 'badge-gold' : 'badge-gray'}`}>{n.importance}</span>
                  {n.category && <span className="badge badge-blue">{n.category}</span>}
                  {can && <button className="pb" style={{ marginLeft: 'auto' }} title="Dismiss (won't come back on refresh)" aria-label={`Dismiss ${n.headline}`} onClick={() => void run(() => m.dismiss(n.id))}>✕</button>}
                </div>
                <div className="sl-news-h">{n.url ? <a href={n.url} target="_blank" rel="noopener noreferrer">{n.headline}</a> : n.headline}</div>
                {n.summary && <div className="sub">{n.summary}</div>}
                {n.source && <div className="note">{n.source}</div>}
              </li>
            ))}
          </ul>
        ) : <p className="note">{item.last_refreshed_at ? 'No headlines logged.' : 'No news yet: run Refresh now to search the web.'}</p>}
      </Card>

      <div style={{ display: 'flex', flexDirection: 'column', gap: 12, margin: '12px 0' }}>
        <Card title="Priority log">
          {item.priority_log.length ? (
            <table className="mini-tbl"><thead><tr><th>When</th><th>Track</th><th>Change</th><th>By / reason</th></tr></thead>
              <tbody>{item.priority_log.map(p => (
                <tr key={p.id}><td className="note">{day(p.changed_at)}</td><td>{p.track === 'mine' ? 'Mine' : 'Claude'}</td>
                  <td style={{ whiteSpace: 'nowrap' }}><LevelPill level={p.old} /> → <LevelPill level={p.new} /></td>
                  <td><b style={{ fontWeight: 600 }}>{p.changed_by}</b>{p.note && <div className="sub">{clip(p.note, 260)}</div>}</td></tr>
              ))}</tbody></table>
          ) : <p className="note">No changes yet.</p>}
        </Card>
        <Card title="Progress log (each refresh)">
          {item.marks.length ? (
            <table className="mini-tbl"><thead><tr><th>Checked</th>{item.kind === 'company' ? <><th>Valuation</th><th>Revenue</th></> : <th>AUM</th>}<th>Changes</th></tr></thead>
              <tbody>{item.marks.map((k, ix) => (
                <tr key={ix}><td className="note">{day(k.as_of)}</td>
                  {item.kind === 'company' ? <><td>{money(k.valuation_usd_bn)}<div className="sub">{k.valuation_date}</div></td><td>{money(k.revenue_usd_bn)}<div className="sub">{k.revenue_metric} {k.revenue_date}</div></td></>
                    : <td>{money(k.aum_usd_bn)}</td>}
                  <td className="sub">{k.note || '—'}</td></tr>
              ))}</tbody></table>
          ) : <p className="note">Filled in by each refresh.</p>}
        </Card>
      </div>

      <Card title="My notes">
        {can ? (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
            <label className="form-label" htmlFor="sl-th">Thesis</label>
            <textarea id="sl-th" className="form-textarea" rows={3} value={notes.thesis} onChange={e => { setSaved(false); setNotes({ ...notes, thesis: e.target.value }) }} />
            <label className="form-label" htmlFor="sl-rp">{item.kind === 'fund' ? 'Funds / vintages to back, access' : 'Rounds to back, access route'}</label>
            <textarea id="sl-rp" className="form-textarea" rows={2} value={notes.rounds_plan} onChange={e => { setSaved(false); setNotes({ ...notes, rounds_plan: e.target.value }) }} />
            <label className="form-label" htmlFor="sl-ta">Target allocation (USD m)</label>
            <input id="sl-ta" className="form-input" inputMode="decimal" style={{ maxWidth: 160 }} value={notes.target} onChange={e => { setSaved(false); setNotes({ ...notes, target: e.target.value }) }} />
            <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
              <button className="pb" onClick={() => void run(async () => { await m.save(item.id, { thesis: notes.thesis, rounds_plan: notes.rounds_plan, target_allocation_usd_m: notes.target === '' ? null : Number(notes.target) }); setSaved(true) })}>Save notes</button>
              {saved && <span className="note">Saved</span>}
            </div>
          </div>
        ) : (
          <>
            <p style={{ marginTop: 0 }}>{item.thesis || '—'}</p>
            {item.rounds_plan && <p>{item.rounds_plan}</p>}
            {item.target_allocation_usd_m != null && <p className="note">Target allocation {usdm(item.target_allocation_usd_m)}</p>}
          </>
        )}
      </Card>

      {item.sources.length > 0 && (
        <Card title="Sources (latest refresh)">
          <ul className="plain">{item.sources.map(s => <li key={s}><a href={s} target="_blank" rel="noopener noreferrer">{s.replace(/^https?:\/\/(www\.)?/, '').slice(0, 90)}</a></li>)}</ul>
        </Card>
      )}

      {can && (
        <div style={{ marginTop: 14 }}>
          <button className="btn" style={{ color: 'var(--red)' }} onClick={() => void run(async () => {
            if (!window.confirm(`Remove ${item.name} from the shortlist? Its news and priority log are deleted; the tracker profile stays.`)) return
            await m.remove(item.id); closeDrawer()
          })}>Remove from shortlist</button>
        </div>
      )}
    </Drawer>
  )
}
