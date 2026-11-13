/**
 * Trends: where venture & growth capital is going and where to deploy, split EARLY vs GROWTH.
 * Weekly brief → deploy board → heat ranking → visual market map (logos) → capital flows → valuation evolution
 * → reading list → "stay on top" playbook. Theme drawer (#th-<id>) holds the full thesis.
 * Data: /api/v1/trends/ (updated weekly by the "Venture GP Atlas Weekly" job; per-theme refresh on demand).
 */
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { useEffect, useMemo, useRef, useState } from 'react'
import { CartesianGrid, Line, LineChart, ResponsiveContainer, Scatter, ScatterChart, Tooltip, XAxis, YAxis, ZAxis } from 'recharts'
import { PointsView } from '../components/Commentary'
import Drawer from '../components/Drawer'
import { Logo } from '../components/Logo'
import { Card, Kpi } from '../components/ui'
import { api, errorText } from '../lib/api'
import { clip, money } from '../lib/format'
import { go } from '../lib/route'
import { useData } from '../store/data'
import { useResearch } from '../store/research'
import { create } from 'zustand'
import type { Deploy, HeatComponent, TrBrief, TrCompany, TrendsData, TrFramework, TrMark, TrResource, TrTheme } from '../types'

const KEY = ['trends']
type StageView = 'all' | 'early' | 'growth'

export function useTrends() {
  const q = useQuery({
    queryKey: KEY,
    queryFn: () => api.get<TrendsData>('/trends/').then(r => r.data),
    staleTime: 60_000,
    refetchInterval: query => (query.state.data?.active ? 8000 : false),
  })
  const was = useRef(false)
  const active = q.data?.active ?? 0
  useEffect(() => {
    if (was.current && active === 0) void useResearch.getState().refresh()
    was.current = active > 0
  }, [active])
  return q
}

const SIGNAL: Record<string, { label: string; cls: string }> = {
  accelerating: { label: 'Accelerating', cls: 'sig-acc' }, hot: { label: 'Hot', cls: 'sig-hot' }, steady: { label: 'Steady', cls: 'sig-steady' },
  emerging: { label: 'Emerging', cls: 'sig-emg' }, cooling: { label: 'Cooling', cls: 'sig-cool' },
}
const DEPLOY_COLS: { id: Deploy; label: string; hint: string }[] = [
  { id: 'overweight', label: 'Overweight', hint: 'Deploy now' }, { id: 'selective', label: 'Selective', hint: 'Best names / right price only' },
  { id: 'watch', label: 'Watch', hint: 'Track, not yet' }, { id: 'avoid', label: 'Avoid', hint: 'Risk/return not there' },
]
const KINDS: [string, string][] = [['report', 'Reports'], ['article', 'Articles'], ['news', 'News'], ['interview', 'GP interviews'], ['podcast', 'Podcasts'], ['video', 'Videos'], ['newsletter', 'Newsletters'], ['data', 'Data / trackers']]
const STAGE_LABEL: Record<string, string> = { early: 'Early', growth: 'Growth', public: 'Public', acquired: 'Exited' }

export function SignalBadge({ s }: { s: string }) {
  const m = SIGNAL[s]
  return m ? <span className={`sig ${m.cls}`}>{m.label}</span> : null
}
const DeployTag = ({ d }: { d: Deploy }) => d ? <span className={`dep dep-${d}`}>{d}</span> : <span className="note">—</span>

const inStage = (c: TrCompany, s: StageView) => s === 'all' || c.stage === s
const deployFor = (t: TrTheme, s: StageView): Deploy[] => s === 'early' ? [t.deploy_early] : s === 'growth' ? [t.deploy_growth] : [t.deploy_early, t.deploy_growth]
const ym = (d: string) => { const [y, m] = d.split('-').map(Number); return y + ((m || 6) - 1) / 12 }

export const COMP_COLOR: Record<string, string> = {
  capital: '#0f2347', velocity: '#3a6ea5', valuation: '#b38728', exits: '#1d7a47', conviction: '#8a5a9e',
}

function HeatStack({ comps }: { comps: HeatComponent[] }) {
  return (
    <span className="heat-bar heat-stack" title={comps.map(c => `${c.label}: ${c.points} pts (score ${c.score} × ${Math.round(c.weight * 100)}%)${c.scored ? '' : ', not yet sourced'}`).join('\n')}>
      {comps.map(c => <span key={c.id} style={{ width: `${c.points}%`, background: COMP_COLOR[c.id], opacity: c.scored ? 1 : 0.35 }} />)}
    </span>
  )
}

function CompLegend() {
  return (
    <span className="comp-legend">
      {[['capital', 'Capital 30%'], ['velocity', 'Velocity 20%'], ['valuation', 'Valuation 15%'], ['exits', 'Exits 15%'], ['conviction', 'Smart money 20%']].map(([k, l]) => (
        <span key={k}><i style={{ background: COMP_COLOR[k] }} />{l}</span>
      ))}
      <span><i style={{ background: '#999', opacity: 0.35 }} />Faded = not yet sourced (neutral 50)</span>
    </span>
  )
}

export function HeatBreakdown({ t }: { t: TrTheme }) {
  return (
    <div>
      <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 8 }}>
        <span className="heat-big">{t.heat}</span>
        <div style={{ flex: 1 }}><HeatStack comps={t.score.components} /></div>
        <SignalBadge s={t.signal} />
        {t.score.delta_4w != null && <span className="note">{t.score.delta_4w >= 0 ? '+' : ''}{t.score.delta_4w} vs 4 weeks ago</span>}
      </div>
      <table className="mini-tbl">
        <thead><tr><th>Input</th><th>Measured</th><th>Score</th><th>Weight</th><th>Points</th><th>Evidence</th></tr></thead>
        <tbody>{t.score.components.map(c => (
          <tr key={c.id}>
            <td style={{ whiteSpace: 'nowrap' }}><i className="comp-dot" style={{ background: COMP_COLOR[c.id] }} />{c.label}</td>
            <td>{c.value ?? '—'}</td>
            <td><b>{c.score}</b>{!c.scored && <span className="note"> (neutral)</span>}</td>
            <td>{Math.round(c.weight * 100)}%</td>
            <td>{c.points}</td>
            <td className="sub">{c.evidence}</td>
          </tr>
        ))}</tbody>
      </table>
    </div>
  )
}

