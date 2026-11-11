import { useEffect, type ReactNode } from 'react'
import { closeDrawer } from '../lib/route'

export default function Drawer({ eyebrow, title, link, actions, logo, children }: {
  eyebrow?: string; title: ReactNode; link?: string; actions?: ReactNode; logo?: ReactNode; children: ReactNode
}) {
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => { if (e.key === 'Escape') closeDrawer() }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [])
  return (
    <>
      <div className="drawer-scrim" onClick={closeDrawer} />
      <aside className="drawer" role="dialog" aria-modal="true">
        <div className="drawer-hd">
          <div style={{ minWidth: 0, display: 'flex', gap: 12, alignItems: 'center' }}>
            {logo && <span className="drawer-logo">{logo}</span>}
            <div style={{ minWidth: 0 }}>
              {eyebrow && <div className="eyebrow">{eyebrow}</div>}
              <h2>{title}</h2>
              {link && <a href={link} target="_blank" rel="noopener noreferrer">{link.replace(/^https?:\/\//, '')}</a>}
            </div>
          </div>
          <div className="actions">{actions}<button className="btn" onClick={closeDrawer} autoFocus>Close</button></div>
        </div>
        <div className="drawer-bd">{children}</div>
      </aside>
    </>
  )
}
