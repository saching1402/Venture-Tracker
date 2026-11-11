import { useQuery, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { api, errorText } from '../lib/api'
import { pct, usdm, x2 } from '../lib/format'
import { go } from '../lib/route'
import { useResearch } from '../store/research'
import type { Assessment, Point } from '../types'
import { CommentsLog, PointsEditor, PointsView } from './Commentary'
import { Card } from './ui'
import { GpLogo, WithLogo } from './Logo'

/** "Your view" on a GP: overall view, pros / cons / risks, comment log, and your commitments to its funds. */
export default function ManagerView({ id }: { id: string }) {
  const qc = useQueryClient()
  const canEdit = useResearch(s => s.can_research)
  const key = ['assessment', id]
  const { data, error } = useQuery({ queryKey: key, queryFn: () => api.get<Assessment>(`/track-record/managers/${encodeURIComponent(id)}/assessment/`).then(r => r.data) })
  const [edit, setEdit] = useState<{ view: string; pros: Point[]; cons: Point[]; risks: Point[] } | null>(null)
  const [err, setErr] = useState<string | null>(null)
  if (error) return <div className="err-box">{errorText(error)}</div>
  if (!data) return null
  const empty = !data.view && !data.pros.length && !data.cons.length && !data.risks.length

  async function save() {
    try {
      const { data: d } = await api.put<Assessment>(`/track-record/managers/${encodeURIComponent(id)}/assessment/`, edit)
      qc.setQueryData(key, d); setEdit(null); setErr(null)
    } catch (e) { setErr(errorText(e)) }
  }

  return (
    <div className="card" style={{ borderTop: '2px solid var(--gold)' }}>
      <div style={{ display: 'flex', alignItems: 'baseline', gap: 8, marginBottom: 8 }}>
        <div className="card-title" style={{ margin: 0 }}>Your view</div>
        {data.updated_at && <span className="note">updated {new Date(data.updated_at).toLocaleDateString('en-GB')} by {data.updated_by}</span>}
        {canEdit && !edit && <button className="pb" style={{ marginLeft: 'auto' }} onClick={() => setEdit({ view: data.view, pros: data.pros, cons: data.cons, risks: data.risks })}>{empty ? 'Add your view' : 'Edit'}</button>}
      </div>
      {edit ? (
        <>
          <textarea aria-label="Overall view" className="form-textarea" rows={3} style={{ width: '100%', marginBottom: 10 }} placeholder="Overall view on the manager: why you back them, how they fit the programme…"
            value={edit.view} onChange={e => setEdit({ ...edit, view: e.target.value })} />
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 240px), 1fr))', gap: 14 }}>
            <PointsEditor idPrefix="mv-pros" title="Pros" points={edit.pros} onChange={p => setEdit({ ...edit, pros: p })} />
            <PointsEditor idPrefix="mv-cons" title="Cons" points={edit.cons} onChange={p => setEdit({ ...edit, cons: p })} />
            <PointsEditor idPrefix="mv-risks" title="Risks" points={edit.risks} onChange={p => setEdit({ ...edit, risks: p })} />
          </div>
          {err && <div className="err-box" style={{ marginTop: 8 }}>{err}</div>}
          <div style={{ display: 'flex', gap: 8, marginTop: 10 }}>
            <button className="btn btn-primary" onClick={() => void save()}>Save</button>
            <button className="btn" onClick={() => setEdit(null)}>Cancel</button>
          </div>
        </>
      ) : empty ? (
        <p className="note">No view recorded yet.{canEdit ? ' Add your pros, cons and risks on this manager.' : ''}</p>
      ) : (
        <>
          {data.view && <p className="prose" style={{ marginBottom: 10 }}>{data.view}</p>}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 220px), 1fr))', gap: 14 }}>
            <PointsView title="Pros" points={data.pros} />
            <PointsView title="Cons" points={data.cons} />
            <PointsView title="Risks" points={data.risks} />
          </div>
        </>
      )}
      {!!data.commitments.length && (
        <div style={{ marginTop: 12 }}>
          <div className="card-title">Your commitments to this manager</div>
          <table style={{ width: '100%', borderCollapse: 'collapse' }}>
            <thead><tr><th className="ns">Fund</th><th className="ns n">Commitment</th><th className="ns n">Called</th><th className="ns n">NAV</th><th className="ns n">Net TVPI</th><th className="ns n">Net IRR</th></tr></thead>
            <tbody>{data.commitments.map(c => (
              <tr key={c.id} className="click" onClick={() => go(`inv-${c.id}`)}>
                <td className="nm"><WithLogo logo={<GpLogo id={c.manager_id} name={c.manager_name || c.name} size={20} />}>{c.vehicle || c.name}</WithLogo></td><td className="n">{usdm(c.commitment_usd_m)}</td><td className="n">{usdm(c.metrics.invested_usd_m)}</td>
                <td className="n">{usdm(c.metrics.current_usd_m)}</td><td className="n">{x2(c.metrics.net_moic)}</td><td className="n">{c.metrics.irr_nm ? 'n.m.' : pct(c.metrics.net_irr)}</td>
              </tr>))}</tbody>
          </table>
        </div>
      )}
      <div style={{ marginTop: 12 }}>
        <Card title={`Comments (${data.comments.length})`}>
          <CommentsLog comments={data.comments} canEdit={canEdit}
            onAdd={async text => { const { data: d } = await api.post<Assessment>(`/track-record/managers/${encodeURIComponent(id)}/comments/`, { text }); qc.setQueryData(key, d) }}
            onDelete={async cid => { await api.delete(`/track-record/manager-comments/${cid}/`); await qc.invalidateQueries({ queryKey: key }) }} />
        </Card>
      </div>
    </div>
  )
}