function FrameworkModal({ fw, onClose }: { fw: TrFramework; onClose: () => void }) {
  useEffect(() => {
    const k = (e: KeyboardEvent) => { if (e.key === 'Escape') onClose() }
    window.addEventListener('keydown', k); return () => window.removeEventListener('keydown', k)
  }, [onClose])
  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-panel fw-panel" role="dialog" aria-modal="true" aria-label="How the Trends framework works" onClick={e => e.stopPropagation()}>
        <div className="modal-header"><div className="modal-title">How heat, signals and deploy views work</div><button className="btn" onClick={onClose}>Close</button></div>
        <div className="modal-body">
          <p className="fw-lead"><b>Two separate questions.</b> <i>Heat</i> asks "how much momentum is in this theme?" and is <b>calculated</b>.
            The <i>deploy view</i> asks "should an LP put money in at today's prices, at this stage?" and is a <b>judgement</b> against four tests.
            A theme can be very hot and still be "Avoid" at early stage.</p>

          <h3 className="fw-h">1 · Heat (0–100): measured momentum</h3>
          <p>{fw.heat.summary}</p>
          <table className="mini-tbl fw-tbl">
            <thead><tr><th>Input</th><th>Weight</th><th>How it is measured and scored</th></tr></thead>
            <tbody>{fw.heat.components.map(c => (
              <tr key={c.id}><td style={{ whiteSpace: 'nowrap' }}><i className="comp-dot" style={{ background: COMP_COLOR[c.id] }} /><b>{c.label}</b></td>
                <td>{Math.round(c.weight * 100)}%</td><td>{c.how}</td></tr>
            ))}</tbody>
          </table>
          <p className="note">{fw.heat.missing} Heat = Σ (score × weight). Example: capital 75 × 30% + velocity 80 × 20% + valuation 70 × 15% + exits 40 × 15% + smart money 90 × 20% = 73.</p>

          <h3 className="fw-h">2 · Signal: derived from heat and its direction</h3>
          <table className="mini-tbl fw-tbl2"><tbody>{fw.signal.map(r => <tr key={r.id}><td style={{ width: 120 }}><SignalBadge s={r.id} /></td><td>{r.rule}</td></tr>)}</tbody></table>
          <p className="note">Rules are checked top to bottom, so "Cooling" overrides a high heat.</p>

          <h3 className="fw-h">3 · Deploy view: Overweight / Selective / Watch / Avoid (per stage)</h3>
          <p>{fw.deploy.summary}</p>
          <div className="fw-tests">{fw.deploy.tests.map((t, i) => <div key={i} className="fw-test"><span className="pbk-n">{i + 1}</span>{t}</div>)}</div>
          <table className="mini-tbl fw-tbl2"><tbody>{fw.deploy.levels.map(l => <tr key={l.id}><td style={{ width: 120 }}><span className={`dep dep-${l.id}`}>{l.label}</span></td><td>{l.rule}</td></tr>)}</tbody></table>

          <h3 className="fw-h">4 · Stages and cadence</h3>
          <p>{fw.stage}</p>
          <p>{fw.cadence}</p>
          <p className="note">Open any theme to see its own heat breakdown with the evidence behind each input, and the reasoning for its early and growth deploy views.</p>
        </div>
      </div>
    </div>
  )
}

// ── page ─────────────────────────────────────────────────────────────────────
export default function Trends() {
  const { data, isLoading, error } = useTrends()
  const [stage, setStage] = useState<StageView>('all')
  const [followedOnly, setFollowedOnly] = useState(false)
  const [mapTheme, setMapTheme] = useState('')
  const [showFw, setShowFw] = useState(false)
  if (isLoading) return <p className="note">Loading trends…</p>
  if (error || !data) return <div className="err-box">{errorText(error)}</div>
  const themes = data.themes.filter(t => !followedOnly || t.followed)
  const b = data.brief
  const byId = Object.fromEntries(data.themes.map(t => [t.id, t]))
  const mk = b?.market as Record<string, number> | undefined

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
      <div style={{ display: 'flex', flexWrap: 'wrap', gap: 10, alignItems: 'flex-end' }}>
        <div style={{ flex: '1 1 360px' }}>
          <div className="sec-title">Trends</div>
          <div className="sec-sub" style={{ marginBottom: 0 }}>
            Where venture and growth capital is going, and where to deploy. <b>Early</b> = latest post-money below ${data.early_max_usd_bn}bn;
            {' '}<b>Growth</b> = private at ${data.early_max_usd_bn}bn or more. Updated weekly{b ? ` · as of ${b.as_of}` : ''}.
          </div>
        </div>
        <div style={{ display: 'flex', gap: 8, alignItems: 'center', flexWrap: 'wrap' }}>
          <button className="btn" onClick={() => setShowFw(true)}>ⓘ How heat &amp; deploy work</button>
          <div className="toggle-bar" role="tablist" aria-label="Stage" style={{ marginBottom: 0 }}>
            {(['all', 'early', 'growth'] as const).map(s => (
              <button key={s} role="tab" aria-selected={stage === s} className={`tog-btn${stage === s ? ' on' : ''}`} onClick={() => setStage(s)}>
                {s === 'all' ? 'All stages' : s === 'early' ? 'Early' : 'Growth'}
              </button>
            ))}
          </div>
          <label className="note" style={{ display: 'inline-flex', gap: 5, alignItems: 'center', cursor: 'pointer' }}>
            <input type="checkbox" checked={followedOnly} onChange={e => setFollowedOnly(e.target.checked)} /> Followed themes only
          </label>
        </div>
      </div>

      {b && (
        <div className="tr-brief">
          <div className="tr-brief-main">
            <div className="eyebrow">Weekly brief · {b.as_of}</div>
            <h2>{b.headline}</h2>
            <p>{b.summary}</p>
            {b.market?.sources && <div className="note">Sources: {b.market.sources.map((s, i) => <span key={s.url}>{i ? ' · ' : ''}<a href={s.url} target="_blank" rel="noopener noreferrer">{s.label}</a></span>)}</div>}
          </div>
          <div className="tr-brief-side"><PointsView title="This week's signals" points={b.highlights} /></div>
        </div>
      )}

      {mk && (
        <div className="atl-kpis">
          {mk.q3_2026_global_vc_usd_bn != null && <Kpi label="Global VC, latest quarter" value={money(mk.q3_2026_global_vc_usd_bn)} sub={`AI ${mk.q3_2026_ai_share_pct}% · ${mk.q3_2026_billion_rounds} rounds of $1bn+`} dark />}
          {mk.q3_2026_early_usd_bn != null && <Kpi label="Early vs late stage" value={`${money(mk.q3_2026_early_usd_bn)} / ${money(mk.q3_2026_late_usd_bn)}`} sub="Early / late, latest quarter" />}
          {mk.enterprise_ai_spend_2026_usd_bn != null && <Kpi label="Enterprise AI spend 2026" value={money(mk.enterprise_ai_spend_2026_usd_bn)} sub="Menlo Ventures estimate" gold />}
          {mk.hyperscaler_capex_2026_usd_bn != null && <Kpi label="Hyperscaler capex 2026" value={money(mk.hyperscaler_capex_2026_usd_bn)} sub="Big-4 guidance (demand backdrop)" />}
          <Kpi label="Themes tracked" value={data.themes.length} sub={`${data.themes.reduce((n, t) => n + t.stats.companies, 0)} companies on the map`} />
        </div>
      )}

      <DeployBoard themes={themes} stage={stage} picks={b ? [...b.deploy_now] : []} byId={byId} onHelp={() => setShowFw(true)} />
      <HeatRanking themes={themes} prev={data.heat_prev} onHelp={() => setShowFw(true)} />
      <MarketMap themes={themes} stage={stage} only={mapTheme} setOnly={setMapTheme} />
      <CapitalFlows themes={themes} />
      <ValuationEvolution themes={themes} stage={stage} />
      <ReadingList data={data} />
      {b?.playbook?.length ? <Playbook items={b.playbook} /> : null}
      {showFw && data.framework && <FrameworkModal fw={data.framework} onClose={() => setShowFw(false)} />}
    </div>
  )
}

