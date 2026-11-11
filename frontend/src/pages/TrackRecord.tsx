import { keepPreviousData, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { CommentsLog, PointsEditor, PointsView } from '../components/Commentary'
import DataTable, { type Col } from '../components/DataTable'
import Drawer from '../components/Drawer'
import { Card, Fact, GpChips, Kpi } from '../components/ui'
import { api, errorText } from '../lib/api'
import { money, pct, usdm, x2 } from '../lib/format'
import { closeDrawer, go } from '../lib/route'
import type { FundBucket, LpInvestment, Point, SheetSettings, TrackRecordData, TrSummary } from '../types'
import InvestmentForm from './InvestmentForm'
import { CoLogo, GpLogo, WithLogo } from '../components/Logo'

export const TR_KEY = ['track-record']
export type SheetKind = 'all' | 'direct' | 'funds'

export interface TrFilters { view: SheetKind; structure: string; status: string; sector: string; q: string }
export const NO_FILTERS: TrFilters = { view: 'all', structure: '', status: '', sector: '', q: '' }

function qs(f: TrFilters): string {
  const p = new URLSearchParams()
  Object.entries(f).forEach(([k, v]) => { if (v && !(k === 'view' && v === 'all')) p.set(k, v) })
  return p.toString()
}

export function useTrackRecord(f: TrFilters = NO_FILTERS) {
  return useQuery({
    queryKey: [...TR_KEY, f],
    queryFn: () => api.get<TrackRecordData>(`/track-record/investments/?${qs(f)}`).then(r => r.data),
    placeholderData: keepPreviousData,
  })
}

const irr = (i: LpInvestment, k: 'gross_irr' | 'net_irr') => (i.metrics.irr_nm ? 'n.m.' : pct(i.metrics[k]))
const reported = (i: LpInvestment) => (i.metrics.net_basis === 'reported' ? <span className="lbl lbl-HARD" title="Reported by the GP">GP</span> : i.metrics.net_basis === 'estimate' ? <span className="lbl lbl-ESTIMATE" title="Estimated after stated fees and carry">EST</span> : null)

function Kpis({ s, showCapacity }: { s: TrSummary; showCapacity: boolean }) {
  return (
    <div className="atl-kpis">
      <Kpi label="Investments" value={s.count} sub={`${s.active ?? 0} active`} />
      <Kpi label="Invested" value={usdm(s.invested_usd_m)} sub={`Realised ${usdm(s.realised_usd_m)}`} />
      <Kpi label="Total value" value={usdm(s.total_value_usd_m)} sub={`Unrealised ${usdm(s.current_usd_m)}`} />
      <Kpi label="Gross / net MOIC" value={`${x2(s.gross_moic)} · ${x2(s.net_moic)}`} sub="Pooled" dark gold />
      <Kpi label="Gross / net IRR" value={`${pct(s.gross_irr)} · ${pct(s.net_irr)}`} sub="Pooled XIRR on dated cash flows" dark />
      <Kpi label="DPI" value={x2(s.dpi)} sub="Realised ÷ invested" />
      {showCapacity && <Kpi label="Available capacity" value={usdm(s.capacity_usd_m)} sub="For co-investors" />}
    </div>
  )
}

function FundKpis({ fp, showCapacity }: { fp: TrackRecordData['fund_programme']; showCapacity: boolean }) {
  return (
    <div className="atl-kpis">
      <Kpi label="Funds · GPs" value={`${fp.count} · ${fp.gps ?? 0}`} sub={`Unfunded ${usdm(fp.unfunded_usd_m)}`} />
      <Kpi label="Commitments" value={usdm(fp.commitment_usd_m)} sub={`${pct(fp.pct_called, 0)} called`} />
      <Kpi label="Paid-in" value={usdm(fp.called_usd_m)} sub={`Distributed ${usdm(fp.distributed_usd_m)}`} />
      <Kpi label="NAV" value={usdm(fp.nav_usd_m)} sub={`Total value ${usdm(fp.total_value_usd_m)}`} />
      <Kpi label="Net TVPI" value={x2(fp.tvpi)} sub={`DPI ${x2(fp.dpi)} · RVPI ${x2(fp.rvpi)}`} dark gold />
      <Kpi label="Net IRR" value={pct(fp.net_irr)} sub="Paid-in-weighted fund net IRRs" dark />
      {showCapacity && <Kpi label="Available capacity" value={usdm(fp.capacity_usd_m)} sub="For co-investors" />}
    </div>
  )
}

function FundProgrammeSummary({ fp }: { fp: TrackRecordData['fund_programme'] }) {
  return (
    <div className="facts" style={{ marginBottom: 12 }}>
      <div><div className="k">Funds · GPs</div><div className="v big">{fp.count} · {fp.gps ?? 0}</div></div>
      <div><div className="k">Commitments</div><div className="v big">{usdm(fp.commitment_usd_m)}</div></div>
      <div><div className="k">Paid-in · % called</div><div className="v big">{usdm(fp.called_usd_m)} · {pct(fp.pct_called, 0)}</div></div>
      <div><div className="k">Distributed · NAV</div><div className="v big">{usdm(fp.distributed_usd_m)} · {usdm(fp.nav_usd_m)}</div></div>
      <div><div className="k">Net TVPI · DPI · RVPI</div><div className="v big">{x2(fp.tvpi)} · {x2(fp.dpi)} · {x2(fp.rvpi)}</div></div>
      <div><div className="k">Net IRR · unfunded</div><div className="v big">{pct(fp.net_irr)} · {usdm(fp.unfunded_usd_m)}</div></div>
    </div>
  )
}

function BucketTable({ rows, label, k }: { rows: FundBucket[]; label: string; k: 'vintage' | 'strategy' }) {
  return (
    <DataTable rows={rows} rowKey={b => String(b[k])} pageSize={50}
      cols={[
        { key: 'k', header: label, sort: b => b[k] ?? '', cell: b => <span className="nm">{b[k]}</span> },
        { key: 'n', header: 'Funds', numeric: true, sort: b => b.count, cell: b => b.count },
        { key: 'com', header: 'Commitment', numeric: true, sort: b => b.commitment_usd_m, cell: b => usdm(b.commitment_usd_m) },
        { key: 'called', header: 'Paid-in', numeric: true, sort: b => b.called_usd_m, cell: b => <>{usdm(b.called_usd_m)}<div className="sub">{pct(b.pct_called, 0)} called</div></> },
        { key: 'dist', header: 'Distributed', numeric: true, sort: b => b.distributed_usd_m, cell: b => usdm(b.distributed_usd_m) },
        { key: 'nav', header: 'NAV', numeric: true, sort: b => b.nav_usd_m, cell: b => usdm(b.nav_usd_m) },
        { key: 'tvpi', header: 'TVPI', numeric: true, sort: b => b.tvpi, cell: b => x2(b.tvpi) },
        { key: 'dpi', header: 'DPI', numeric: true, sort: b => b.dpi, cell: b => x2(b.dpi) },
        { key: 'rvpi', header: 'RVPI', numeric: true, sort: b => b.rvpi, cell: b => x2(b.rvpi) },
        { key: 'irr', header: 'Net IRR', numeric: true, sort: b => b.net_irr, cell: b => pct(b.net_irr) },
        { key: 'unf', header: 'Unfunded', numeric: true, sort: b => b.unfunded_usd_m, cell: b => usdm(b.unfunded_usd_m) },
      ]} />
  )
}

function directCols(): Col<LpInvestment>[] {
  return [
    { key: 'name', header: 'Company', sort: i => i.name, wrap: true, cell: i => <WithLogo logo={<CoLogo id={i.company_id} name={i.name} size={26} />}><div className="nm">{i.name}{!i.include_in_sheet && <span className="tag" style={{ marginLeft: 6 }}>not on sheet</span>}</div><div className="sub">{i.sector}</div></WithLogo> },
    { key: 'st', header: 'Structure', sort: i => i.structure_label, cell: i => <>{i.structure_label}<div className="sub">{i.vehicle}</div></> },
    { key: 'date', header: 'Round / date', sort: i => i.invest_date, cell: i => <>{i.round || '—'}<div className="sub">{i.invest_date}</div></> },
    { key: 'entry', header: 'Entry val.', numeric: true, sort: i => i.entry_valuation_usd_bn, cell: i => money(i.entry_valuation_usd_bn) },
    { key: 'inv', header: 'Invested', numeric: true, sort: i => i.metrics.invested_usd_m, cell: i => usdm(i.metrics.invested_usd_m) },
    { key: 'cur', header: 'Current', numeric: true, sort: i => i.metrics.current_usd_m, cell: i => <>{usdm(i.metrics.current_usd_m)}<div className="sub">{i.value_basis}</div></> },
    { key: 'real', header: 'Realised', numeric: true, sort: i => i.metrics.realised_usd_m, cell: i => usdm(i.metrics.realised_usd_m) },
    { key: 'gm', header: 'Gross MOIC', numeric: true, sort: i => i.metrics.gross_moic, cell: i => <span className={(i.metrics.gross_moic ?? 1) >= 1 ? 'pos' : 'neg'}>{x2(i.metrics.gross_moic)}</span> },
    { key: 'nm', header: 'Net MOIC', numeric: true, sort: i => i.metrics.net_moic, cell: i => <>{x2(i.metrics.net_moic)}{reported(i)}</> },
    { key: 'irr', header: 'IRR', numeric: true, sort: i => i.metrics.gross_irr, cell: i => <>{irr(i, 'gross_irr')}<div className="sub">{irr(i, 'net_irr')} net</div></> },
    { key: 'dpi', header: 'DPI', numeric: true, sort: i => i.metrics.dpi, cell: i => x2(i.metrics.dpi) },
    { key: 'lead', header: 'Lead / invested with', wrap: true, cell: i => <>{i.lead_investors.join(', ') || '—'}<div className="sub">{i.co_investors.slice(0, 4).join(', ')}</div></> },
    { key: 'cap', header: 'Capacity', numeric: true, sort: i => i.capacity_usd_m, cell: i => (i.capacity_usd_m ? usdm(i.capacity_usd_m) : '—') },
  ]
}

function fundCols(): Col<LpInvestment>[] {
  return [
    { key: 'name', header: 'Fund / GP', sort: i => i.vehicle || i.name, wrap: true, cell: i => <WithLogo logo={<GpLogo id={i.manager_id} name={i.manager_name || i.name} size={26} />}><div className="nm">{i.vehicle || i.name}</div><div className="sub">{i.manager_name}</div></WithLogo> },
    { key: 'type', header: 'Type', sort: i => i.structure_label, cell: i => i.structure_label },
    { key: 'vin', header: 'Vintage', numeric: true, sort: i => i.vintage, cell: i => i.vintage ?? i.invest_date.slice(0, 4) },
    { key: 'com', header: 'Commitment', numeric: true, sort: i => i.commitment_usd_m, cell: i => usdm(i.commitment_usd_m) },
    { key: 'call', header: 'Called', numeric: true, sort: i => i.metrics.invested_usd_m, cell: i => usdm(i.metrics.invested_usd_m) },
    { key: 'dist', header: 'Distributed', numeric: true, sort: i => i.metrics.realised_usd_m, cell: i => usdm(i.metrics.realised_usd_m) },
    { key: 'nav', header: 'NAV', numeric: true, sort: i => i.metrics.current_usd_m, cell: i => usdm(i.metrics.current_usd_m) },
    { key: 'tvpi', header: 'Net TVPI', numeric: true, sort: i => i.metrics.net_moic, cell: i => <>{x2(i.metrics.net_moic)}{reported(i)}</> },
    { key: 'irr', header: 'Net IRR', numeric: true, sort: i => i.metrics.net_irr, cell: i => irr(i, 'net_irr') },
    { key: 'dpi', header: 'DPI', numeric: true, sort: i => i.metrics.net_dpi, cell: i => x2(i.metrics.net_dpi) },
    { key: 'unf', header: 'Unfunded', numeric: true, sort: i => i.metrics.unfunded_usd_m, cell: i => usdm(i.metrics.unfunded_usd_m) },
    { key: 'cap', header: 'Capacity', numeric: true, sort: i => i.capacity_usd_m, cell: i => (i.capacity_usd_m ? usdm(i.capacity_usd_m) : '—') },
  ]
}

const SHEET_NAME: Record<SheetKind, string> = { all: 'track-record', direct: 'direct-investments', funds: 'fund-programme' }

async function downloadPdf(commentary: boolean, f: TrFilters) {
  const kind = f.view
  const res = await api.get(`/track-record/pdf/?${qs(f)}&kind=${kind}&commentary=${commentary ? 1 : 0}`, { responseType: 'blob' })
  const url = URL.createObjectURL(res.data as Blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `${SHEET_NAME[kind]}-${new Date().toISOString().slice(0, 10)}.pdf`
  document.body.appendChild(a)
  a.click()
  a.remove()
  setTimeout(() => URL.revokeObjectURL(url), 3000)
}

function SettingsDialog({ settings, onClose }: { settings: SheetSettings; onClose: () => void }) {
  const qc = useQueryClient()
  const [s, setS] = useState(settings)
  const [err, setErr] = useState<string | null>(null)
  const f = (k: keyof SheetSettings) => (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => setS(p => ({ ...p, [k]: e.target.value }))
  return (
    <div className="modal-overlay" onClick={onClose}>
      <form className="modal-panel" style={{ maxWidth: 640 }} onClick={e => e.stopPropagation()}
        onSubmit={async e => { e.preventDefault(); try { await api.put('/track-record/settings/', s); await qc.invalidateQueries({ queryKey: TR_KEY }); onClose() } catch (e2) { setErr(errorText(e2)) } }}>
        <div className="modal-header"><div className="modal-title">Marketing sheet settings</div><button type="button" className="btn" onClick={onClose}>Cancel</button></div>
        <div className="modal-body">
          {(['title', 'subtitle', 'fund_title', 'fund_subtitle', 'prepared_by', 'contact'] as const).map(k => (
            <div className="form-group" key={k}>
              <label className="form-label" htmlFor={`ss-${k}`}>{{ title: 'Track record title', subtitle: 'Track record subtitle', fund_title: 'Fund programme title', fund_subtitle: 'Fund programme subtitle', prepared_by: 'Prepared by', contact: 'Contact' }[k]}</label>
              <input id={`ss-${k}`} className="form-input" style={{ width: '100%' }} value={s[k]} onChange={f(k)} />
            </div>
          ))}
          <div className="form-group">
            <label className="form-label" htmlFor="ss-disclaimer">Disclaimer</label>
            <textarea id="ss-disclaimer" className="form-textarea" rows={4} style={{ width: '100%' }} value={s.disclaimer} onChange={f('disclaimer')} />
          </div>
          <label className="chk"><input id="ss-cap" type="checkbox" checked={s.show_capacity} onChange={e => setS(p => ({ ...p, show_capacity: e.target.checked }))} /> Show available capacity on the sheet</label>
          {err && <div className="err-box" style={{ marginTop: 10 }}>{err}</div>}
        </div>
        <div className="modal-footer"><button className="btn btn-primary" type="submit">Save</button></div>
      </form>
    </div>
  )
}

const VIEW_LABEL: Record<SheetKind, string> = { all: 'All investments', direct: 'Directs & co-investments', funds: 'Funds' }

export default function TrackRecord() {
  const [f, setF] = useState<TrFilters>(() => {
    try { return { ...NO_FILTERS, view: (localStorage.getItem('atlas_tr_view') as SheetKind) || 'all' } } catch { return NO_FILTERS }
  })
  const [qText, setQText] = useState('')
  const { data, isLoading, error, isFetching } = useTrackRecord(f)
  const setFilter = <K extends keyof TrFilters>(k: K, v: TrFilters[K]) => {
    setF(p => ({ ...p, [k]: v }))
    if (k === 'view') { try { localStorage.setItem('atlas_tr_view', String(v)) } catch { /* ignore */ } }
  }
  // search is applied after a short pause so typing stays smooth
  const [qTimer, setQTimer] = useState<ReturnType<typeof setTimeout> | null>(null)
  const onSearch = (v: string) => {
    setQText(v)
    if (qTimer) clearTimeout(qTimer)
    setQTimer(setTimeout(() => setFilter('q', v.trim()), 300))
  }
  const qc = useQueryClient()
  const [adding, setAdding] = useState(false)
  const [settingsOpen, setSettingsOpen] = useState(false)
  const [commentary, setCommentary] = useState(false)
  const [pdfBusy, setPdfBusy] = useState(false)
  const [pdfErr, setPdfErr] = useState<string | null>(null)
  const getPdf = async (view: SheetKind = f.view) => { setPdfBusy(true); setPdfErr(null); try { await downloadPdf(commentary, { ...f, view }) } catch (e) { setPdfErr(errorText(e)) } setPdfBusy(false) }

  if (isLoading) return <div className="empty-state">Loading your track record…</div>
  if (error || !data) return <div className="err-box">{errorText(error)}</div>
  const directs = data.investments.filter(i => !i.is_fund)
  const funds = data.investments.filter(i => i.is_fund)
  const fc = data.facets
  const filtered = !!(f.structure || f.status || f.sector || f.q)
  const structOpts = fc.structures.filter(o => f.view === 'all' || (f.view === 'funds') === ['l1', 'l2'].includes(o.id))

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
      <div style={{ display: 'flex', flexWrap: 'wrap', gap: 10, alignItems: 'flex-end' }}>
        <div style={{ minWidth: 0 }}>
          <div className="sec-title">{data.settings.title}</div>
          <div className="sec-sub" style={{ marginBottom: 0 }}>{data.settings.subtitle}</div>
        </div>
        <div style={{ marginLeft: 'auto', display: 'flex', flexWrap: 'wrap', gap: 8, alignItems: 'center' }}>
          <label className="chk" title="Adds thesis, pros, cons, risks and comments to the PDF. Leave off for external sheets.">
            <input id="tr-commentary" type="checkbox" checked={commentary} onChange={e => setCommentary(e.target.checked)} /> Include commentary
          </label>
          <button className="btn btn-gold" disabled={pdfBusy || !data.investments.length} onClick={() => void getPdf()}
            title="Downloads exactly what is shown: the selected view and filters">
            {pdfBusy ? 'Preparing PDF…' : `Download PDF · ${f.view === 'funds' ? 'Fund programme' : VIEW_LABEL[f.view]}`}
          </button>
          {data.can_edit && <button className="btn" onClick={() => setSettingsOpen(true)}>Sheet settings</button>}
          {data.can_edit && <button className="btn btn-primary" onClick={() => setAdding(true)}>+ Add investment</button>}
        </div>
      </div>
      {pdfErr && <div className="err-box">{pdfErr}</div>}
      <div style={{ display: 'flex', flexWrap: 'wrap', gap: 10, alignItems: 'center' }}>
        <div className="toggle-bar" role="tablist" aria-label="View" style={{ marginBottom: 0 }}>
          {(['all', 'direct', 'funds'] as SheetKind[]).map(v => (
            <button key={v} role="tab" aria-selected={f.view === v} className={`tog-btn${f.view === v ? ' on' : ''}`}
              onClick={() => { setFilter('view', v); setFilter('structure', '') }}>
              {VIEW_LABEL[v]} <span className="note">{v === 'all' ? fc.total : v === 'direct' ? fc.direct : fc.funds}</span>
            </button>
          ))}
        </div>
        <input id="tr-q" type="search" className="tbl-search" placeholder="Search name, GP, investor…" value={qText} onChange={e => onSearch(e.target.value)} />
        <select id="tr-structure-f" aria-label="Structure" className="tbl-sel" value={f.structure} onChange={e => setFilter('structure', e.target.value)}>
          <option value="">Any structure</option>
          {structOpts.map(o => <option key={o.id} value={o.id}>{o.label} ({o.count})</option>)}
        </select>
        <select id="tr-status-f" aria-label="Status" className="tbl-sel" value={f.status} onChange={e => setFilter('status', e.target.value)}>
          <option value="">Any status</option>
          {fc.statuses.map(o => <option key={o.id} value={o.id}>{o.label} ({o.count})</option>)}
        </select>
        {f.view !== 'funds' && !!fc.sectors.length && (
          <select id="tr-sector-f" aria-label="Sector" className="tbl-sel" value={f.sector} onChange={e => setFilter('sector', e.target.value)}>
            <option value="">Any sector</option>
            {fc.sectors.map(o => <option key={o} value={o}>{o}</option>)}
          </select>
        )}
        {filtered && <button className="pb" onClick={() => { setQText(''); setF(p => ({ ...NO_FILTERS, view: p.view })) }}>Clear filters</button>}
        <span className="tbl-ct">{isFetching ? 'Updating…' : `Showing ${data.investments.length} of ${fc.total}`}</span>
      </div>
      {f.view === 'funds' ? <FundKpis fp={data.fund_programme} showCapacity={data.settings.show_capacity} />
        : <Kpis s={data.summary} showCapacity={data.settings.show_capacity} />}

      {!data.investments.length && fc.total > 0 && (
        <div className="card empty-state" style={{ minHeight: 140 }}>
          <div className="sec-title">Nothing matches</div>
          <p>No {f.view === 'funds' ? 'fund commitments' : f.view === 'direct' ? 'direct or co-investments' : 'investments'} match these filters.</p>
          <button className="pb" onClick={() => { setQText(''); setF({ ...NO_FILTERS }) }}>Show all investments</button>
        </div>
      )}
      {!fc.total && (
        <div className="card empty-state" style={{ minHeight: 200 }}>
          <div className="sec-title">No investments yet</div>
          <p style={{ maxWidth: 520 }}>Add your direct investments, SPVs, co-investments and fund commitments. Gross and net MOIC, IRR and DPI are calculated for each one and pooled across the book, and the Download PDF button turns it into a marketing sheet.</p>
          {data.can_edit && <button className="btn btn-primary" onClick={() => setAdding(true)}>+ Add investment</button>}
        </div>
      )}
      {!!directs.length && (
        <Card title={`Direct investments, SPVs and co-investments (${directs.length})`} right={<span className="note">{x2(data.summary_direct.gross_moic)} gross · {pct(data.summary_direct.gross_irr)} IRR</span>}>
          <DataTable rows={directs} cols={directCols()} rowKey={i => String(i.id)} onRowClick={i => go(`inv-${i.id}`)} initialSort={{ key: 'date', dir: -1 }} />
        </Card>
      )}
      {!!funds.length && (
        <Card title={`Fund commitments (${funds.length})`}
          right={f.view !== 'funds' ? <button className="pb" disabled={pdfBusy} onClick={() => void getPdf('funds')}>Download fund programme PDF</button> : undefined}>
          {f.view !== 'funds' && <FundProgrammeSummary fp={data.fund_programme} />}
          <DataTable rows={funds} cols={fundCols()} rowKey={i => String(i.id)} onRowClick={i => go(`inv-${i.id}`)} initialSort={{ key: 'vin', dir: -1 }} />
          {data.fund_programme.by_vintage.length > 1 && (
            <>
              <div className="card-title" style={{ marginTop: 6 }}>By vintage</div>
              <BucketTable rows={data.fund_programme.by_vintage} label="Vintage" k="vintage" />
            </>
          )}
          <p className="note" style={{ marginTop: 6 }}>Programme, vintage and strategy net IRRs are paid-in-weighted averages of fund net IRRs (GP-reported where entered). For funds without a reported IRR, add capital calls and distributions as dated cash flows for an accurate figure.</p>
          {data.fund_programme.by_strategy.length > 1 && (
            <>
              <div className="card-title" style={{ marginTop: 6 }}>By strategy</div>
              <BucketTable rows={data.fund_programme.by_strategy} label="Strategy" k="strategy" />
            </>
          )}
        </Card>
      )}
      <p className="note">Net figures marked GP are reported by the manager; EST are estimated after the stated fees and carry. IRR is n.m. for positions held under a year. Amounts in USD.</p>

      {adding && <InvestmentForm onClose={() => setAdding(false)} onSaved={async i => { setAdding(false); await qc.invalidateQueries({ queryKey: TR_KEY }); go(`inv-${i.id}`) }} />}
      {settingsOpen && <SettingsDialog settings={data.settings} onClose={() => setSettingsOpen(false)} />}
    </div>
  )
}

// ── Investment drawer ─────────────────────────────────────────────────────────
export function InvestmentDrawer({ id }: { id: string }) {
  const { data } = useTrackRecord()
  const qc = useQueryClient()
  const [editing, setEditing] = useState(false)
  const [confirmDel, setConfirmDel] = useState(false)
  const [view, setView] = useState<{ pros: Point[]; cons: Point[]; risks: Point[] } | null>(null)
  const inv = data?.investments.find(i => String(i.id) === id)
  const refresh = () => qc.invalidateQueries({ queryKey: TR_KEY })
  if (!data) return <Drawer title="Loading…"><div className="empty-state">Loading…</div></Drawer>
  if (!inv) return <Drawer title="Investment not found"><div className="err-box">This investment no longer exists.</div></Drawer>
  const m = inv.metrics
  const canEdit = data.can_edit

  return (
    <Drawer eyebrow={[inv.structure_label, inv.vehicle, inv.status_label].filter(Boolean).join(' · ')} title={inv.is_fund ? inv.vehicle || inv.name : inv.name}
      logo={inv.is_fund ? <GpLogo id={inv.manager_id} name={inv.manager_name || inv.name} size={44} /> : <CoLogo id={inv.company_id} name={inv.name} size={44} />}
      actions={canEdit ? <>
        <button className="btn" onClick={() => setEditing(true)}>Edit</button>
        {confirmDel
          ? <button className="btn" style={{ color: 'var(--red)', borderColor: 'var(--red)' }} onClick={async () => { await api.delete(`/track-record/investments/${inv.id}/`); await refresh(); closeDrawer() }}>Confirm delete</button>
          : <button className="btn" onClick={() => setConfirmDel(true)}>Delete</button>}
      </> : undefined}>
      {inv.description && <p className="prose">{inv.description}</p>}
      <div>
        {inv.company_id && <span className="tag gp" onClick={() => go(`co-${inv.company_id}`)}>Open company profile</span>}
        {inv.manager_id && <GpChips ids={[inv.manager_id]} />}
      </div>
      <div className="facts">
        <Fact k={inv.is_fund ? 'Called' : 'Invested'} big v={usdm(m.invested_usd_m)} />
        <Fact k={inv.is_fund ? 'NAV' : 'Current value'} big v={usdm(m.current_usd_m)} />
        <Fact k={inv.is_fund ? 'Distributed' : 'Realised'} v={usdm(m.realised_usd_m)} />
        <Fact k="Gross MOIC" big v={x2(m.gross_moic)} />
        <Fact k={inv.is_fund ? 'Net TVPI' : 'Net MOIC'} big v={<>{x2(m.net_moic)}{reported(inv)}</>} />
        <Fact k="Gross IRR" v={irr(inv, 'gross_irr')} />
        <Fact k="Net IRR" v={irr(inv, 'net_irr')} />
        <Fact k="DPI (net)" v={`${x2(m.dpi)} (${x2(m.net_dpi)})`} />
        <Fact k="Holding period" v={m.holding_years != null ? `${m.holding_years.toFixed(1)} yrs` : '—'} />
        {inv.is_fund ? <>
          <Fact k="Commitment" v={usdm(inv.commitment_usd_m)} />
          <Fact k="Unfunded" v={usdm(m.unfunded_usd_m)} />
          <Fact k="Vintage" v={inv.vintage ?? '—'} />
        </> : <>
          <Fact k="Entry valuation" v={money(inv.entry_valuation_usd_bn)} />
          <Fact k="Ownership" v={m.ownership_pct != null ? `${m.ownership_pct.toFixed(m.ownership_pct < 0.1 ? 4 : 2)}%` : '—'} />
          <Fact k="Round · date" v={`${inv.round || '—'} · ${inv.invest_date}`} />
        </>}
        <Fact k="Value basis · date" v={[inv.value_basis, inv.value_date].filter(Boolean).join(' · ') || '—'} />
        <Fact k="Fees · carry" v={`${inv.mgmt_fee_pct || 0}% · ${inv.carry_pct || 0}%`} />
        <Fact k="Available capacity" v={inv.capacity_usd_m ? usdm(inv.capacity_usd_m) : '—'} />
      </div>
      {m.implied_markup_x != null && (
        <div className="card" style={{ background: 'var(--surface2)' }}>
          <p className="prose">The company's latest tracked valuation is <b>{x2(m.implied_markup_x)}</b> your entry valuation, which implies about <b>{usdm(m.suggested_value_usd_m)}</b> for the initial cheque before dilution and preferences. Your recorded current value is {usdm(inv.current_value_usd_m)}.</p>
        </div>
      )}
      <div className="grid2">
        <Card title="Lead investors"><p className="prose">{inv.lead_investors.join(', ') || '—'}</p></Card>
        <Card title="Invested with"><p className="prose">{inv.co_investors.join(', ') || '—'}</p></Card>
      </div>
      {!!inv.cashflows.length && (
        <Card title="Cash flows">
          <table style={{ width: '100%', borderCollapse: 'collapse' }}>
            <thead><tr><th className="ns">Date</th><th className="ns n">Amount</th><th className="ns">Note</th></tr></thead>
            <tbody>
              <tr><td>{inv.invest_date}</td><td className="n neg">{usdm(-(inv.invested_usd_m ?? 0))}</td><td>Initial investment</td></tr>
              {inv.cashflows.map((c, i) => <tr key={i}><td>{c.date}</td><td className={`n ${(c.amount_usd_m ?? 0) < 0 ? 'neg' : 'pos'}`}>{usdm(c.amount_usd_m)}</td><td>{c.note}</td></tr>)}
            </tbody>
          </table>
        </Card>
      )}
      <Card title="Your view" right={canEdit && !view ? <button className="pb" onClick={() => setView({ pros: inv.pros, cons: inv.cons, risks: inv.risks })}>Edit pros, cons, risks</button> : undefined}>
        {inv.thesis && <p className="prose" style={{ marginBottom: 10 }}>{inv.thesis}</p>}
        {view ? (
          <>
            <div className="grid2" style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 240px), 1fr))' }}>
              <PointsEditor idPrefix="dv-pros" title="Pros" points={view.pros} onChange={p => setView({ ...view, pros: p })} />
              <PointsEditor idPrefix="dv-cons" title="Cons" points={view.cons} onChange={p => setView({ ...view, cons: p })} />
              <PointsEditor idPrefix="dv-risks" title="Risks" points={view.risks} onChange={p => setView({ ...view, risks: p })} />
            </div>
            <div style={{ display: 'flex', gap: 8, marginTop: 10 }}>
              <button className="btn btn-primary" onClick={async () => { await api.patch(`/track-record/investments/${inv.id}/`, view); await refresh(); setView(null) }}>Save</button>
              <button className="btn" onClick={() => setView(null)}>Cancel</button>
            </div>
          </>
        ) : (
          <div className="grid2" style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 220px), 1fr))' }}>
            <PointsView title="Pros" points={inv.pros} />
            <PointsView title="Cons" points={inv.cons} />
            <PointsView title="Risks" points={inv.risks} />
          </div>
        )}
      </Card>
      <Card title={`Comments (${inv.comments.length})`}>
        <CommentsLog comments={inv.comments} canEdit={canEdit}
          onAdd={async text => { await api.post(`/track-record/investments/${inv.id}/comments/`, { text }); await refresh() }}
          onDelete={async cid => { await api.delete(`/track-record/comments/${cid}/`); await refresh() }} />
      </Card>
      {inv.highlight && <Card title="Highlight on the marketing sheet"><p className="prose">{inv.highlight}</p></Card>}
      {editing && <InvestmentForm inv={inv} onClose={() => setEditing(false)} onSaved={async () => { setEditing(false); await refresh() }} />}
    </Drawer>
  )
}
