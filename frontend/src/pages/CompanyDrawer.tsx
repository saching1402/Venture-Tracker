import { useQuery } from '@tanstack/react-query'
import Drawer from '../components/Drawer'
import { Card, Fact, Lbl, Sources, Star, StatusPill, Tags } from '../components/ui'
import ValuationChart from '../components/ValuationChart'
import { api, errorText } from '../lib/api'
import { money, shortName, xmult } from '../lib/format'
import { go } from '../lib/route'
import { useData } from '../store/data'
import type { CompanyDetail } from '../types'

export default function CompanyDrawer({ id }: { id: string }) {
  const managers = useData(s => s.managers)
  const { data: c, error, isLoading } = useQuery({
    queryKey: ['company', id],
    queryFn: () => api.get<CompanyDetail>(`/companies/${encodeURIComponent(id)}/`).then(r => r.data),
  })
  if (isLoading) return <Drawer title="Loading…"><div className="empty-state">Loading company…</div></Drawer>
  if (error || !c) return <Drawer title="Company not found"><div className="err-box">{errorText(error)}</div></Drawer>

  const named = managers.filter(m => !m.is_stub)
  const matchMgr = (inv: string) => named.find(m => inv.toLowerCase().includes(shortName(m.name).toLowerCase()))
  const positions = [...c.gp_positions].sort((a, b) => (a.first_invest_year ?? 9999) - (b.first_invest_year ?? 9999))

  return (
    <Drawer eyebrow={[c.sector, c.hq, c.founded ? `Founded ${c.founded}` : ''].filter(Boolean).join(' · ')} title={c.name}
      link={c.website || undefined} actions={<Star kind="company" id={c.id} />}>
      <p className="prose">{c.description}</p>
      <div><StatusPill status={c.status} /> <Tags items={c.focus_tags} cls="focus" /></div>
      <div className="facts">
        <Fact k="Latest valuation" big v={<>{money(c.latest_valuation_usd_bn)}<Lbl l={c.valuation_label} /></>} />
        <Fact k="Basis · as of" v={<>{[c.valuation_basis, c.valuation_date].filter(Boolean).join(' · ') || '—'}{(c.valuation_stale || c.legacy) && <> <span className="stale">{c.legacy ? 'legacy' : 'stale'}</span></>}</>} />
        <Fact k={c.revenue_metric || 'ARR / revenue'} big v={c.revenue_usd_bn != null ? <>{money(c.revenue_usd_bn)}<Lbl l={c.revenue_label} /></> : '—'} />
        <Fact k="Revenue date" v={c.revenue_date || '—'} />
        <Fact k="Valuation / revenue" v={xmult(c.ev_rev_x)} />
        <Fact k="Step-up since first mark" v={c.step_up_x && !c.legacy ? <>{xmult(c.step_up_x)} <span className="sub">from {money(c.first_mark_usd_bn)}</span></> : '—'} />
        <Fact k="Total raised" v={money(c.total_raised_usd_bn)} />
        <Fact k="Employees" v={c.employees ? c.employees.toLocaleString() : '—'} />
        <Fact k="CEO" v={c.ceo || '—'} />
        <Fact k="Tracked managers" v={c.gp_positions.length} />
      </div>
      {(c.growth || c.profitability) && (
        <div className="grid2">
          <Card title="Growth"><p className="prose">{c.growth || 'Not disclosed.'}</p></Card>
          <Card title="Profitability and margins"><p className="prose">{c.profitability || 'Not disclosed.'}</p></Card>
        </div>
      )}
      <Card title="Valuation evolution">
        <ValuationChart rounds={c.valuation_history} latest={c.latest_valuation_usd_bn} latestDate={c.valuation_date} />
        {c.valuation_history.length ? (
          <div className="tbl-wrap" style={{ marginTop: 10, marginBottom: 0 }}>
            <table>
              <thead><tr><th className="ns">Date</th><th className="ns">Round</th><th className="ns n">Post-money</th><th className="ns n">Step</th><th className="ns">Lead</th></tr></thead>
              <tbody>
                {c.valuation_history.map((v, i, a) => {
                  const prev = i ? a[i - 1].post_money_usd_bn : null
                  const st = prev && v.post_money_usd_bn ? v.post_money_usd_bn / prev : null
                  return (
                    <tr key={`${v.date}-${v.round}-${i}`}>
                      <td>{v.date}</td><td style={{ whiteSpace: 'normal' }}>{v.round}</td>
                      <td className="n">{money(v.post_money_usd_bn)}</td>
                      <td className={`n ${st ? (st >= 1 ? 'pos' : 'neg') : ''}`}>{st ? xmult(st) : ''}</td>
                      <td style={{ whiteSpace: 'normal' }}>{v.lead}</td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        ) : <p className="note">No round history verified yet.</p>}
      </Card>
      <Card title={`Tracked managers on the cap table (${positions.length})`}>
        <div className="tbl-wrap" style={{ marginBottom: 0 }}>
          <table>
            <thead><tr><th className="ns">Manager</th><th className="ns n">First in</th><th className="ns">Entry round</th><th className="ns n">Entry mark</th><th className="ns n">Markup</th><th className="ns">Fund</th></tr></thead>
            <tbody>
              {positions.map(p => (
                <tr key={p.firm_id} className="click" onClick={() => go(`gp-${p.firm_id}`)}>
                  <td className="nm">{p.firm_name}{p.lead && <span className="tag" style={{ marginLeft: 6 }}>lead</span>}</td>
                  <td className="n">{p.first_invest_year ?? '—'}</td>
                  <td style={{ whiteSpace: 'normal' }}>{p.entry_round || (p.via ? 'via investor list' : '—')}</td>
                  <td className="n">{money(p.entry_post_usd_bn)}</td>
                  <td className={`n ${p.markup_x ? 'pos' : ''}`}>{xmult(p.markup_x)}</td>
                  <td className="sub" style={{ whiteSpace: 'normal' }}>{p.fund}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>
      <Card title={`All notable investors (${c.other_investors.length})`}>
        {c.other_investors.map(o => {
          const m = matchMgr(o)
          return m ? <span key={o} className="tag gp" onClick={() => go(`gp-${m.id}`)}>{o}</span> : <span key={o} className="tag">{o}</span>
        })}
        {!c.other_investors.length && <span className="note">Not available.</span>}
      </Card>
      {c.notes && <Card title="Notes"><p className="prose">{c.notes}</p></Card>}
      <Sources list={c.sources} verified={c.last_verified} />
    </Drawer>
  )
}