// ── deploy board ─────────────────────────────────────────────────────────────
function DeployBoard({ themes, stage, picks, byId, onHelp }: { themes: TrTheme[]; stage: StageView; picks: { theme: string; stage: string; why: string }[]; byId: Record<string, TrTheme>; onHelp: () => void }) {
  const rows = themes.flatMap(t => {
    const st = stage === 'all' ? (['early', 'growth'] as const) : [stage]
    const by = new Map<Deploy, string[]>()
    st.forEach(x => { const d = x === 'early' ? t.deploy_early : t.deploy_growth; by.set(d, [...(by.get(d) ?? []), x]) })
    return [...by.entries()].map(([d, ss]) => ({ t, ss, d }))
  })
  const pk = picks.filter(p => stage === 'all' || p.stage === stage).filter(p => byId[p.theme])
  return (
    <Card title={`Where to deploy · ${stage === 'all' ? 'early and growth' : stage}`}
      right={<button className="linkish" onClick={onHelp}>What do Overweight / Selective / Watch / Avoid mean?</button>}>
      {pk.length > 0 && (
        <div className="tr-picks">
          {pk.map((p, i) => (
            <button key={i} className="tr-pick" onClick={() => go(`th-${p.theme}`)} style={{ borderLeftColor: byId[p.theme].color || 'var(--gold)' }}>
              <span className="tr-pick-hd">{byId[p.theme].name} <span className={`stg stg-${p.stage}`}>{STAGE_LABEL[p.stage] ?? p.stage}</span></span>
              <span className="sub">{p.why}</span>
            </button>
          ))}
        </div>
      )}
      <div className="tr-board">
        {DEPLOY_COLS.map(c => {
          const hit = rows.filter(r => r.d === c.id).sort((a, b) => (b.t.heat ?? 0) - (a.t.heat ?? 0))
          return (
            <div key={c.id} className={`tr-col tr-col-${c.id}`}>
              <div className="tr-col-hd"><DeployTag d={c.id} /> <span className="note">{c.hint}</span></div>
              {hit.length ? hit.map(r => (
                <button key={r.t.id} className="tr-chip" onClick={() => go(`th-${r.t.id}`)} title={r.t.deploy_view}>
                  <span className="dot" style={{ background: r.t.color || 'var(--navy)' }} />{r.t.name}
                  {stage === 'all' && <span className="tr-chip-st">{r.ss.map(x => <span key={x} className={`stg stg-${x}`}>{STAGE_LABEL[x]}</span>)}</span>}
                </button>
              )) : <span className="note">None</span>}
            </div>
          )
        })}
      </div>
    </Card>
  )
}

// ── heat ranking ─────────────────────────────────────────────────────────────
function HeatRanking({ themes, prev, onHelp }: { themes: TrTheme[]; prev: Record<string, number>; onHelp: () => void }) {
  const sorted = [...themes].sort((a, b) => (b.heat ?? 0) - (a.heat ?? 0))
  return (
    <Card title="Theme heat (0–100)" right={<span style={{ display: 'flex', gap: 10, alignItems: 'center', flexWrap: 'wrap' }}><CompLegend /><button className="linkish" onClick={onHelp}>How is heat measured?</button></span>}>
      <div className="heat-list">
        {sorted.map((t, i) => {
          const d = prev[t.id] != null && t.heat != null ? t.heat - prev[t.id] : null
          return (
            <button key={t.id} className="heat-row" onClick={() => go(`th-${t.id}`)}>
              <span className="heat-rank">{i + 1}</span>
              <span className="heat-name">{t.name}{!t.followed && <span className="note"> · not followed</span>}</span>
              <HeatStack comps={t.score.components} />
              <span className="heat-val">{t.heat ?? '—'}</span>
              <span className={`heat-d ${d && d > 0 ? 'up' : d && d < 0 ? 'down' : ''}`}>{d == null ? '' : d === 0 ? '·' : `${d > 0 ? '▲' : '▼'}${Math.abs(d)}`}</span>
              <span className="heat-sig"><SignalBadge s={t.signal} /></span>
              <span className="heat-dep"><DeployTag d={t.deploy_early} /><DeployTag d={t.deploy_growth} /></span>
            </button>
          )
        })}
      </div>
      <p className="note" style={{ marginTop: 6 }}>Bar segments show the points each input contributes (hover for detail). Δ = change vs last week. Right-hand tags: deploy view for Early, then Growth. Heat is momentum, not a buy signal: see the deploy board.</p>
    </Card>
  )
}

