import { useEffect, useState } from 'react'
import { go } from '../lib/route'
import { useResearch } from '../store/research'
import type { ResearchModel, ResearchStatus } from '../types'

const usd = (v: number) => (v < 1 ? `$${v.toFixed(2)}` : `$${v.toFixed(v < 10 ? 1 : 0)}`)
const modelLabel = (models: ResearchModel[], id: string) => models.find(m => m.id === id)?.label.split(' · ')[0] ?? id

export function ResearchBadge({ status }: { status: ResearchStatus }) {
  if (!status) return null
  const label = { queued: 'Queued', running: 'Researching', failed: 'Research failed' }[status]
  return <span className={`rs rs-${status}`}>{label}</span>
}

/** "+ Add manager" / "+ Add company" button with its dialog. */
export function AddButton({ kind }: { kind: 'manager' | 'company' }) {
  const { enabled, can_research } = useResearch()
  const [open, setOpen] = useState(false)
  if (!can_research) return null
  return (
    <>
      <button className="btn btn-gold" onClick={() => setOpen(true)}
        title={enabled ? undefined : 'Auto-research needs ANTHROPIC_API_KEY on the server'}>
        + Add {kind}
      </button>
      {open && <AddDialog kind={kind} onClose={() => setOpen(false)} />}
    </>
  )
}

function AddDialog({ kind, onClose }: { kind: 'manager' | 'company'; onClose: () => void }) {
  const { add, enabled, models, defaults, max_portfolio } = useResearch()
  const [name, setName] = useState('')
  const [website, setWebsite] = useState('')
  const [portfolio, setPortfolio] = useState(true)
  const [model, setModel] = useState(kind === 'manager' ? defaults.manager : defaults.company)
  const [pModel, setPModel] = useState(defaults.portfolio)
  const [limit, setLimit] = useState(max_portfolio)
  const est = (id: string, k: 'manager' | 'company') => models.find(m => m.id === id)?.[k === 'manager' ? 'est_manager' : 'est_company'] ?? 0
  const total = kind === 'manager' ? est(model, 'manager') + (portfolio ? limit * est(pModel, 'company') : 0) : est(model, 'company')
  const [busy, setBusy] = useState(false)
  const [err, setErr] = useState<{ text: string; id?: string } | null>(null)

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => { if (e.key === 'Escape') onClose() }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [onClose])

  async function submit(e: React.FormEvent) {
    e.preventDefault()
    if (!name.trim() || busy) return
    setBusy(true)
    const r = await add(kind, name.trim(), website.trim(),
      kind === 'manager' ? { model, portfolio_model: pModel, portfolio_limit: limit, include_portfolio: portfolio } : { model })
    setBusy(false)
    if (r.ok) { onClose(); go(`${kind === 'manager' ? 'gp' : 'co'}-${r.id}`); return }
    setErr({ text: r.message ?? 'Could not add.', id: r.exists ? r.id : undefined })
  }

  const what = kind === 'manager' ? 'manager' : 'company'
  return (
    <div className="modal-overlay" onClick={onClose}>
      <form className="modal-panel" onClick={e => e.stopPropagation()} onSubmit={submit}>
        <div className="modal-header">
          <div className="modal-title">Add a {what}</div>
          <button type="button" className="btn" onClick={onClose}>Cancel</button>
        </div>
        <div className="modal-body">
          {!enabled && <div className="err-box" style={{ marginBottom: 14 }}>Auto-research is off on the server. An admin needs to add ANTHROPIC_API_KEY to the Railway variables.</div>}
          <div className="form-group">
            <label className="form-label" htmlFor="add-name">{kind === 'manager' ? 'Manager name' : 'Company name'}</label>
            <input id="add-name" className="form-input" style={{ width: '100%' }} autoFocus value={name} onChange={e => { setName(e.target.value); setErr(null) }}
              placeholder={kind === 'manager' ? 'e.g. Obvious Ventures' : 'e.g. Physical Intelligence'} />
          </div>
          <div className="form-group">
            <label className="form-label" htmlFor="add-web">Website <span className="note" style={{ textTransform: 'none' }}>(optional, helps tell similar names apart)</span></label>
            <input id="add-web" className="form-input" style={{ width: '100%' }} value={website} onChange={e => setWebsite(e.target.value)} placeholder="https://" />
          </div>
          <div className="form-group">
            <label className="form-label" htmlFor="add-model">{kind === 'manager' ? 'Model for the manager profile' : 'Research model'}</label>
            <select id="add-model" className="form-select" style={{ width: '100%' }} value={model} onChange={e => setModel(e.target.value)}>
              {models.map(m => <option key={m.id} value={m.id}>{m.label} (~{usd(kind === 'manager' ? m.est_manager : m.est_company)})</option>)}
            </select>
          </div>
          {kind === 'manager' && (
            <>
              <label className="chk" style={{ alignItems: 'flex-start', marginBottom: 12 }}>
                <input id="add-portfolio" type="checkbox" checked={portfolio} onChange={e => setPortfolio(e.target.checked)} style={{ marginTop: 2 }} />
                <span>Also research its portfolio companies. Companies already tracked are linked straight away; new ones are researched one by one.</span>
              </label>
              {portfolio && (
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 120px', gap: 10 }}>
                  <div className="form-group" style={{ marginBottom: 0 }}>
                    <label className="form-label" htmlFor="add-pmodel">Model for portfolio companies</label>
                    <select id="add-pmodel" className="form-select" style={{ width: '100%' }} value={pModel} onChange={e => setPModel(e.target.value)}>
                      {models.map(m => <option key={m.id} value={m.id}>{m.label} (~{usd(m.est_company)} each)</option>)}
                    </select>
                  </div>
                  <div className="form-group" style={{ marginBottom: 0 }}>
                    <label className="form-label" htmlFor="add-limit">New companies</label>
                    <input id="add-limit" type="number" min={1} max={60} className="form-input" style={{ width: '100%' }} value={limit}
                      onChange={e => setLimit(Math.max(1, Math.min(60, Number(e.target.value) || 1)))} />
                  </div>
                </div>
              )}
            </>
          )}
          <div className="card" style={{ marginTop: 14, background: 'var(--surface2)', display: 'flex', alignItems: 'baseline', gap: 10 }}>
            <span className="card-title" style={{ margin: 0 }}>Estimated cost</span>
            <span className="kpi-val" style={{ fontSize: 20 }}>~{usd(total)}</span>
            <span className="note">{kind === 'manager' && portfolio ? `profile + up to ${limit} new companies; tracked ones are linked free` : 'one research run'}</span>
          </div>
          <p className="note" style={{ marginTop: 14 }}>
            The {what} appears in the list right away. Research runs in the background with web search and fills the same fields as the rest of the tracker,
            usually in {kind === 'manager' ? (portfolio ? '5–20 minutes including portfolio companies' : '2–4 minutes') : '1–3 minutes'}.
          </p>
          {err && (
            <div className="err-box" style={{ marginTop: 12 }}>
              {err.text}{' '}
              {err.id && <button type="button" className="pb" onClick={() => { onClose(); go(`${kind === 'manager' ? 'gp' : 'co'}-${err.id}`) }}>Open it</button>}
            </div>
          )}
        </div>
        <div className="modal-footer">
          <button type="submit" className="btn btn-primary" disabled={!name.trim() || busy || !enabled}>{busy ? 'Adding…' : `Add and research`}</button>
        </div>
      </form>
    </div>
  )
}

