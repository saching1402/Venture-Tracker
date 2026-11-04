import { useState } from 'react'
import type { LpComment, Point, Severity } from '../types'

const SEVS: Severity[] = ['high', 'medium', 'low']
const SEV_CLS: Record<Severity, string> = { high: 'badge-red', medium: 'badge-gold', low: 'badge-gray' }

export function PointsView({ title, points }: { title: string; points: Point[] }) {
  return (
    <div>
      <div className="card-title">{title}</div>
      {points.length ? (
        <ul className="plain" style={{ listStyle: 'none', paddingLeft: 0 }}>
          {points.map((p, i) => <li key={i} style={{ marginBottom: 4 }}><span className={`badge ${SEV_CLS[p.severity]}`} style={{ marginRight: 6 }}>{p.severity}</span>{p.text}</li>)}
        </ul>
      ) : <p className="note">None noted.</p>}
    </div>
  )
}

export function PointsEditor({ title, points, onChange, idPrefix }: { title: string; points: Point[]; onChange: (p: Point[]) => void; idPrefix: string }) {
  const [draft, setDraft] = useState('')
  const [sev, setSev] = useState<Severity>('medium')
  const add = () => { if (draft.trim()) { onChange([...points, { text: draft.trim(), severity: sev }]); setDraft('') } }
  return (
    <div>
      <div className="card-title">{title}</div>
      {points.map((p, i) => (
        <div key={i} style={{ display: 'flex', gap: 6, alignItems: 'center', marginBottom: 5 }}>
          <select aria-label={`${title} ${i + 1} severity`} className="tbl-sel" value={p.severity}
            onChange={e => onChange(points.map((q, j) => (j === i ? { ...q, severity: e.target.value as Severity } : q)))}>
            {SEVS.map(s => <option key={s} value={s}>{s}</option>)}
          </select>
          <input aria-label={`${title} ${i + 1}`} className="form-input" style={{ flex: 1, minWidth: 0 }} value={p.text}
            onChange={e => onChange(points.map((q, j) => (j === i ? { ...q, text: e.target.value } : q)))} />
          <button type="button" className="pb" onClick={() => onChange(points.filter((_, j) => j !== i))} aria-label="Remove">✕</button>
        </div>
      ))}
      <div style={{ display: 'flex', gap: 6, alignItems: 'center' }}>
        <select id={`${idPrefix}-sev`} aria-label={`New ${title} severity`} className="tbl-sel" value={sev} onChange={e => setSev(e.target.value as Severity)}>
          {SEVS.map(s => <option key={s} value={s}>{s}</option>)}
        </select>
        <input id={`${idPrefix}-new`} className="form-input" style={{ flex: 1, minWidth: 0 }} placeholder={`Add a ${title.toLowerCase().replace(/s$/, '')}…`} value={draft}
          onChange={e => setDraft(e.target.value)} onKeyDown={e => { if (e.key === 'Enter') { e.preventDefault(); add() } }} />
        <button type="button" className="pb" onClick={add}>Add</button>
      </div>
    </div>
  )
}

export function CommentsLog({ comments, canEdit, onAdd, onDelete }: {
  comments: LpComment[]; canEdit: boolean; onAdd: (text: string) => Promise<void>; onDelete: (id: number) => Promise<void>
}) {
  const [text, setText] = useState('')
  const [busy, setBusy] = useState(false)
  return (
    <div>
      {canEdit && (
        <div style={{ display: 'flex', gap: 6, marginBottom: 10 }}>
          <textarea aria-label="New comment" className="form-textarea" rows={2} style={{ flex: 1, minWidth: 0, resize: 'vertical' }}
            placeholder="Add a comment (IC discussion, GP meeting, update…)" value={text} onChange={e => setText(e.target.value)} />
          <button className="btn btn-primary" disabled={!text.trim() || busy}
            onClick={async () => { setBusy(true); await onAdd(text.trim()); setText(''); setBusy(false) }}>Post</button>
        </div>
      )}
      {comments.length ? comments.map(c => (
        <div key={c.id} style={{ borderTop: '1px solid var(--border)', padding: '7px 0', display: 'flex', gap: 8 }}>
          <div style={{ flex: 1, minWidth: 0 }}>
            <div className="sub">{new Date(c.created_at).toLocaleDateString('en-GB', { day: '2-digit', month: 'short', year: 'numeric' })} · {c.author_name}</div>
            <div className="prose" style={{ whiteSpace: 'pre-wrap' }}>{c.text}</div>
          </div>
          {canEdit && <button className="pb" style={{ alignSelf: 'flex-start' }} onClick={() => void onDelete(c.id)} aria-label="Delete comment">Delete</button>}
        </div>
      )) : <p className="note">No comments yet.</p>}
    </div>
  )
}
