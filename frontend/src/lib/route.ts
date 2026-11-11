/** Hash routing — #managers, #companies, #shortlist, #gp-<id>, #co-<id>, #inv-<id>, #sl-<id> — so views are linkable. */
import { useEffect, useState } from 'react'

export type View = 'managers' | 'companies' | 'shortlist' | 'trends' | 'track' | 'rounds' | 'overlap' | 'watchlist' | 'changes' | 'method'
export const VIEWS: { id: View; label: string }[] = [
  { id: 'managers', label: 'Managers' },
  { id: 'companies', label: 'Companies' },
  { id: 'shortlist', label: 'Shortlisted' },
  { id: 'trends', label: 'Trends' },
  { id: 'track', label: 'Track Record' },
  { id: 'rounds', label: 'Recent Rounds' },
  { id: 'overlap', label: 'Overlap & Focus' },
  { id: 'watchlist', label: 'Watchlist' },
  { id: 'changes', label: 'Change Log' },
  { id: 'method', label: 'Method' },
]

let lastView: View = 'managers'

export function go(hash: string) {
  if (location.hash.slice(1) !== hash) location.hash = hash
}

export function closeDrawer() {
  history.replaceState(null, '', `#${lastView}`)
  window.dispatchEvent(new HashChangeEvent('hashchange'))
}

export function parse(h: string): { view: View; drawer: { kind: 'gp' | 'co' | 'inv' | 'sl' | 'th'; id: string } | null } {
  const hash = h.replace(/^#/, '')
  const m = hash.match(/^(gp|co|inv|sl|th)-(.+)$/)
  if (m) return { view: lastView, drawer: { kind: m[1] as 'gp' | 'co' | 'inv' | 'sl' | 'th', id: decodeURIComponent(m[2]) } }
  const view = (VIEWS.find(v => v.id === hash)?.id ?? 'managers') as View
  lastView = view
  return { view, drawer: null }
}

export function useRoute() {
  const [r, setR] = useState(() => parse(location.hash))
  useEffect(() => {
    const on = () => setR(parse(location.hash))
    window.addEventListener('hashchange', on)
    return () => window.removeEventListener('hashchange', on)
  }, [])
  return r
}