// ── market map ───────────────────────────────────────────────────────────────
// Every map company opens in-app: tracked ones open their full profile drawer, the rest a details popup.
type MapCoSel = { c: TrCompany; theme?: string; segment?: string }
const useMapCo = create<{ sel: MapCoSel | null; open: (s: MapCoSel) => void; close: () => void }>(set => ({
  sel: null, open: sel => set({ sel }), close: () => set({ sel: null }),
}))

function useOpenCo() {
  const { companies } = useData()
  const open = useMapCo(s => s.open)
  const tracked = useMemo(() => new Set(companies.map(c => c.id)), [companies])
  return (c: TrCompany, theme?: string, segment?: string) => {
    if (c.tracked && c.id && tracked.has(c.id)) go(`co-${c.id}`)
    else open({ c, theme, segment })
  }
}

function Tile({ c, theme, segment }: { c: TrCompany; theme?: string; segment?: string }) {
  const openCo = useOpenCo()
  const tip = [c.name, c.description, c.valuation_usd_bn ? `${money(c.valuation_usd_bn)} (${c.valuation_date || 'n.d.'}${c.valuation_label ? `, ${c.valuation_label}` : ''})` : '',
    c.last_round, 'Click for details'].filter(Boolean).join('\n')
  return (
    <button className={`tile tile-${c.stage}`} title={tip} onClick={() => openCo(c, theme, segment)}>
      <Logo domain={c.domain} name={c.name} />
      <span className="tile-nm">{c.name.replace(/ \(.*\)$/, '')}</span>
      <span className="tile-v">{c.valuation_usd_bn ? money(c.valuation_usd_bn) : STAGE_LABEL[c.stage]}</span>
    </button>
  )
}

export function MapCoModal() {
  const { sel, close } = useMapCo()
  const { managers } = useData()
  useEffect(() => {
    if (!sel) return
    const k = (e: KeyboardEvent) => { if (e.key === 'Escape') close() }
    window.addEventListener('keydown', k)
    return () => window.removeEventListener('keydown', k)
  }, [sel, close])
  if (!sel) return null
  const { c, theme, segment } = sel
  const site = c.domain ? `https://${c.domain.replace(/^https?:\/\//, '')}` : ''
  const gpByName = (n: string) => {
    const k = n.toLowerCase().replace(/[^a-z0-9]/g, '')
    return managers.find(m => m.name.toLowerCase().replace(/[^a-z0-9]/g, '') === k || m.id === k)
  }
  return (
    <div className="modal-overlay" onClick={close}>
      <div className="modal-panel" role="dialog" aria-modal="true" aria-label={c.name} onClick={e => e.stopPropagation()}>
        <div className="modal-header" style={{ alignItems: 'flex-start', gap: 12 }}>
          <Logo domain={c.domain} name={c.name} size={40} />
          <div style={{ minWidth: 0 }}>
            <div className="modal-title" style={{ display: 'flex', alignItems: 'center', flexWrap: 'wrap' }}>{c.name}<span className={`stg stg-${c.stage}`}>{STAGE_LABEL[c.stage]}</span></div>
            <div className="note">{[theme, segment].filter(Boolean).join(' · ')}</div>
            {site && <a href={site} target="_blank" rel="noopener noreferrer" style={{ fontSize: 12.5 }}>{c.domain} ↗</a>}
          </div>
          <button className="btn" style={{ marginLeft: 'auto' }} onClick={close}>Close</button>
        </div>
        <div className="modal-body" style={{ overflowY: 'auto', padding: '14px 20px 20px', display: 'flex', flexDirection: 'column', gap: 14 }}>
          {c.description && <p style={{ margin: 0 }}>{c.description}</p>}
          <div className="facts">
            <div><div className="k">Latest valuation</div><div className="v big">{c.valuation_usd_bn ? money(c.valuation_usd_bn) : '—'}</div>
              <div className="note">{[c.valuation_date, c.valuation_label].filter(Boolean).join(' · ')}</div></div>
            <div><div className="k">Stage</div><div className="v">{STAGE_LABEL[c.stage]}</div><div className="note">{c.status}</div></div>
            {c.hq && <div><div className="k">HQ</div><div className="v">{c.hq}</div></div>}
            {c.revenue_usd_bn ? <div><div className="k">{c.revenue_metric || 'Revenue'}</div><div className="v">{money(c.revenue_usd_bn)}</div></div> : null}
            {c.last_round && <div style={{ gridColumn: '1 / -1' }}><div className="k">Last round</div><div className="v" style={{ fontWeight: 500 }}>{c.last_round}</div></div>}
          </div>
          {c.investors?.length > 0 && (
            <div>
              <div className="mm-seg-nm">Investors</div>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
                {c.investors.map(n => {
                  const m = gpByName(n)
                  return m
                    ? <button key={n} className="chip on" onClick={() => { close(); go(`gp-${m.id}`) }} title="Tracked GP: open profile">{n}</button>
                    : <span key={n} className="chip" style={{ cursor: 'default' }}>{n}</span>
                })}
              </div>
            </div>
          )}
          {c.note && <p className="note" style={{ margin: 0 }}>{c.note}</p>}
          {c.rounds?.length > 0 && (
            <table className="mini-tbl"><thead><tr><th>Date</th><th>Round</th><th>Post-money</th></tr></thead>
              <tbody>{c.rounds.map(r => <tr key={r.date + r.round}><td>{r.date}</td><td>{r.round}</td><td>{money(r.post_money_usd_bn)}</td></tr>)}</tbody></table>
          )}
          <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', alignItems: 'center' }}>
            {site && <a className="btn btn-primary" href={site} target="_blank" rel="noopener noreferrer">Visit website ↗</a>}
            {c.url && <a className="btn" href={c.url} target="_blank" rel="noopener noreferrer">Source ↗</a>}
            <span className="note">From the Trends market map; not yet a tracked company, so there is no full profile.</span>
          </div>
        </div>
      </div>
    </div>
  )
}

