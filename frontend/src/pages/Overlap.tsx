import { useMemo } from 'react'
import DataTable from '../components/DataTable'
import { Card, GpChips } from '../components/ui'
import { money, shortName, uniq } from '../lib/format'
import { go } from '../lib/route'
import { useData } from '../store/data'
import { Logo, WithLogo } from '../components/Logo'

export default function Overlap() {
  const { companies, managers } = useData()
  const consensus = useMemo(() => companies.filter(c => !c.legacy && c.tracked_gp_ids.length >= 3), [companies])
  const real = useMemo(() => managers.filter(m => !m.is_stub).sort((a, b) => b.n_companies - a.n_companies), [managers])
  const tags = useMemo(() => uniq(companies.flatMap(c => c.focus_tags)), [companies])
  const { cnt, max } = useMemo(() => {
    const cnt: Record<string, Record<string, number>> = {}
    let max = 1
    for (const c of companies) for (const g of c.tracked_gp_ids) for (const t of c.focus_tags) {
      const row = (cnt[g] ??= {})
      row[t] = (row[t] ?? 0) + 1
      max = Math.max(max, row[t])
    }
    return { cnt, max }
  }, [companies])

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
      <Card title="Consensus names">
        <p className="sec-sub">Companies held by three or more tracked managers. Many co-holders mean crowded rounds and marks that move together across your fund commitments.</p>
        <DataTable rows={consensus} rowKey={c => c.id} onRowClick={c => go(`co-${c.id}`)} pageSize={60} initialSort={{ key: 'n', dir: -1 }}
          cols={[
            { key: 'name', header: 'Company', sort: c => c.name, cell: c => <WithLogo logo={<Logo url={c.website} name={c.name} size={24} />}><div className="nm">{c.name}</div><div className="sub">{c.sector}</div></WithLogo> },
            { key: 'val', header: 'Valuation', numeric: true, sort: c => c.latest_valuation_usd_bn, cell: c => money(c.latest_valuation_usd_bn) },
            { key: 'n', header: '# Managers', numeric: true, sort: c => c.tracked_gp_ids.length, cell: c => c.tracked_gp_ids.length },
            { key: 'g', header: 'Tracked co-holders', wrap: true, cell: c => <GpChips ids={c.tracked_gp_ids} max={14} /> },
          ]} />
      </Card>
      <Card title="Focus heatmap">
        <p className="sec-sub">Tracked holdings per manager by focus tag. Read across for a manager's revealed exposure, down for who owns a theme.</p>
        <div className="tbl-wrap heat">
          <table>
            <thead><tr><th className="ns">Manager</th>{tags.map(t => <th key={t} className="ns v">{t}</th>)}</tr></thead>
            <tbody>
              {real.map(m => (
                <tr key={m.id} className="click" onClick={() => go(`gp-${m.id}`)}>
                  <td className="nm"><WithLogo logo={<Logo url={m.website} name={m.name} size={18} />}>{shortName(m.name)}</WithLogo></td>
                  {tags.map(t => {
                    const v = cnt[m.id]?.[t] ?? 0
                    const share = v / max
                    return <td key={t} className="h" style={v ? { background: `color-mix(in srgb, var(--navy) ${Math.round(8 + 72 * share)}%, var(--surface))`, color: share > 0.45 ? '#fff' : 'var(--text)' } : undefined}>{v || ''}</td>
                  })}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>
    </div>
  )
}
