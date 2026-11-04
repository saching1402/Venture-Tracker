import { CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { money } from '../lib/format'
import type { Round } from '../types'

interface Pt { d: string; v: number; r: string }

/** Post-money by round on a log scale, with the latest mark appended. */
export default function ValuationChart({ rounds, latest, latestDate }: { rounds: Round[]; latest: number | null; latestDate: string }) {
  const pts: Pt[] = rounds.filter(r => r.post_money_usd_bn != null && r.post_money_usd_bn > 0)
    .map(r => ({ d: (r.date || '').slice(0, 7), v: r.post_money_usd_bn as number, r: r.round }))
  if (latest && latest > 0 && (!pts.length || (latestDate || '') > pts[pts.length - 1].d)) pts.push({ d: (latestDate || 'latest').slice(0, 7), v: latest, r: 'Latest mark' })
  if (pts.length < 2) return null
  const lo = Math.min(...pts.map(p => p.v)), hi = Math.max(...pts.map(p => p.v))
  const ticks: number[] = []
  for (let e = Math.floor(Math.log10(lo)); e <= Math.ceil(Math.log10(hi)); e++) ticks.push(10 ** e)
  return (
    <div style={{ width: '100%' }}>
      <div style={{ width: '100%', height: 230 }}>
      <ResponsiveContainer>
        <LineChart data={pts} margin={{ top: 10, right: 16, left: 4, bottom: 4 }}>
          <CartesianGrid stroke="var(--border)" vertical={false} />
          <XAxis dataKey="d" tick={{ fontSize: 10, fill: 'var(--muted)' }} tickLine={false} axisLine={{ stroke: 'var(--border2)' }} />
          <YAxis scale="log" domain={[ticks[0], ticks[ticks.length - 1]]} ticks={ticks} allowDataOverflow
            tickFormatter={v => money(v as number)} tick={{ fontSize: 10, fill: 'var(--muted)' }} tickLine={false} axisLine={false} width={56} />
          <Tooltip formatter={(v: number) => [money(v), 'Post-money']} labelFormatter={(l, p) => `${l} · ${p?.[0]?.payload?.r ?? ''}`}
            contentStyle={{ fontSize: 12, borderRadius: 8, border: '1px solid var(--border)', fontFamily: 'var(--f-body)' }} />
          <Line type="linear" dataKey="v" stroke="var(--navy)" strokeWidth={2} dot={{ r: 3, fill: '#fff', stroke: 'var(--navy)' }}
            activeDot={{ r: 5, fill: 'var(--gold)', stroke: 'var(--navy)' }} isAnimationActive={false} />
        </LineChart>
      </ResponsiveContainer>
      </div>
      <p className="note" style={{ marginTop: 4 }}>Log scale. Post-money by round.</p>
    </div>
  )
}