function MarketMap({ themes, stage, only, setOnly }: { themes: TrTheme[]; stage: StageView; only: string; setOnly: (v: string) => void }) {
  const shown = themes.filter(t => !only || t.id === only)
  return (
    <Card title="Market map" right={
      <div style={{ display: 'flex', gap: 8, alignItems: 'center', flexWrap: 'wrap' }}>
        <span className="legend"><span className="tile-key key-early" />Early</span><span className="legend"><span className="tile-key key-growth" />Growth</span>
        <span className="legend"><span className="tile-key key-public" />Public / exited</span>
        <select className="tbl-sel" aria-label="Map theme" value={only} onChange={e => setOnly(e.target.value)}>
          <option value="">All themes</option>{themes.map(t => <option key={t.id} value={t.id}>{t.name}</option>)}
        </select>
      </div>}>
      <div className="mm-grid">
        {shown.map(t => {
          const segs = t.segments.map(s => ({ ...s, companies: s.companies.filter(c => inStage(c, stage)) })).filter(s => s.companies.length)
          if (!segs.length) return null
          return (
            <section key={t.id} className="mm-theme" style={{ borderTopColor: t.color || 'var(--navy)' }}>
              <button className="mm-hd" onClick={() => go(`th-${t.id}`)}>
                <span className="mm-name">{t.name}</span><SignalBadge s={t.signal} /><span className="mm-heat">{t.heat}</span>
              </button>
              {segs.map(s => (
                <div key={s.name} className="mm-seg">
                  <div className="mm-seg-nm">{s.name}</div>
                  <div className="mm-tiles">{s.companies.map(c => <Tile key={c.name} c={c} theme={t.name} segment={s.name} />)}</div>
                </div>
              ))}
            </section>
          )
        })}
      </div>
      <p className="note" style={{ marginTop: 8 }}>Logos via each company's website icon. Valuations: the newer of the tracker's mark and the theme's sourced mark. Click any company for details; tracked companies open their full profile.</p>
    </Card>
  )
}

// ── capital flows ────────────────────────────────────────────────────────────
function CapitalFlows({ themes }: { themes: TrTheme[] }) {
  const rows = themes.flatMap(t => t.funding.filter(f => f.capital_usd_bn != null && f.metric !== 'market').slice(0, 2).map(f => ({ t, f })))
    .sort((a, b) => (b.f.capital_usd_bn ?? 0) - (a.f.capital_usd_bn ?? 0))
  const max = Math.max(...rows.map(r => r.f.capital_usd_bn ?? 0), 1)
  return (
    <Card title="Venture capital raised by theme (latest reported)" right={<span className="note">Venture rounds only (market-size and spend figures are in each theme). Periods differ by source; compare within a theme over time</span>}>
      <div className="cf-list">
        {rows.map(({ t, f }, i) => (
          <div key={i} className="cf-row">
            <button className="cf-name" onClick={() => go(`th-${t.id}`)}>{t.name}</button>
            <span className="cf-bar"><span style={{ width: `${Math.max(2, ((f.capital_usd_bn ?? 0) / max) * 100)}%`, background: t.color || 'var(--navy)' }} /></span>
            <span className="cf-v">{money(f.capital_usd_bn)}</span>
            <span className="cf-p">{f.period}{f.deals ? ` · ${f.deals} deals` : ''}{f.note ? <span className="sub"> · {clip(f.note, 90)}</span> : null}</span>
            <span className="cf-s">{f.url ? <a href={f.url} target="_blank" rel="noopener noreferrer">{f.source}</a> : f.source}</span>
          </div>
        ))}
      </div>
    </Card>
  )
}

// ── valuation evolution ──────────────────────────────────────────────────────
function MarksChart({ marks, stage, height = 300 }: { marks: TrMark[]; stage: StageView; height?: number }) {
  const pts = marks.filter(m => m.date >= '2015' && (stage === 'all' || m.stage === stage)).map(m => ({ ...m, x: ym(m.date), y: m.post_money_usd_bn }))
  if (pts.length < 2) return <p className="note">Not enough priced rounds in the tracker for this view.</p>
  const lo = Math.min(...pts.map(p => p.y)), hi = Math.max(...pts.map(p => p.y))
  const ticks: number[] = []
  for (let e = Math.floor(Math.log10(lo)); e <= Math.ceil(Math.log10(hi)); e++) ticks.push(10 ** e)
  const early = pts.filter(p => p.stage === 'early'), growth = pts.filter(p => p.stage === 'growth')
  return (
    <div style={{ width: '100%', height }}>
      <ResponsiveContainer>
        <ScatterChart margin={{ top: 10, right: 16, left: 4, bottom: 4 }}>
          <CartesianGrid stroke="var(--border)" />
          <XAxis type="number" dataKey="x" domain={['dataMin - 0.3', 'dataMax + 0.3']} tickFormatter={v => String(Math.floor(v as number))}
            tick={{ fontSize: 10, fill: 'var(--muted)' }} allowDecimals={false} name="Date" />
          <YAxis type="number" dataKey="y" scale="log" domain={[ticks[0], ticks[ticks.length - 1]]} ticks={ticks} allowDataOverflow
            tickFormatter={v => money(v as number)} tick={{ fontSize: 10, fill: 'var(--muted)' }} width={56} name="Post-money" />
          <ZAxis range={[36, 36]} />
          <Tooltip cursor={{ strokeDasharray: '3 3' }} content={({ payload }) => {
            const p = payload?.[0]?.payload as (TrMark & { y: number }) | undefined
            return p ? <div className="chart-tip"><b>{p.company}</b><br />{p.date} · {p.round}<br />{money(p.y)} post-money</div> : null
          }} />
          {stage !== 'growth' && <Scatter name="Early" data={early} fill="var(--gold)" isAnimationActive={false} />}
          {stage !== 'early' && <Scatter name="Growth" data={growth} fill="var(--navy)" isAnimationActive={false} />}
        </ScatterChart>
      </ResponsiveContainer>
    </div>
  )
}

