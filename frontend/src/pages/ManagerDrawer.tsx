import { useQuery } from '@tanstack/react-query'
import DataTable from '../components/DataTable'
import Drawer from '../components/Drawer'
import { Card, Fact, Lbl, Sources, Star, StatusPill, Tags } from '../components/ui'
import { ReresearchButton, ResearchBadge } from '../components/Research'
import ManagerView from '../components/ManagerView'
import { api, errorText } from '../lib/api'
import { useData } from '../store/data'
import { money, xmult } from '../lib/format'
import { go } from '../lib/route'
import type { ManagerDetail } from '../types'
import { CoLogo, Logo, WithLogo } from '../components/Logo'

const SEC_COLORS = ['var(--navy)', 'var(--gold)', 'var(--navy3)', 'var(--gold2)', 'var(--blue)', 'var(--red)', '#7d8aa3', '#d9c08a']

function List({ items }: { items: string[] }) {
  return items.length ? <ul className="plain">{items.map(x => <li key={x}>{x}</li>)}</ul> : <p className="note">Not available.</p>
}

export default function ManagerDrawer({ id }: { id: string }) {
  const rs = useData(s => s.mgrById[id]?.research_status ?? '')
  const { data: f, error, isLoading } = useQuery({
    queryKey: ['manager', id, rs],
    refetchInterval: rs === 'queued' || rs === 'running' ? 8000 : false,
    queryFn: () => api.get<ManagerDetail>(`/managers/${encodeURIComponent(id)}/`).then(r => r.data),
  })
  if (isLoading) return <Drawer title="Loading…"><div className="empty-state">Loading manager…</div></Drawer>
  if (error || !f) return <Drawer title="Manager not found"><div className="err-box">{errorText(error)}</div></Drawer>

  const live = f.holdings.filter(h => !h.legacy && !h.valuation_stale)
  const agg = live.reduce((s, h) => s + (h.latest_valuation_usd_bn ?? 0), 0)
  const sec: Record<string, number> = {}
  f.holdings.forEach(h => { sec[h.sector || 'Other'] = (sec[h.sector || 'Other'] ?? 0) + 1 })
  const secs = Object.entries(sec).sort((a, b) => b[1] - a[1])

  return (
    <Drawer eyebrow={[f.type, f.founded ? `Founded ${f.founded}` : ''].filter(Boolean).join(' · ')} title={<>{f.name}<ResearchBadge status={f.research_status} /></>} link={f.website || undefined} logo={<Logo url={f.website} name={f.name} size={44} />}
      actions={<><ReresearchButton kind="manager" id={f.id} status={f.research_status} /><Star kind="manager" id={f.id} /></>}>
      {f.research_status && f.research_status !== 'failed' && <div className="card"><p className="prose">Researching this manager on the web. The profile fills in automatically; its portfolio companies follow one by one (see Research in the header).</p></div>}
      {f.research_status === 'failed' && <div className="err-box">Research did not finish. Open Research in the header to see why and retry.</div>}
      {f.is_stub && !f.research_status && <p className="note">This manager appears on tracked cap tables but has no profile yet; use Re-research or wait for the next refresh.</p>}
      <div className="facts">
        <Fact k="AUM" big v={<>{money(f.aum_usd_bn)}<Lbl l={f.aum_label} /></>} />
        <Fact k="HQ" v={f.hq || '—'} />
        <Fact k="Team" v={f.team_size || '—'} />
        <Fact k="Check size" v={f.check_size || '—'} />
        <Fact k="Tracked holdings" v={`${f.holdings.length} · ${money(agg)}`} />
        <Fact k="Other offices" v={f.other_offices.join(', ') || '—'} />
      </div>
      <ManagerView id={f.id} />
      <Card title="Overview">
        <p className="prose">{f.overview || '—'}</p>
        <div style={{ marginTop: 10 }}><Tags items={f.stages} /></div>
        <div style={{ marginTop: 4 }}><Tags items={f.focus_areas} cls="focus" /></div>
      </Card>
      <div className="grid2">
        <Card title="Recent funds">
          {f.recent_funds.length ? (
            <table style={{ width: '100%', borderCollapse: 'collapse' }}>
              <thead><tr><th className="ns">Fund</th><th className="ns n">Size</th><th className="ns n">Vintage</th></tr></thead>
              <tbody>{f.recent_funds.map(x => <tr key={`${x.name}-${x.vintage}`}><td style={{ whiteSpace: 'normal' }}>{x.name}<Lbl l={x.label} /></td><td className="n">{money(x.size_usd_bn)}</td><td className="n">{x.vintage ?? ''}</td></tr>)}</tbody>
            </table>
          ) : <p className="note">Not disclosed.</p>}
        </Card>
        <Card title={<>Performance <Lbl l={f.performance_label} /></>}><p className="prose">{f.performance || 'Not publicly disclosed.'}</p></Card>
      </div>
      <Card title="Key people">
        <div className="people">
          {f.key_people.map(p => <div key={p.name}><div className="nm">{p.name}</div><div className="sub">{p.title}</div>{p.focus && <div className="note" style={{ marginTop: 3 }}>{p.focus}</div>}</div>)}
        </div>
        {!f.key_people.length && <p className="note">Not available.</p>}
      </Card>
      <div className="grid2">
        <Card title="Best performers"><List items={f.best_performers} /></Card>
        <Card title="Notable exits"><List items={f.notable_exits} /></Card>
      </div>
      <div className="grid2">
        <Card title="Recent activity"><p className="prose">{f.recent_activity || '—'}</p></Card>
        <Card title="LP watch items"><p className="prose">{f.watch_items || '—'}</p></Card>
      </div>
      <Card title="Sector mix of tracked holdings">
        <div className="secbar">
          {secs.map(([s, n], i) => <div key={s} title={`${s}: ${n}`} style={{ width: `${(100 * n) / (f.holdings.length || 1)}%`, background: SEC_COLORS[i % SEC_COLORS.length] }} />)}
        </div>
        <div style={{ marginTop: 8 }}>{secs.map(([s, n]) => <span key={s} className="tag">{s} {n}</span>)}</div>
      </Card>
      <Card title={`Portfolio (${f.holdings.length})`}>
        <p className="sec-sub">Entry mark is the post-money of the round in the first investment year; markup is today's valuation over it. Gross company-level indicators only.</p>
        <DataTable rows={f.holdings} rowKey={h => h.company_id} onRowClick={h => go(`co-${h.company_id}`)} pageSize={300} initialSort={{ key: 'val', dir: -1 }}
          cols={[
            { key: 'name', header: 'Company', sort: h => h.name, cell: h => <WithLogo logo={<CoLogo id={h.company_id} name={h.name} size={24} />}><div className="nm">{h.name}</div><div className="sub">{h.sector}</div></WithLogo> },
            { key: 'st', header: 'Status', sort: h => h.status, cell: h => <StatusPill status={h.status} /> },
            { key: 'yr', header: 'Entry', numeric: true, sort: h => h.first_invest_year,
              cell: h => h.first_invest_year ? <>{h.first_invest_year}<div className="sub">{h.entry_round}{h.lead ? ' · lead' : ''}</div></> : <span className="sub">{h.via ? 'investor list' : '—'}</span> },
            { key: 'ep', header: 'Entry mark', numeric: true, sort: h => h.entry_post_usd_bn, cell: h => money(h.entry_post_usd_bn) },
            { key: 'val', header: 'Valuation', numeric: true, sort: h => (h.legacy ? null : h.latest_valuation_usd_bn),
              cell: h => <>{money(h.latest_valuation_usd_bn)}{(h.legacy || h.valuation_stale) && <div className="sub"><span className="stale">{h.legacy ? 'legacy' : 'stale'}</span></div>}</> },
            { key: 'mx', header: 'Markup', numeric: true, sort: h => h.markup_x, cell: h => h.markup_x ? <span className="pos">{xmult(h.markup_x)}</span> : '—' },
            { key: 'rev', header: 'ARR / Rev.', numeric: true, sort: h => h.revenue_usd_bn, cell: h => money(h.revenue_usd_bn) },
          ]} />
      </Card>
      <Sources list={f.sources} verified={f.last_verified} />
    </Drawer>
  )
}
