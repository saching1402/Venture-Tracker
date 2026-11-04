import { useQuery } from '@tanstack/react-query'
import DataTable from '../components/DataTable'
import { Card } from '../components/ui'
import { api, errorText } from '../lib/api'
import { go } from '../lib/route'
import { useData } from '../store/data'
import type { ChangeRow } from '../types'

export default function Changes() {
  const meta = useData(s => s.meta)
  const { data, error } = useQuery({ queryKey: ['changes'], queryFn: () => api.get<ChangeRow[]>('/changes/').then(r => r.data) })
  const rows = data ?? []
  return (
    <div className="grid2" style={{ alignItems: 'start' }}>
      <Card title="Refresh history">
        <p className="sec-sub">Each weekly refresh re-verifies valuations, ARR and cap tables, then records what moved.</p>
        <DataTable rows={meta?.refresh_log ?? []} rowKey={r => `${r.date}-${r.source}-${r.companies}`}
          cols={[
            { key: 'date', header: 'Date', sort: r => r.date, cell: r => r.date },
            { key: 'm', header: 'Managers', numeric: true, cell: r => r.managers },
            { key: 'c', header: 'Companies', numeric: true, cell: r => r.companies },
            { key: 'ch', header: 'Changes', numeric: true, cell: r => r.changes },
            { key: 's', header: 'Source', cell: r => r.source },
          ]} />
      </Card>
      <Card title="What moved">
        {error && <div className="err-box">{errorText(error)}</div>}
        <p className="sec-sub">{rows.length ? 'Valuation, revenue, status and cap-table changes detected between refreshes.'
          : 'This is the baseline snapshot. From the next refresh, every change in valuation, ARR, status or cap table is logged here with its date.'}</p>
        {!!rows.length && (
          <DataTable rows={rows} rowKey={r => `${r.date}-${r.company_name}-${r.type}-${r.detail}`}
            onRowClick={r => r.company_id && go(`co-${r.company_id}`)}
            cols={[
              { key: 'date', header: 'Date', sort: r => r.date, cell: r => r.date },
              { key: 'co', header: 'Company', sort: r => r.company_name, cell: r => <span className="nm">{r.company_name}</span> },
              { key: 'type', header: 'Type', sort: r => r.type, cell: r => <span className="badge badge-gray">{r.type.replace('_', ' ')}</span> },
              { key: 'd', header: 'Change', wrap: true, cell: r => <span className={r.from != null && r.to != null ? (r.to > r.from ? 'pos' : 'neg') : ''}>{r.detail}</span> },
            ]} />
        )}
      </Card>
    </div>
  )
}