function ValuationEvolution({ themes, stage }: { themes: TrTheme[]; stage: StageView }) {
  const withMarks = themes.filter(t => t.marks.length >= 2)
  const [sel, setSel] = useState('')
  const t = withMarks.find(x => x.id === sel) ?? withMarks.find(x => x.id === 'physical-ai-robotics') ?? withMarks[0]
  const movers = useMemo(() => (t ? t.segments.flatMap(s => s.companies) : []).filter(c => c.step_up_x && inStage(c, stage))
    .sort((a, b) => (b.step_up_x ?? 0) - (a.step_up_x ?? 0)).slice(0, 6), [t, stage])
  if (!t) return null
  return (
    <Card title="Valuation evolution" right={
      <select className="tbl-sel" aria-label="Theme for valuation chart" value={t.id} onChange={e => setSel(e.target.value)}>
        {withMarks.map(x => <option key={x.id} value={x.id}>{x.name}</option>)}
      </select>}>
      <div className="grid2">
        <div>
          <MarksChart marks={t.marks} stage={stage} />
          <p className="note">Each dot is a priced round (post-money, log scale) for this theme's tracked companies. Gold = early (below $1bn), navy = growth.</p>
        </div>
        <div>
          <div className="card-title">Biggest step-ups since first mark</div>
          {movers.length ? (
            <table className="mini-tbl"><thead><tr><th>Company</th><th>Latest</th><th>Step-up</th></tr></thead>
              <tbody>{movers.map(c => (
                <tr key={c.name} style={{ cursor: c.id ? 'pointer' : undefined }} onClick={() => c.id && go(`co-${c.id}`)}>
                  <td><span style={{ display: 'inline-flex', gap: 6, alignItems: 'center' }}><Logo domain={c.domain} name={c.name} size={18} />{c.name}</span></td>
                  <td>{money(c.valuation_usd_bn)}<div className="sub">{c.valuation_date}</div></td><td><b>{(c.step_up_x ?? 0).toFixed(1)}x</b></td></tr>
              ))}</tbody></table>
          ) : <p className="note">No tracked step-ups for this stage.</p>}
          {t.valuation_notes && <p style={{ fontSize: 12.5, marginTop: 10 }}>{t.valuation_notes}</p>}
        </div>
      </div>
    </Card>
  )
}

// ── reading list ─────────────────────────────────────────────────────────────
function ResourceRow({ r, themeName, canEdit, onHide }: { r: TrResource; themeName?: string; canEdit: boolean; onHide: (id: number) => void }) {
  return (
    <li className="rl-item">
      <div className="rl-hd">
        <span className={`badge ${r.kind === 'report' ? 'badge-blue' : r.kind === 'podcast' || r.kind === 'video' || r.kind === 'interview' ? 'badge-gold' : 'badge-gray'}`}>{r.kind}</span>
        {themeName && <span className="note">{themeName}</span>}
        {r.pinned && <span className="note" title="Pinned">★</span>}
        <span className="note">{r.date}</span>
        {canEdit && <button className="pb" style={{ marginLeft: 'auto' }} aria-label={`Remove ${r.title}`} title="Remove (won't come back on the weekly update)" onClick={() => onHide(r.id)}>✕</button>}
      </div>
      <a className="rl-t" href={r.url} target="_blank" rel="noopener noreferrer">{r.title}</a>
      <div className="note">{r.source}{r.summary ? ` · ${r.summary}` : ''}</div>
    </li>
  )
}

function ReadingList({ data }: { data: TrendsData }) {
  const qc = useQueryClient()
  const [theme, setTheme] = useState('')
  const [kind, setKind] = useState('')
  const [q, setQ] = useState('')
  const [adding, setAdding] = useState(false)
  const names = Object.fromEntries(data.themes.map(t => [t.id, t.name]))
  const all = [...data.resources, ...data.themes.flatMap(t => t.resources)]
  const list = all.filter(r => (!theme || (theme === '_global' ? !r.theme : r.theme === theme)) && (!kind || r.kind === kind)
    && (!q || `${r.title} ${r.source} ${r.summary}`.toLowerCase().includes(q.toLowerCase())))
    .sort((a, b) => Number(b.pinned) - Number(a.pinned) || (b.date || '').localeCompare(a.date || ''))
  const hide = async (id: number) => { await api.delete(`/trends/resources/${id}/`); await qc.invalidateQueries({ queryKey: KEY }) }
  return (
    <Card title={`Reading list & repository (${all.length})`} right={data.can_edit ? <button className="btn btn-primary" onClick={() => setAdding(true)}>+ Add link</button> : undefined}>
      <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', marginBottom: 10 }}>
        <select className="tbl-sel" aria-label="Theme" value={theme} onChange={e => setTheme(e.target.value)}>
          <option value="">All themes</option><option value="_global">Market-wide</option>
          {data.themes.map(t => <option key={t.id} value={t.id}>{t.name}</option>)}
        </select>
        <div className="chips">
          <button className={`chip${!kind ? ' on' : ''}`} onClick={() => setKind('')}>All</button>
          {KINDS.map(([k, l]) => all.some(r => r.kind === k) && <button key={k} className={`chip${kind === k ? ' on' : ''}`} onClick={() => setKind(kind === k ? '' : k)}>{l}</button>)}
        </div>
        <input type="search" className="tbl-search" placeholder="Search links…" aria-label="Search links" value={q} onChange={e => setQ(e.target.value)} />
      </div>
      <ul className="rl-list">{list.slice(0, 120).map(r => <ResourceRow key={r.id} r={r} themeName={r.theme ? names[r.theme] : 'Market-wide'} canEdit={data.can_edit} onHide={id => void hide(id)} />)}</ul>
      {!list.length && <p className="note">No links match.</p>}
      {adding && <AddLink themes={data.themes} onClose={() => setAdding(false)} preset={theme && theme !== '_global' ? theme : ''} />}
    </Card>
  )
}

