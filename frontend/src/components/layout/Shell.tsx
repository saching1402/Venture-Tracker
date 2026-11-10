import { useEffect, useState } from 'react'
import { errorText } from '../../lib/api'
import { money } from '../../lib/format'
import { VIEWS, go, useRoute } from '../../lib/route'
import { useAuthStore } from '../../store/auth'
import { useData } from '../../store/data'
import Changes from '../../pages/Changes'
import Companies from '../../pages/Companies'
import CompanyDrawer from '../../pages/CompanyDrawer'
import Login from '../../pages/Login'
import ManagerDrawer from '../../pages/ManagerDrawer'
import Managers from '../../pages/Managers'
import Method from '../../pages/Method'
import Overlap from '../../pages/Overlap'
import Rounds from '../../pages/Rounds'
import Watchlist from '../../pages/Watchlist'
import TrackRecord, { InvestmentDrawer } from '../../pages/TrackRecord'
import Shortlist, { ShortlistDrawer } from '../../pages/Shortlist'
import { ResearchTray } from '../Research'

const PAGES = { managers: Managers, companies: Companies, shortlist: Shortlist, track: TrackRecord, rounds: Rounds, overlap: Overlap, watchlist: Watchlist, changes: Changes, method: Method }

function Splash({ children }: { children: React.ReactNode }) {
  return (
    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100vh', flexDirection: 'column', gap: 14, background: 'var(--bg)' }}>
      <div style={{ fontSize: 30, fontFamily: 'var(--f-display)', color: 'var(--navy)' }}>Venture GP Atlas</div>
      {children}
    </div>
  )
}

function AppShell() {
  const { loaded, load, meta } = useData()
  const { email, logout } = useAuthStore()
  const [err, setErr] = useState<string | null>(null)
  const { view, drawer } = useRoute()

  useEffect(() => { load().catch(e => setErr(errorText(e))) }, [load])

  if (err) return (
    <Splash>
      <div className="err-box" style={{ maxWidth: 480, textAlign: 'center' }}>{err}</div>
      <button className="btn btn-primary" onClick={() => window.location.reload()}>Retry</button>
    </Splash>
  )
  if (!loaded) return (
    <Splash>
      <div style={{ color: 'var(--muted)' }}>Loading managers and portfolio companies…</div>
      <div style={{ width: 200, height: 3, background: 'var(--border)', borderRadius: 2, overflow: 'hidden' }}>
        <div style={{ width: '60%', height: '100%', background: 'var(--gold)', animation: 'pulse 1.5s ease-in-out infinite' }} />
      </div>
    </Splash>
  )

  const Page = PAGES[view]
  const asof = meta?.asof ? new Date(meta.asof).toLocaleDateString('en-GB', { day: '2-digit', month: 'short', year: 'numeric' }) : '—'

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100vh', overflow: 'hidden' }}>
      <div id="app-header">
        <span className="logo">Venture GP <em>·</em> Atlas</span>
        <span className="logo-tag">Mindari &nbsp;·&nbsp; VC &amp; Growth Managers</span>
        <div className="hdr-space" />
        <span className="hdr-asof">{meta?.managers} managers · {meta?.companies} companies · {money(meta?.combined_value_usd_bn)}&nbsp;&nbsp;·&nbsp;&nbsp;Data as of&nbsp;</span>
        <span className="hdr-date">{asof}</span>
        <div className="hdr-div" style={{ width: 1, height: 18, background: 'var(--border)', margin: '0 14px' }} />
        <ResearchTray />
        <span className="hdr-email" style={{ fontSize: 11.5, color: 'var(--muted)', margin: '0 10px 0 12px' }}>{email}</span>
        <button className="hdr-btn" onClick={logout}>Sign out</button>
      </div>
      <div id="app-tabnav-wrap">
        <div id="app-tabnav">
          {VIEWS.map(v => (
            <button key={v.id} className={`tab-item${view === v.id ? ' active' : ''}`} onClick={() => go(v.id)}>{v.label}</button>
          ))}
        </div>
      </div>
      <div id="app-body">
        <div id="app-content" key={view}>
          <div className="page fade-in"><Page /></div>
        </div>
      </div>
      {drawer?.kind === 'gp' && <ManagerDrawer key={drawer.id} id={drawer.id} />}
      {drawer?.kind === 'co' && <CompanyDrawer key={drawer.id} id={drawer.id} />}
      {drawer?.kind === 'inv' && <InvestmentDrawer key={drawer.id} id={drawer.id} />}
      {drawer?.kind === 'sl' && <ShortlistDrawer key={drawer.id} id={drawer.id} />}
    </div>
  )
}

export default function Shell() {
  const { access, booting, boot } = useAuthStore()
  useEffect(() => { void boot() }, [boot])
  if (booting) return <Splash><div style={{ color: 'var(--muted)' }}>Signing in…</div></Splash>
  return access ? <AppShell /> : <Login />
}
