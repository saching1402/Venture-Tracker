import { useQuery } from '@tanstack/react-query'
import DataTable from '../components/DataTable'
import { GpChips } from '../components/ui'
import { api, errorText } from '../lib/api'
import { money } from '../lib/format'
import { go } from '../lib/route'
import { useData } from '../store/data'
import type { RecentRound } from '../types'
import { Logo, WithLogo } from '../components/Logo'

export default function Rounds() {
  const coById = useData(s => s.coById)
  const { data, isLoading, error } = useQuery({
    queryKey: ['rounds', '2025-07'],
    queryFn: () => api.get<RecentRound[]>('/companies/rounds/recent/?since=2025-07').then(r => r.data),
  })
  const rows = (data ?? []).filter(r => coById[r.company_id])
  return (
    <>
      <div className="sec-title">Priced rounds and tenders since July 2025</div>
      <div className="sec-sub">Every valuation event in the tracked companies' round histories, newest first. Click a row for the company file.</div>
      {error && <div className="err-box">{errorText(error)}</div>}
      {isLoading ? <div className="empty-state">Loading rounds…</div> : (
        <DataTable rows={rows} rowKey={r => `${r.company_id}-${r.date}-${r.round}`} onRowClick={r => go(`co-${r.company_id}`)}
          initialSort={{ key: 'date', dir: -1 }}
          cols={[
            { key: 'date', header: 'Date', sort: r => r.date, cell: r => r.date },
            { key: 'co', header: 'Company', sort: r => coById[r.company_id].name, cell: r => <WithLogo logo={<Logo url={coById[r.company_id].website} name={coById[r.company_id].name} size={24} />}><div className="nm">{coById[r.company_id].name}</div><div className="sub">{coById[r.company_id].sector}</div></WithLogo> },
            { key: 'round', header: 'Round', wrap: true, cell: r => r.round },
            { key: 'pm', header: 'Post-money', numeric: true, sort: r => r.post_money_usd_bn, cell: r => money(r.post_money_usd_bn) },
            { key: 'lead', header: 'Lead', wrap: true, cell: r => r.lead || '—' },
            { key: 'gps', header: 'Tracked managers on cap table', wrap: true, sort: r => coById[r.company_id].tracked_gp_ids.length, cell: r => <GpChips ids={coById[r.company_id].tracked_gp_ids} max={5} /> },
          ]} />
      )}
    </>
  )
}
