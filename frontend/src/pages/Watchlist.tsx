import DataTable from '../components/DataTable'
import { Card, Star } from '../components/ui'
import { clip, money } from '../lib/format'
import { go } from '../lib/route'
import { useData } from '../store/data'
import { companyCols } from './Companies'

export default function Watchlist() {
  const { managers, companies, watch } = useData()
  const fw = managers.filter(m => watch.managers.includes(m.id))
  const cw = companies.filter(c => watch.companies.includes(c.id))
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
      <div>
        <div className="sec-title">Your watchlist</div>
        <div className="sec-sub">Star any manager or company to pin it here. Your watchlist is saved to your account, so it follows you across devices and survives data refreshes.</div>
      </div>
      <Card title={`Managers (${fw.length})`}>
        {fw.length ? (
          <DataTable rows={fw} rowKey={m => m.id} onRowClick={m => go(`gp-${m.id}`)}
            cols={[
              { key: 'w', header: '', cell: m => <Star kind="manager" id={m.id} /> },
              { key: 'name', header: 'Manager', sort: m => m.name, cell: m => <span className="nm">{m.name}</span> },
              { key: 'aum', header: 'AUM', numeric: true, sort: m => m.aum_usd_bn, cell: m => money(m.aum_usd_bn) },
              { key: 'n', header: 'Cos.', numeric: true, sort: m => m.n_companies, cell: m => m.n_companies },
              { key: 'r', header: 'Recent activity', wrap: true, cell: m => clip(m.recent_activity, 180) },
            ]} />
        ) : <p className="note">No managers starred yet. Use ★ on the Managers tab.</p>}
      </Card>
      <Card title={`Companies (${cw.length})`}>
        {cw.length ? <DataTable rows={cw} rowKey={c => c.id} cols={companyCols()} onRowClick={c => go(`co-${c.id}`)} initialSort={{ key: 'val', dir: -1 }} />
          : <p className="note">No companies starred yet. Use ★ on the Companies tab.</p>}
      </Card>
    </div>
  )
}
