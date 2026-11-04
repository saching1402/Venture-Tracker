import { useEffect, useMemo, useState } from 'react'
import { PointsEditor } from '../components/Commentary'
import { api, errorText } from '../lib/api'
import { useData } from '../store/data'
import type { CashFlowRow, LpInvestment, Point, Structure } from '../types'

const STRUCTURES: [Structure, string][] = [
  ['direct', 'Direct (cap table)'], ['spv', 'SPV'], ['coinvest', 'Co-investment'],
  ['l1', 'L1 fund'], ['l2', 'L2 fund-of-funds'], ['secondary', 'Secondary'],
]
const STATUSES: [string, string][] = [['active', 'Active'], ['partial', 'Partially realised'], ['realised', 'Realised'], ['written_off', 'Written off']]

type F = {
  name: string; company_id: string; manager_id: string; structure: Structure; vehicle: string; round: string; vintage: string
  description: string; sector: string; hq: string; lead_investors: string; co_investors: string
  invest_date: string; commitment_usd_m: string; invested_usd_m: string; entry_valuation_usd_bn: string; ownership_pct: string
  current_value_usd_m: string; value_date: string; value_basis: string; realised_usd_m: string
  mgmt_fee_pct: string; carry_pct: string; net_moic_reported: string; net_irr_reported: string; dpi_reported: string
  capacity_usd_m: string; status: string; highlight: string; thesis: string; include_in_sheet: boolean
  pros: Point[]; cons: Point[]; risks: Point[]; cashflows: CashFlowRow[]
}

const s = (v: unknown) => (v === null || v === undefined ? '' : String(v))

function fromInv(i?: LpInvestment): F {
  return {
    name: i?.name ?? '', company_id: i?.company_id ?? '', manager_id: i?.manager_id ?? '', structure: i?.structure ?? 'direct',
    vehicle: i?.vehicle ?? '', round: i?.round ?? '', vintage: s(i?.vintage), description: i?.description ?? '', sector: i?.sector ?? '',
    hq: i?.hq ?? '', lead_investors: (i?.lead_investors ?? []).join(', '), co_investors: (i?.co_investors ?? []).join(', '),
    invest_date: i?.invest_date ?? '', commitment_usd_m: s(i?.commitment_usd_m), invested_usd_m: s(i?.invested_usd_m),
    entry_valuation_usd_bn: s(i?.entry_valuation_usd_bn), ownership_pct: s(i?.ownership_pct), current_value_usd_m: s(i?.current_value_usd_m),
    value_date: i?.value_date ?? '', value_basis: i?.value_basis ?? '', realised_usd_m: s(i?.realised_usd_m || ''),
    mgmt_fee_pct: s(i?.mgmt_fee_pct || ''), carry_pct: s(i?.carry_pct || ''), net_moic_reported: s(i?.net_moic_reported),
    net_irr_reported: s(i?.net_irr_reported), dpi_reported: s(i?.dpi_reported), capacity_usd_m: s(i?.capacity_usd_m),
    status: i?.status ?? 'active', highlight: i?.highlight ?? '', thesis: i?.thesis ?? '', include_in_sheet: i?.include_in_sheet ?? true,
    pros: i?.pros ?? [], cons: i?.cons ?? [], risks: i?.risks ?? [], cashflows: i?.cashflows ?? [],
  }
}

const n = (v: string): number | null => (v.trim() === '' || Number.isNaN(Number(v)) ? null : Number(v))
const list = (v: string) => v.split(',').map(x => x.trim()).filter(Boolean)

function Field({ id, label, children, hint }: { id: string; label: string; children: React.ReactNode; hint?: string }) {
  return (
    <div className="form-group" style={{ marginBottom: 12, minWidth: 0 }}>
      <label className="form-label" htmlFor={id}>{label}{hint && <span className="note" style={{ textTransform: 'none', fontWeight: 400 }}> {hint}</span>}</label>
      {children}
    </div>
  )
}

const grid = (cols: number): React.CSSProperties => ({ display: 'grid', gridTemplateColumns: `repeat(auto-fit, minmax(min(100%, ${cols}px), 1fr))`, gap: '0 12px' })