/** Header button + dropdown listing recent research jobs. */
export function ResearchTray() {
  const { jobs, active, trayOpen, setTray, retry, refresh, loaded, can_research } = useResearch()
  useEffect(() => { void refresh() }, [refresh])
  if (!loaded || (!can_research && !jobs.length)) return null
  return (
    <>
      <button className="hdr-btn" onClick={() => setTray(!trayOpen)} aria-expanded={trayOpen}>
        {active > 0 && <span className="dot" />}Research{active > 0 ? ` · ${active} running` : ''}
      </button>
      {trayOpen && (
        <div className="tray" role="dialog" aria-label="Research activity">
          <div className="tray-hd"><b>Research activity</b><button className="pb" style={{ marginLeft: 'auto' }} onClick={() => setTray(false)}>Close</button></div>
          {!jobs.length && <div className="job note">Nothing researched yet. Use “+ Add manager” or “+ Add company”.</div>}
          {jobs.map(j => {
            const kids = j.children_total
            const pct = kids ? Math.round((100 * (j.children_done + j.children_failed)) / kids) : 0
            return (
              <div key={j.id} className="job">
                <div className="top">
                  <span className="nm" onClick={() => { setTray(false); go(`${j.kind === 'manager' ? 'gp' : j.kind === 'shortlist' ? 'sl' : j.kind === 'theme' ? 'th' : 'co'}-${j.slug}`) }}>{j.name}</span>
                  <span className="badge badge-gray">{j.kind}</span>
                  <span className={`badge ${j.status === 'done' ? 'badge-green' : j.status === 'failed' ? 'badge-red' : 'badge-gold'}`} style={{ marginLeft: 'auto' }}>{j.status}</span>
                </div>
                {kids > 0 && (
                  <>
                    <div className="sub">Portfolio: {j.children_done} of {kids} companies researched{j.children_failed ? `, ${j.children_failed} failed` : ''}</div>
                    <div className="bar"><div style={{ width: `${pct}%` }} /></div>
                  </>
                )}
                {j.summary && <div className="sub">{j.summary}</div>}
                {j.error && <div className="sub" style={{ color: 'var(--red)' }}>{j.error}</div>}
                <div className="sub">{new Date(j.created_at).toLocaleString()} · {modelLabel(useResearch.getState().models, j.model)}{j.children_total ? ` + ${modelLabel(useResearch.getState().models, j.portfolio_model)} for portfolio` : ''} · {j.searches} searches · {usd(j.cost_usd)}{j.children_total ? ' incl. portfolio' : ''}</div>
                {(j.status === 'failed' || j.children_failed > 0) && can_research && (
                  <div><button className="pb" onClick={() => void retry(j.id)}>Retry failed</button></div>
                )}
              </div>
            )
          })}
        </div>
      )}
    </>
  )
}

export function ReresearchButton({ kind, id, status }: { kind: 'manager' | 'company'; id: string; status?: ResearchStatus }) {
  const { can_research, enabled, reresearch, models, defaults } = useResearch()
  const [msg, setMsg] = useState<string | null>(null)
  const [model, setModel] = useState(kind === 'manager' ? defaults.manager : defaults.company)
  if (!can_research || !enabled) return null
  const busy = status === 'queued' || status === 'running'
  return (
    <>
      {!busy && (
        <select aria-label="Model for re-research" className="tbl-sel" value={model} onChange={e => setModel(e.target.value)}>
          {models.map(m => <option key={m.id} value={m.id}>{m.label.split(' · ')[0]}</option>)}
        </select>
      )}
      <button className="btn" disabled={busy} title="Run web research again and update this profile (its portfolio is not re-researched)"
        onClick={async () => { const r = await reresearch(kind, id, model); setMsg(r.ok ? 'Research started' : r.message ?? 'Failed') }}>
        {busy ? 'Researching…' : 'Re-research'}
      </button>
      {msg && <span className="note">{msg}</span>}
    </>
  )
}
