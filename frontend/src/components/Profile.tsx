/** Structured business profiles (company / GP) shown in the detail drawers, plus generate / refresh controls. */
import { useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { api, errorText } from '../lib/api'
import { money } from '../lib/format'
import { go } from '../lib/route'
import { useData } from '../store/data'
import { useResearch } from '../store/research'
import type { CompanyProfile, ManagerProfile } from '../types'
import { CoLogo, GpLogo } from './Logo'
import { Card, Kpi, Lbl } from './ui'

const norm = (s: string) => s.toLowerCase().replace(/\(.*?\)/g, '').replace(/[^a-z0-9]/g, '')

function useNameIndex(kind: 'co' | 'gp') {
  const rows = useData(s => (kind === 'co' ? s.companies : s.managers))
  const idx = new Map<string, string>()
  for (const r of rows) idx.set(norm(r.name), r.id)
  return idx
}

function NamedChips({ items, kind }: { items: { name: string; note: string }[]; kind: 'co' | 'gp' }) {
  const idx = useNameIndex(kind)
  if (!items.length) return <p className="note">Not available.</p>
  return (
    <div className="pf-named">
      {items.map(x => {
        const id = idx.get(norm(x.name))
        return (
          <div key={x.name} className={`pf-named-row${id ? ' click' : ''}`} onClick={() => id && go(`${kind}-${id}`)}>
            {kind === 'co' ? <CoLogo id={id} name={x.name} size={22} /> : <GpLogo id={id} name={x.name} size={22} />}
            <div><b>{x.name}</b>{id && <span className="note"> · tracked</span>}{x.note && <div className="sub">{x.note}</div>}</div>
          </div>
        )
      })}
    </div>
  )
}

const Bullets = ({ items }: { items: string[] }) => items.length ? <ul className="plain">{items.map(x => <li key={x}>{x}</li>)}</ul> : <p className="note">Not available.</p>
const Para = ({ t }: { t?: string }) => <p className="prose" style={{ margin: 0 }}>{t || <span className="note">Not available.</span>}</p>

export function ProfileControls({ kind, id, status, has, asOf }: { kind: 'company' | 'manager'; id: string; status: string; has: boolean; asOf?: string }) {
  const qc = useQueryClient()
  const canResearch = useResearch(s => s.can_research)
  const enabled = useResearch(s => s.enabled)
  const models = useResearch(s => s.models)
  const [model, setModel] = useState('')
  const [err, setErr] = useState<string | null>(null)
  const busy = status === 'queued' || status === 'running'
  const run = async () => {
    setErr(null)
    try {
      await api.post('/research/profiles/', { kind, ids: [id], model: model || undefined })
      await qc.invalidateQueries({ queryKey: [kind, id] })
      void useResearch.getState().refresh()
    } catch (e) { setErr(errorText(e)) }
  }
  return (
    <div className="pf-ctrl">
      {busy ? <span className="badge badge-gold">{status === 'running' ? 'Writing profile…' : 'Profile queued'}</span>
        : status === 'failed' ? <span className="badge badge-red">Profile research failed</span>
          : has ? <span className="note">Profile as of {asOf}</span> : <span className="note">No business profile yet.</span>}
      {canResearch && enabled && !busy && (
        <>
          <select className="tbl-sel" aria-label="Model for profile" value={model} onChange={e => setModel(e.target.value)}>
            <option value="">Haiku (economy)</option>
            {models.filter(m => !m.id.includes('haiku')).map(m => <option key={m.id} value={m.id}>{m.label.split(' · ')[0]}</option>)}
          </select>
          <button className="pb" onClick={() => void run()} title={models.length ? `About $${(models.find(m => m.id === (model || models[0].id))?.est_profile ?? 0).toFixed(2)}` : undefined}>
            {has ? 'Refresh profile' : 'Generate profile'}
          </button>
        </>
      )}
      {err && <span className="err-inline">{err}</span>}
    </div>
  )
}

export function CompanyProfileView({ p }: { p: CompanyProfile }) {
  const f = p.financials
  return (
    <div className="pf">
      <Card title="Business profile"><Para t={p.summary} /></Card>
      <div className="grid2">
        <Card title="What it sells">
          {p.products.length ? <ul className="pf-products">{p.products.map(x => <li key={x.name}><b>{x.name}</b>{x.description && <> · {x.description}</>}</li>)}</ul> : <p className="note">Not available.</p>}
          {p.customers && <><div className="pf-k">Customers</div><Para t={p.customers} /></>}
          {p.business_model && <><div className="pf-k">Business model</div><Para t={p.business_model} /></>}
        </Card>
        <Card title={<>Financials {f.label && <Lbl l={f.label} />}</>}>
          <div className="pf-fin">
            <div><div className="pf-k">{f.revenue_metric || 'Revenue'}</div><div className="pf-v">{f.revenue_usd_bn != null ? money(f.revenue_usd_bn) : '—'}</div><div className="sub">{f.revenue_date}</div></div>
            <div><div className="pf-k">Growth</div><div className="pf-v2">{f.growth || '—'}</div></div>
            <div><div className="pf-k">Gross margin</div><div className="pf-v2">{f.gross_margin || '—'}</div></div>
            <div><div className="pf-k">Profitability</div><div className="pf-v2">{f.profitability || '—'}</div></div>
            {f.headcount ? <div><div className="pf-k">Headcount</div><div className="pf-v2">{Math.round(f.headcount).toLocaleString()}</div></div> : null}
          </div>
          {f.note && <p className="sub" style={{ marginTop: 8 }}>{f.note}</p>}
        </Card>
      </div>
      {p.value_chain.chain.length > 0 && (
        <Card title="Where it sits in the value chain">
          <div className="pf-chain" role="list">
            {p.value_chain.chain.map((l, i) => (
              <div key={i} role="listitem" className={`pf-layer${l.current ? ' on' : ''}`}>
                <div className="pf-layer-n">{l.layer}{l.current && <span className="pf-here">this company</span>}</div>
                {l.examples && <div className="sub">{l.examples}</div>}
              </div>
            ))}
          </div>
          <p className="note" style={{ margin: '6px 0 0' }}>Upstream (inputs) → downstream (end customers)</p>
          {p.value_chain.position && <div style={{ marginTop: 8 }}><Para t={p.value_chain.position} /></div>}
        </Card>
      )}
      <div className="grid2">
        <Card title="Competition">
          <NamedChips items={p.competition} kind="co" />
          {p.competitive_position && <><div className="pf-k">Position</div><Para t={p.competitive_position} /></>}
          {p.moat && <><div className="pf-k">Moat</div><Para t={p.moat} /></>}
        </Card>
        <Card title="Industry & trends">
          {p.industry.market && <><div className="pf-k">Market</div><Para t={p.industry.market} /></>}
          <div className="pf-k">Trends</div><Bullets items={p.industry.trends} />
          <div className="pf-k">Key risks</div><Bullets items={p.risks} />
        </Card>
      </div>
      {p.sources.length > 0 && <p className="note">Profile sources: {p.sources.map((s, i) => <span key={s}>{i ? ' · ' : ''}<a href={s} target="_blank" rel="noopener noreferrer">{s.replace(/^https?:\/\/(www\.)?/, '').split('/')[0]}</a></span>)}</p>}
    </div>
  )
}

export function ManagerProfileView({ p }: { p: ManagerProfile }) {
  const st = p.strategy
  const rows: [string, string][] = [['Stages', st.stages], ['Check size', st.check_size], ['Sectors', st.sectors], ['Geography', st.geography], ['Style', st.style]]
  return (
    <div className="pf">
      <Card title="Firm profile"><Para t={p.summary} /></Card>
      <div className="grid2">
        <Card title="Strategy">
          <table className="mini-tbl pf-tbl"><tbody>{rows.filter(([, v]) => v).map(([k, v]) => <tr key={k}><td className="pf-k">{k}</td><td>{v}</td></tr>)}</tbody></table>
          {p.funds && <><div className="pf-k">Funds</div><Para t={p.funds} /></>}
        </Card>
        <Card title="Team & track record">
          {p.team && <><div className="pf-k">Team</div><Para t={p.team} /></>}
          <div className="pf-k">Track record</div><Para t={p.track_record} />
        </Card>
      </div>
      <div className="grid2">
        <Card title="Differentiation">
          <Para t={p.differentiation} />
          {p.platform && <><div className="pf-k">Platform / value-add</div><Para t={p.platform} /></>}
          <div className="pf-k">Investing behind now</div><Bullets items={p.current_themes} />
        </Card>
        <Card title="Peers">
          <NamedChips items={p.peers} kind="gp" />
          <div className="pf-k">LP considerations</div><Bullets items={p.lp_considerations} />
        </Card>
      </div>
      {p.sources.length > 0 && <p className="note">Profile sources: {p.sources.map((s, i) => <span key={s}>{i ? ' · ' : ''}<a href={s} target="_blank" rel="noopener noreferrer">{s.replace(/^https?:\/\/(www\.)?/, '').split('/')[0]}</a></span>)}</p>}
    </div>
  )
}

interface ProfileStats {
  companies: { total: number; with_profile: number; queued: number }
  managers: { total: number; with_profile: number; queued: number }
  enabled: boolean; can_edit: boolean; models: { id: string; label: string; est_profile: number }[]
}

/** Admin control: generate profiles in bulk (missing only, or refresh all), with a cost estimate and cancel. */
export function ProfilesBulkButton({ kind }: { kind: 'company' | 'manager' }) {
  const canResearch = useResearch(s => s.can_research)
  const [open, setOpen] = useState(false)
  if (!canResearch) return null
  return (
    <>
      <button className="btn" onClick={() => setOpen(true)}>Business profiles…</button>
      {open && <ProfilesBulkDialog kind={kind} onClose={() => setOpen(false)} />}
    </>
  )
}

function ProfilesBulkDialog({ kind: kind0, onClose }: { kind: 'company' | 'manager'; onClose: () => void }) {
  const [stats, setStats] = useState<ProfileStats | null>(null)
  const [kind, setKind] = useState<'company' | 'manager' | 'both'>(kind0)
  const [scope, setScope] = useState<'missing' | 'shortlist' | 'all'>('missing')
  const [model, setModel] = useState('')
  const [limit, setLimit] = useState('')
  const [msg, setMsg] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)
  const load = () => api.get<ProfileStats>('/research/profiles/').then(r => { setStats(r.data); if (!model) setModel(r.data.models[0]?.id ?? '') }).catch(e => setMsg(errorText(e)))
  if (!stats && !msg) void load()
  const per = stats?.models.find(m => m.id === model)?.est_profile ?? 0
  const pool = (k: 'companies' | 'managers') => !stats ? 0 : scope === 'all' ? stats[k].total : stats[k].total - stats[k].with_profile
  const count = !stats ? 0 : scope === 'shortlist' ? NaN
    : (kind !== 'manager' ? pool('companies') : 0) + (kind !== 'company' ? pool('managers') : 0)
  const n = limit ? Math.min(Number(limit) || 0, count || Number(limit)) : count
  const start = async () => {
    setBusy(true); setMsg(null)
    try {
      const { data } = await api.post<{ queued: number; estimated_cost: number }>('/research/profiles/', { kind, scope, model, limit: limit ? Number(limit) : undefined })
      setMsg(`Queued ${data.queued} profiles (about $${data.estimated_cost.toFixed(2)}). They run in the background, behind anything you add by hand; open any company or GP to see its profile once written.`)
      void useResearch.getState().refresh(); void load()
    } catch (e) { setMsg(errorText(e)) } finally { setBusy(false) }
  }
  const cancel = async () => {
    setBusy(true)
    try { const { data } = await api.delete<{ cancelled: number }>('/research/profiles/'); setMsg(`Cancelled ${data.cancelled} queued profiles.`); void load() }
    catch (e) { setMsg(errorText(e)) } finally { setBusy(false) }
  }
  const queued = (stats?.companies.queued ?? 0) + (stats?.managers.queued ?? 0)
  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-panel" role="dialog" aria-modal="true" aria-label="Business profiles" onClick={e => e.stopPropagation()}>
        <div className="modal-header"><div className="modal-title">Business profiles</div><button className="btn" onClick={onClose}>Close</button></div>
        <div className="modal-body">
          <p className="note" style={{ marginTop: 0 }}>Each profile covers what the company sells, customers, revenue / ARR and margins, value-chain position, competitors, industry trends, moat and risks (for GPs: strategy, funds, team, track record, peers, themes and LP considerations). Written with web search and sourced.</p>
          {stats && (
            <div className="atl-kpis" style={{ margin: '8px 0 12px' }}>
              <Kpi label="Companies with a profile" value={`${stats.companies.with_profile} / ${stats.companies.total}`} />
              <Kpi label="GPs with a profile" value={`${stats.managers.with_profile} / ${stats.managers.total}`} />
              <Kpi label="In the queue" value={queued} />
            </div>
          )}
          <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap' }}>
            <div className="form-group"><label className="form-label" htmlFor="pb-kind">For</label>
              <select id="pb-kind" className="form-select" value={kind} onChange={e => setKind(e.target.value as typeof kind)}>
                <option value="company">Companies</option><option value="manager">GPs / managers</option><option value="both">Both</option>
              </select></div>
            <div className="form-group"><label className="form-label" htmlFor="pb-scope">Which</label>
              <select id="pb-scope" className="form-select" value={scope} onChange={e => setScope(e.target.value as typeof scope)}>
                <option value="missing">Only those without a profile</option><option value="shortlist">Shortlisted companies</option><option value="all">All (refresh existing too)</option>
              </select></div>
            <div className="form-group"><label className="form-label" htmlFor="pb-model">Model</label>
              <select id="pb-model" className="form-select" value={model} onChange={e => setModel(e.target.value)}>
                {stats?.models.map(m => <option key={m.id} value={m.id}>{m.label} · ~${m.est_profile.toFixed(2)} each</option>)}
              </select></div>
            <div className="form-group"><label className="form-label" htmlFor="pb-limit">Limit (optional)</label>
              <input id="pb-limit" className="form-input" inputMode="numeric" placeholder="e.g. 100" style={{ width: 110 }} value={limit} onChange={e => setLimit(e.target.value.replace(/\D/g, ''))} /></div>
          </div>
          {stats && !Number.isNaN(n) && <p><b>{n.toLocaleString()}</b> profiles · estimated <b>${(n * per).toFixed(2)}</b> on your Anthropic API key. Order: GPs first, then shortlisted companies, then companies by valuation. Legacy holdings are skipped.</p>}
          {stats && Number.isNaN(n) && <p>Shortlisted companies · about <b>${per.toFixed(2)}</b> each.</p>}
          {stats && !stats.enabled && <div className="err-box">Research is off until ANTHROPIC_API_KEY is set on Railway.</div>}
          {msg && <div className="note" role="status" style={{ marginTop: 6 }}>{msg}</div>}
        </div>
        <div className="modal-footer" style={{ display: 'flex', gap: 8, justifyContent: 'flex-end' }}>
          {queued > 0 && <button className="btn" disabled={busy} onClick={() => void cancel()}>Cancel {queued} queued</button>}
          <button className="btn btn-primary" disabled={busy || !stats?.enabled || n === 0} onClick={() => void start()}>Start</button>
        </div>
      </div>
    </div>
  )
}