function AddLink({ themes, onClose, preset }: { themes: TrTheme[]; onClose: () => void; preset: string }) {
  const qc = useQueryClient()
  const [f, setF] = useState({ title: '', url: '', theme: preset, kind: 'article', source: '', date: '', summary: '' })
  const [err, setErr] = useState<string | null>(null)
  const submit = async (e: React.FormEvent) => {
    e.preventDefault(); setErr(null)
    try { await api.post('/trends/resources/', f); await qc.invalidateQueries({ queryKey: KEY }); onClose() } catch (ex) { setErr(errorText(ex)) }
  }
  const set = (k: keyof typeof f) => (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement>) => setF({ ...f, [k]: e.target.value })
  return (
    <div className="modal-overlay" onClick={onClose}>
      <form className="modal-panel" onClick={e => e.stopPropagation()} onSubmit={submit}>
        <div className="modal-header"><div className="modal-title">Add to the reading list</div><button type="button" className="btn" onClick={onClose}>Cancel</button></div>
        <div className="modal-body">
          <div className="form-group"><label className="form-label" htmlFor="rl-url">Link</label><input id="rl-url" className="form-input" style={{ width: '100%' }} required placeholder="https://…" value={f.url} onChange={set('url')} /></div>
          <div className="form-group"><label className="form-label" htmlFor="rl-title">Title</label><input id="rl-title" className="form-input" style={{ width: '100%' }} required value={f.title} onChange={set('title')} /></div>
          <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap' }}>
            <div className="form-group"><label className="form-label" htmlFor="rl-theme">Theme</label>
              <select id="rl-theme" className="form-select" value={f.theme} onChange={set('theme')}><option value="">Market-wide</option>{themes.map(t => <option key={t.id} value={t.id}>{t.name}</option>)}</select></div>
            <div className="form-group"><label className="form-label" htmlFor="rl-kind">Type</label>
              <select id="rl-kind" className="form-select" value={f.kind} onChange={set('kind')}>{KINDS.map(([k, l]) => <option key={k} value={k}>{l}</option>)}</select></div>
            <div className="form-group"><label className="form-label" htmlFor="rl-date">Date</label><input id="rl-date" className="form-input" placeholder="YYYY-MM-DD" value={f.date} onChange={set('date')} /></div>
          </div>
          <div className="form-group"><label className="form-label" htmlFor="rl-src">Source</label><input id="rl-src" className="form-input" style={{ width: '100%' }} placeholder="e.g. 20VC, Menlo Ventures" value={f.source} onChange={set('source')} /></div>
          <div className="form-group"><label className="form-label" htmlFor="rl-sum">Why it matters</label><textarea id="rl-sum" className="form-textarea" rows={2} style={{ width: '100%' }} value={f.summary} onChange={set('summary')} /></div>
          {err && <div className="err-box">{err}</div>}
        </div>
        <div className="modal-footer"><button className="btn btn-primary" type="submit">Add</button></div>
      </form>
    </div>
  )
}

function Playbook({ items }: { items: TrBrief['playbook'] }) {
  return (
    <Card title="How to stay on top of it">
      <div className="pbk">
        {items.map((p, i) => (
          <div key={i} className="pbk-item">
            <div className="pbk-n">{i + 1}</div>
            <div>
              <div className="pbk-t">{p.title} <span className="note">· {p.cadence}</span></div>
              <div style={{ fontSize: 12.5 }}>{p.detail}</div>
              {p.links?.length > 0 && <div className="note">{p.links.map((l, j) => <span key={l}>{j ? ' · ' : ''}<a href={l} target="_blank" rel="noopener noreferrer">{l.replace(/^https?:\/\/(www\.)?/, '').split('/')[0]}</a></span>)}</div>}
            </div>
          </div>
        ))}
      </div>
    </Card>
  )
}