export default function InvestmentForm({ inv, onClose, onSaved }: { inv?: LpInvestment; onClose: () => void; onSaved: (i: LpInvestment) => void }) {
  const { companies, managers } = useData()
  const [f, setF] = useState<F>(() => fromInv(inv))
  const [err, setErr] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)
  const [prefillNote, setPrefillNote] = useState<string | null>(null)
  const set = <K extends keyof F>(k: K) => (v: F[K]) => setF(p => ({ ...p, [k]: v }))
  const isFund = f.structure === 'l1' || f.structure === 'l2'
  const byName = useMemo(() => new Map(companies.map(c => [c.name.toLowerCase(), c.id])), [companies])

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => { if (e.key === 'Escape') onClose() }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [onClose])

  async function linkCompany(name: string) {
    set('name')(name)
    const id = byName.get(name.trim().toLowerCase())
    if (!id) { set('company_id')(''); return }
    set('company_id')(id)
    try {
      const { data } = await api.get(`/track-record/prefill/?company=${encodeURIComponent(id)}`)
      setF(p => ({
        ...p,
        description: p.description || data.description || '', sector: p.sector || data.sector || '', hq: p.hq || data.hq || '',
        lead_investors: p.lead_investors || (data.lead_investors ?? []).join(', '),
        co_investors: p.co_investors || (data.co_investors ?? []).slice(0, 8).join(', '),
        round: p.round || data.last_round?.round || '',
        entry_valuation_usd_bn: p.entry_valuation_usd_bn || s(data.last_round?.post_money_usd_bn ?? ''),
      }))
      setPrefillNote(`Linked to ${data.name} in the tracker: description, sector and investors filled in. Check the round and entry valuation match the round you invested in.`)
    } catch { /* prefill is a convenience */ }
  }

  async function submit(e: React.FormEvent) {
    e.preventDefault()
    setBusy(true); setErr(null)
    const body = {
      name: f.name.trim() || (isFund ? f.vehicle.trim() : ''), company_id: f.company_id || null, manager_id: f.manager_id || null,
      structure: f.structure, vehicle: f.vehicle, round: f.round, vintage: n(f.vintage), description: f.description, sector: f.sector, hq: f.hq,
      lead_investors: list(f.lead_investors), co_investors: list(f.co_investors), invest_date: f.invest_date,
      commitment_usd_m: n(f.commitment_usd_m), invested_usd_m: n(f.invested_usd_m), entry_valuation_usd_bn: n(f.entry_valuation_usd_bn),
      ownership_pct: n(f.ownership_pct), current_value_usd_m: n(f.current_value_usd_m), value_date: f.value_date || null,
      value_basis: f.value_basis, realised_usd_m: n(f.realised_usd_m) ?? 0, mgmt_fee_pct: n(f.mgmt_fee_pct) ?? 0, carry_pct: n(f.carry_pct) ?? 0,
      net_moic_reported: n(f.net_moic_reported), net_irr_reported: n(f.net_irr_reported), dpi_reported: n(f.dpi_reported),
      capacity_usd_m: n(f.capacity_usd_m), status: f.status, highlight: f.highlight, thesis: f.thesis, include_in_sheet: f.include_in_sheet,
      pros: f.pros, cons: f.cons, risks: f.risks,
      cashflows: f.cashflows.filter(c => c.date && c.amount_usd_m !== null).map(c => ({ ...c, amount_usd_m: Number(c.amount_usd_m) })),
    }
    if (!body.name) { setErr('Enter a name (or the fund name for a fund commitment).'); setBusy(false); return }
    if (!body.invest_date || body.invested_usd_m === null) { setErr('Enter the investment date and the amount invested.'); setBusy(false); return }
    try {
      const { data } = inv ? await api.put<LpInvestment>(`/track-record/investments/${inv.id}/`, body)
        : await api.post<LpInvestment>('/track-record/investments/', body)
      onSaved(data)
    } catch (e2) {
      const d = (e2 as { response?: { data?: Record<string, string[] | string> } }).response?.data
      setErr(d && typeof d === 'object' && !('detail' in d) ? Object.entries(d).map(([k, v]) => `${k.replace(/_/g, ' ')}: ${Array.isArray(v) ? v.join(' ') : v}`).join(' · ') : errorText(e2))
    }
    setBusy(false)
  }

  const flows = f.cashflows
  return (
    <div className="modal-overlay" onClick={onClose}>
      <form className="modal-panel" style={{ maxWidth: 900 }} onClick={e => e.stopPropagation()} onSubmit={submit}>
        <div className="modal-header">
          <div className="modal-title">{inv ? `Edit ${inv.name}` : 'Add an investment'}</div>
          <button type="button" className="btn" onClick={onClose}>Cancel</button>
        </div>
        <div className="modal-body">
          <div className="card-title">Investment</div>
          <div style={grid(200)}>
            <Field id="tr-structure" label="Structure">
              <select id="tr-structure" className="form-select" style={{ width: '100%' }} value={f.structure} onChange={e => set('structure')(e.target.value as Structure)}>
                {STRUCTURES.map(([v, l]) => <option key={v} value={v}>{l}</option>)}
              </select>
            </Field>
            {isFund ? (
              <>
                <Field id="tr-manager" label="GP / manager">
                  <select id="tr-manager" className="form-select" style={{ width: '100%' }} value={f.manager_id} onChange={e => set('manager_id')(e.target.value)}>
                    <option value="">Not in the tracker</option>
                    {managers.filter(m => !m.is_stub).sort((a, b) => a.name.localeCompare(b.name)).map(m => <option key={m.id} value={m.id}>{m.name}</option>)}
                  </select>
                </Field>
                <Field id="tr-vehicle" label="Fund name"><input id="tr-vehicle" className="form-input" style={{ width: '100%' }} value={f.vehicle} onChange={e => set('vehicle')(e.target.value)} placeholder="e.g. Lux Ventures VIII" /></Field>
                <Field id="tr-vintage" label="Vintage"><input id="tr-vintage" type="number" className="form-input" style={{ width: '100%' }} value={f.vintage} onChange={e => set('vintage')(e.target.value)} /></Field>
              </>
            ) : (
              <>
                <Field id="tr-name" label="Company" hint="pick a tracked company to fill details">
                  <input id="tr-name" list="tr-companies" className="form-input" style={{ width: '100%' }} value={f.name} onChange={e => void linkCompany(e.target.value)} placeholder="Start typing…" />
                  <datalist id="tr-companies">{companies.slice(0, 1500).map(c => <option key={c.id} value={c.name} />)}</datalist>
                </Field>
                <Field id="tr-vehicle" label="Vehicle" hint="SPV / co-invest vehicle"><input id="tr-vehicle" className="form-input" style={{ width: '100%' }} value={f.vehicle} onChange={e => set('vehicle')(e.target.value)} /></Field>
                <Field id="tr-round" label="Round"><input id="tr-round" className="form-input" style={{ width: '100%' }} value={f.round} onChange={e => set('round')(e.target.value)} placeholder="e.g. Series C" /></Field>
              </>
            )}
          </div>
          {isFund && <Field id="tr-name" label="Name shown in the list"><input id="tr-name" className="form-input" style={{ width: '100%' }} value={f.name} onChange={e => set('name')(e.target.value)} placeholder="Defaults to the fund name" /></Field>}
          {prefillNote && <p className="note" style={{ marginTop: -4, marginBottom: 10 }}>{prefillNote}</p>}
          <div style={grid(200)}>
            <Field id="tr-sector" label="Sector"><input id="tr-sector" className="form-input" style={{ width: '100%' }} value={f.sector} onChange={e => set('sector')(e.target.value)} /></Field>
            <Field id="tr-lead" label="Lead investor(s)" hint="comma-separated"><input id="tr-lead" className="form-input" style={{ width: '100%' }} value={f.lead_investors} onChange={e => set('lead_investors')(e.target.value)} /></Field>
            <Field id="tr-co" label="Invested with" hint="comma-separated"><input id="tr-co" className="form-input" style={{ width: '100%' }} value={f.co_investors} onChange={e => set('co_investors')(e.target.value)} /></Field>
          </div>
          <Field id="tr-desc" label="Description"><textarea id="tr-desc" className="form-textarea" rows={2} style={{ width: '100%' }} value={f.description} onChange={e => set('description')(e.target.value)} /></Field>

          <div className="card-title" style={{ marginTop: 6 }}>Economics <span className="note" style={{ textTransform: 'none' }}>amounts in USD millions; valuations in USD billions</span></div>
          <div style={grid(160)}>
            <Field id="tr-date" label="Investment date"><input id="tr-date" type="date" className="form-input" style={{ width: '100%' }} value={f.invest_date} onChange={e => set('invest_date')(e.target.value)} /></Field>
            {isFund && <Field id="tr-commit" label="Commitment $m"><input id="tr-commit" type="number" step="any" className="form-input" style={{ width: '100%' }} value={f.commitment_usd_m} onChange={e => set('commitment_usd_m')(e.target.value)} /></Field>}
            <Field id="tr-inv" label={isFund ? 'Called to date $m' : 'Invested $m'}><input id="tr-inv" type="number" step="any" className="form-input" style={{ width: '100%' }} value={f.invested_usd_m} onChange={e => set('invested_usd_m')(e.target.value)} /></Field>
            {!isFund && <Field id="tr-entry" label="Entry valuation $bn" hint="post-money"><input id="tr-entry" type="number" step="any" className="form-input" style={{ width: '100%' }} value={f.entry_valuation_usd_bn} onChange={e => set('entry_valuation_usd_bn')(e.target.value)} /></Field>}
            {!isFund && <Field id="tr-own" label="Ownership %" hint="blank = derived"><input id="tr-own" type="number" step="any" className="form-input" style={{ width: '100%' }} value={f.ownership_pct} onChange={e => set('ownership_pct')(e.target.value)} /></Field>}
            <Field id="tr-cur" label={isFund ? 'NAV $m' : 'Current value $m'}><input id="tr-cur" type="number" step="any" className="form-input" style={{ width: '100%' }} value={f.current_value_usd_m} onChange={e => set('current_value_usd_m')(e.target.value)} /></Field>
            <Field id="tr-vdate" label="Value date"><input id="tr-vdate" type="date" className="form-input" style={{ width: '100%' }} value={f.value_date} onChange={e => set('value_date')(e.target.value)} /></Field>
            <Field id="tr-basis" label="Value basis"><input id="tr-basis" className="form-input" style={{ width: '100%' }} value={f.value_basis} onChange={e => set('value_basis')(e.target.value)} placeholder={isFund ? 'GP NAV Q2-26' : 'Last round'} /></Field>
            <Field id="tr-real" label={isFund ? 'Distributed $m' : 'Realised $m'}><input id="tr-real" type="number" step="any" className="form-input" style={{ width: '100%' }} value={f.realised_usd_m} onChange={e => set('realised_usd_m')(e.target.value)} /></Field>
            <Field id="tr-fee" label="Mgmt fee % p.a."><input id="tr-fee" type="number" step="any" className="form-input" style={{ width: '100%' }} value={f.mgmt_fee_pct} onChange={e => set('mgmt_fee_pct')(e.target.value)} /></Field>
            <Field id="tr-carry" label="Carry %"><input id="tr-carry" type="number" step="any" className="form-input" style={{ width: '100%' }} value={f.carry_pct} onChange={e => set('carry_pct')(e.target.value)} /></Field>
          </div>
          <div style={grid(160)}>
            <Field id="tr-nmoic" label={isFund ? 'Net TVPI (GP)' : 'Net MOIC reported'} hint="optional"><input id="tr-nmoic" type="number" step="any" className="form-input" style={{ width: '100%' }} value={f.net_moic_reported} onChange={e => set('net_moic_reported')(e.target.value)} /></Field>
            <Field id="tr-nirr" label="Net IRR % reported" hint="optional"><input id="tr-nirr" type="number" step="any" className="form-input" style={{ width: '100%' }} value={f.net_irr_reported} onChange={e => set('net_irr_reported')(e.target.value)} /></Field>
            <Field id="tr-ndpi" label="Net DPI reported" hint="optional"><input id="tr-ndpi" type="number" step="any" className="form-input" style={{ width: '100%' }} value={f.dpi_reported} onChange={e => set('dpi_reported')(e.target.value)} /></Field>
            <Field id="tr-cap" label="Available capacity $m" hint="for co-investors"><input id="tr-cap" type="number" step="any" className="form-input" style={{ width: '100%' }} value={f.capacity_usd_m} onChange={e => set('capacity_usd_m')(e.target.value)} /></Field>
            <Field id="tr-status" label="Status">
              <select id="tr-status" className="form-select" style={{ width: '100%' }} value={f.status} onChange={e => set('status')(e.target.value)}>
                {STATUSES.map(([v, l]) => <option key={v} value={v}>{l}</option>)}
              </select>
            </Field>
          </div>

          <div className="card-title" style={{ marginTop: 6 }}>Follow-ons and distributions <span className="note" style={{ textTransform: 'none' }}>negative = money in, positive = money back; used for IRR</span></div>
          {flows.map((c, i) => (
            <div key={i} style={{ display: 'grid', gridTemplateColumns: '150px 130px 1fr auto', gap: 6, marginBottom: 5 }}>
              <input aria-label={`Cash flow ${i + 1} date`} type="date" className="form-input" value={c.date} onChange={e => set('cashflows')(flows.map((q, j) => (j === i ? { ...q, date: e.target.value } : q)))} />
              <input aria-label={`Cash flow ${i + 1} amount`} type="number" step="any" className="form-input" value={c.amount_usd_m ?? ''} placeholder="$m, e.g. -2.5"
                onChange={e => set('cashflows')(flows.map((q, j) => (j === i ? { ...q, amount_usd_m: e.target.value === '' ? null : Number(e.target.value) } : q)))} />
              <input aria-label={`Cash flow ${i + 1} note`} className="form-input" value={c.note} placeholder="Follow-on, tender, distribution…" onChange={e => set('cashflows')(flows.map((q, j) => (j === i ? { ...q, note: e.target.value } : q)))} />
              <button type="button" className="pb" onClick={() => set('cashflows')(flows.filter((_, j) => j !== i))} aria-label="Remove cash flow">✕</button>
            </div>
          ))}
          <button type="button" className="pb" style={{ marginBottom: 12 }} onClick={() => set('cashflows')([...flows, { date: '', amount_usd_m: null, note: '' }])}>+ Add cash flow</button>

          <div className="card-title" style={{ marginTop: 6 }}>Your view</div>
          <Field id="tr-thesis" label="Thesis / comments"><textarea id="tr-thesis" className="form-textarea" rows={3} style={{ width: '100%' }} value={f.thesis} onChange={e => set('thesis')(e.target.value)} /></Field>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 250px), 1fr))', gap: 14, marginBottom: 12 }}>
            <PointsEditor idPrefix="tr-pros" title="Pros" points={f.pros} onChange={set('pros')} />
            <PointsEditor idPrefix="tr-cons" title="Cons" points={f.cons} onChange={set('cons')} />
            <PointsEditor idPrefix="tr-risks" title="Risks" points={f.risks} onChange={set('risks')} />
          </div>

          <div className="card-title" style={{ marginTop: 6 }}>Marketing sheet</div>
          <Field id="tr-high" label="Highlight" hint="one or two lines printed on the PDF"><input id="tr-high" className="form-input" style={{ width: '100%' }} value={f.highlight} onChange={e => set('highlight')(e.target.value)} /></Field>
          <label className="chk"><input id="tr-include" type="checkbox" checked={f.include_in_sheet} onChange={e => set('include_in_sheet')(e.target.checked)} /> Include on the marketing sheet</label>
          {err && <div className="err-box" style={{ marginTop: 12 }}>{err}</div>}
        </div>
        <div className="modal-footer">
          <button type="submit" className="btn btn-primary" disabled={busy}>{busy ? 'Saving…' : inv ? 'Save changes' : 'Add investment'}</button>
        </div>
      </form>
    </div>
  )
}
