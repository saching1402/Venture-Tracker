import { useQuery, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { CommentsLog, PointsEditor, PointsView } from '../components/Commentary'
import DataTable, { type Col } from '../components/DataTable'
import Drawer from '../components/Drawer'
import { Card, Fact, GpChips, Kpi } from '../components/ui'
import { api, errorText } from '../lib/api'
import { money, pct, usdm, x2 } from '../lib/format'
import { closeDrawer, go } from '../lib/route'
import type { LpInvestment, Point, SheetSettings, TrackRecordData, TrSummary } from '../types'
import InvestmentForm from './InvestmentForm'

export const TR_KEY = ['track-record']

export function useTrackRecord() {
  return useQuery({ queryKey: TR_KEY, queryFn: () => api.get<TrackRecordData>('/track-record/investments/').then(r => r.data) })
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

function directCols(): Col<LpInvestment>[] {
  return [
    { key: 'name', header: 'Company', sort: i => i.name, wrap: true, cell: i => <><div className="nm">{i.name}{!i.include_in_sheet && <span className="tag" style={{ marginLeft: 6 }}>not on sheet</span>}</div><div className="sub">{i.sector}</div></> },
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
    { key: 'name', header: 'Fund / GP', sort: i => i.vehicle || i.name, wrap: true, cell: i => <><div className="nm">{i.vehicle || i.name}</div><div className="sub">{i.manager_name}</div></> },
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

async function downloadPdf(commentary: boolean) {
  const res = await api.get(`/track-record/pdf/?commentary=${commentary ? 1 : 0}`, { responseType: 'blob' })
  const url = URL.createObjectURL(res.data as Blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `track-record-${new Date().toISOString().slice(0, 10)}.pdf`
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
          {(['title', 'subtitle', 'prepared_by', 'contact'] as const).map(k => (
            <div className="form-group" key={k}>
              <label className="form-label" htmlFor={`ss-${k}`}>{k.replace('_', ' ')}</label>
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

export default function TrackRecord() {
  const { data, isLoading, error } = useTrackRecord()
  const qc = useQueryClient()
  const [adding, setAdding] = useState(false)
  const [settingsOpen, setSettingsOpen] = useState(false)
  const [commentary, setCommentary] = useState(false)
  const [pdfBusy, setPdfBusy] = useState(false)
  const [pdfErr, setPdfErr] = useState<string | null>(null)

  if (isLoading) return <div className="empty-state">Loading your track record…</div>
  if (error || !data) return <div className="err-box">{errorText(error)}</div>
  const directs = data.investments.filter(i => !i.is_fund)
  const funds = data.investments.filter(i => i.is_fund)

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
          <button className="btn btn-gold" disabled={pdfBusy || !data.investments.length}
            onClick={async () => { setPdfBusy(true); setPdfErr(null); try { await downloadPdf(commentary) } catch (e) { setPdfErr(errorText(e)) } setPdfBusy(false) }}>
            {pdfBusy ? 'Preparing PDF…' : 'Download PDF'}
          </button>
          {data.can_edit && <button className="btn" onClick={() => setSettingsOpen(true)}>Sheet settings</button>}
          {data.can_edit && <button className="btn btn-primary" onClick={() => setAdding(true)}>+ Add investment</button>}
        </div>
      </div>
      {pdfErr && <div className="err-box">{pdfErr}</div>}
      <Kpis s={data.summary} showCapacity={data.settings.show_capacity} />

      {!data.investments.length && (
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
        <Card title={`Fund commitments (${funds.length})`} right={<span className="note">{x2(data.summary_funds.net_moic)} net · {pct(data.summary_funds.net_irr)} net IRR</span>}>
          <DataTable rows={funds} cols={fundCols()} rowKey={i => String(i.id)} onRowClick={i => go(`inv-${i.id}`)} initialSort={{ key: 'vin', dir: -1 }} />
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