// ── theme drawer ─────────────────────────────────────────────────────────────
export function ThemeDrawer({ id }: { id: string }) {
  const { data } = useTrends()
  const qc = useQueryClient()
  const { companies } = useData()
  const t = data?.themes.find(x => x.id === id)
  const [model, setModel] = useState('')
  const [note, setNote] = useState<string | null>(null)
  const [err, setErr] = useState<string | null>(null)
  useEffect(() => { if (data && !model) setModel(data.defaults.company) }, [data, model])
  if (!data) return <Drawer title="Loading…"><p className="note">Loading…</p></Drawer>
  if (!t) return <Drawer title="Not found"><p className="note">Unknown theme.</p></Drawer>
  const busy = t.research_status === 'queued' || t.research_status === 'running'
  const run = async (f: () => Promise<unknown>) => { setErr(null); try { await f(); await qc.invalidateQueries({ queryKey: KEY }) } catch (e) { setErr(errorText(e)) } }
  const refresh = () => run(async () => { await api.post(`/trends/themes/${t.id}/refresh/`, { model }); void useResearch.getState().refresh() })
  const est = data.models.find(m => m.id === model)?.est_company
  const fund = t.funding.filter(f => f.capital_usd_bn != null)
  const tracked = new Set(companies.map(c => c.id))
  const openCo = useOpenCo()

  return (
    <Drawer eyebrow={`Trend theme · ${t.category}`} title={t.name}
      actions={<>
        {data.can_edit && <button className="btn" onClick={() => void run(() => api.patch(`/trends/themes/${t.id}/`, { followed: !t.followed }))}>{t.followed ? '★ Following' : '☆ Follow'}</button>}
        {data.can_edit && data.enabled && <>
          {!busy && <select aria-label="Model for refresh" className="tbl-sel" value={model} onChange={e => setModel(e.target.value)}>{data.models.map(m => <option key={m.id} value={m.id}>{m.label.split(' · ')[0]}</option>)}</select>}
          <button className="btn btn-primary" disabled={busy} onClick={() => void refresh()} title={est ? `About $${(est * 1.5).toFixed(2)}` : undefined}>{busy ? 'Refreshing…' : 'Refresh theme'}</button>
        </>}
      </>}>
      {err && <div className="err-box" style={{ marginBottom: 10 }}>{err}</div>}
      <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', alignItems: 'center', marginBottom: 12 }}>
        <SignalBadge s={t.signal} /><span className="badge badge-gray">Heat {t.heat ?? '—'}</span>
        <span className="badge badge-gray">Conviction: {t.conviction || '—'}</span><span className="badge badge-gray">Horizon: {t.horizon || '—'}</span>
        <span className="note">Early</span><DeployTag d={t.deploy_early} /><span className="note">Growth</span><DeployTag d={t.deploy_growth} />
        <span className="note">· updated {t.last_refreshed_at ? new Date(t.last_refreshed_at).toLocaleDateString('en-GB') : '—'}</span>
      </div>
      <p style={{ marginTop: 0 }}>{t.summary}</p>
      <Card title="Heat breakdown (how this score is calculated)"><HeatBreakdown t={t} /></Card>
      <div className="grid2" style={{ margin: '12px 0' }}>
        <Card title="Why now"><p style={{ margin: 0 }}>{t.why_now}</p></Card>
        <Card title="How to deploy (early vs growth)"><p style={{ margin: 0 }}>{t.deploy_view}</p></Card>
      </div>

      <div className="atl-kpis" style={{ marginBottom: 12 }}>
        <Kpi label="On the map" value={t.stats.companies} sub={`${t.stats.early} early · ${t.stats.growth} growth · ${t.stats.public} public/exited`} />
        <Kpi label="Private value mapped" value={money(t.stats.private_value_usd_bn)} sub="Sum of latest marks" />
        <Kpi label="Priced rounds, 12m" value={t.stats.rounds_12m} sub={`${t.stats.tracked} companies tracked in Atlas`} />
      </div>

      {fund.length > 0 && (
        <Card title="Funding (reported)">
          <table className="mini-tbl"><thead><tr><th>Period</th><th>Capital</th><th>Deals</th><th>Note</th><th>Source</th></tr></thead>
            <tbody>{t.funding.map((f, i) => (
              <tr key={i}><td>{f.period}{f.metric === 'market' && <div className="sub">market size / spend</div>}</td><td><b>{money(f.capital_usd_bn)}</b> <span className="note">{f.label}</span></td><td>{f.deals ?? '—'}</td><td className="sub">{f.note}</td>
                <td>{f.url ? <a href={f.url} target="_blank" rel="noopener noreferrer">{f.source}</a> : f.source}</td></tr>
            ))}</tbody></table>
        </Card>
      )}

      <Card title="Market map">
        {t.segments.map(s => (
          <div key={s.name} className="mm-seg" style={{ marginBottom: 12 }}>
            <div className="mm-seg-nm">{s.name}</div>
            <table className="mini-tbl"><thead><tr><th>Company</th><th>Stage</th><th>Valuation</th><th>Last round / note</th></tr></thead>
              <tbody>{s.companies.map(c => (
                <tr key={c.name} style={{ cursor: 'pointer' }} onClick={() => openCo(c, t.name, s.name)}>
                  <td><span style={{ display: 'inline-flex', gap: 7, alignItems: 'center' }}><Logo domain={c.domain} name={c.name} size={20} /><span><b style={{ fontWeight: 600 }}>{c.name}</b><div className="sub">{clip(c.description, 90)}</div></span></span></td>
                  <td><span className={`stg stg-${c.stage}`}>{STAGE_LABEL[c.stage]}</span></td>
                  <td>{money(c.valuation_usd_bn)}<div className="sub">{c.valuation_date}{c.valuation_label ? ` · ${c.valuation_label}` : ''}</div></td>
                  <td className="sub">{c.last_round || (c.investors?.length ? c.investors.join(', ') : '')}</td>
                </tr>
              ))}</tbody></table>
          </div>
        ))}
      </Card>

      {t.marks.length >= 2 && <Card title="Valuation evolution (tracked rounds)"><MarksChart marks={t.marks} stage="all" height={260} /></Card>}

      <div className="grid2" style={{ margin: '12px 0' }}>
        <Card><PointsView title="Catalysts" points={t.catalysts} /></Card>
        <Card><PointsView title="Risks" points={t.risks} /></Card>
      </div>
      {t.kpis.length > 0 && <Card title="Signals to watch"><ul className="plain">{t.kpis.map(k => <li key={k}>{k}</li>)}</ul></Card>}

      {t.heat_history.length > 1 && (
        <Card title="Heat over time">
          <div style={{ width: '100%', height: 160 }}>
            <ResponsiveContainer><LineChart data={t.heat_history} margin={{ top: 8, right: 12, left: 0, bottom: 0 }}>
              <CartesianGrid stroke="var(--border)" vertical={false} /><XAxis dataKey="as_of" tick={{ fontSize: 10, fill: 'var(--muted)' }} />
              <YAxis domain={[0, 100]} tick={{ fontSize: 10, fill: 'var(--muted)' }} width={30} /><Tooltip />
              <Line dataKey="heat" stroke={t.color || 'var(--navy)'} strokeWidth={2} isAnimationActive={false} />
            </LineChart></ResponsiveContainer>
          </div>
        </Card>
      )}

      <Card title={`Latest news (${t.news.length})`}>
        {t.news.length ? <ul className="sl-news">{t.news.slice(0, 20).map((n, i) => (
          <li key={i}><div className="sl-news-hd"><span className="note">{n.date}</span>{n.source && <span className="note">· {n.source}</span>}</div>
            <div className="sl-news-h">{n.url ? <a href={n.url} target="_blank" rel="noopener noreferrer">{n.headline}</a> : n.headline}</div>
            {n.summary && <div className="sub">{n.summary}</div>}</li>))}</ul>
          : <p className="note">No headlines yet; the weekly update and Refresh add them.</p>}
      </Card>

      <Card title={`Reading list (${t.resources.length})`}>
        {t.resources.length ? <ul className="rl-list">{t.resources.map(r => <ResourceRow key={r.id} r={r} canEdit={false} onHide={() => undefined} />)}</ul> : <p className="note">No links yet.</p>}
      </Card>

      <Card title="My thesis & kill criteria">
        {data.can_edit ? (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
            <textarea aria-label="My note" className="form-textarea" rows={4} value={note ?? t.user_note}
              placeholder="What would make you overweight? What would make you stop?" onChange={e => setNote(e.target.value)} />
            <div><button className="pb" disabled={note == null || note === t.user_note} onClick={() => void run(async () => { await api.patch(`/trends/themes/${t.id}/`, { user_note: note }); setNote(null) })}>Save note</button></div>
          </div>
        ) : <p style={{ margin: 0 }}>{t.user_note || '—'}</p>}
      </Card>

      {t.sources.length > 0 && <Card title="Sources"><ul className="plain">{t.sources.map(s => <li key={s}><a href={s} target="_blank" rel="noopener noreferrer">{s.replace(/^https?:\/\/(www\.)?/, '').slice(0, 90)}</a></li>)}</ul></Card>}
    </Drawer>
  )
}
