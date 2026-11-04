/** USD-billions formatters for the Atlas (inputs are in $bn). */
export const num = (v: unknown): number | null =>
  v === null || v === undefined || v === '' || Number.isNaN(Number(v)) ? null : Number(v)

export function money(v: number | null | undefined): string {
  const n = num(v)
  if (n === null) return '—'
  if (n >= 1000) return `$${(n / 1000).toFixed(2)}T`
  if (n >= 100) return `$${n.toFixed(0)}B`
  if (n >= 1) return `$${n.toFixed(1)}B`
  return `$${Math.round(n * 1000)}M`
}

export function xmult(v: number | null | undefined): string {
  const n = num(v)
  if (n === null) return '—'
  return `${n >= 100 ? n.toFixed(0) : n.toFixed(1)}x`
}

export const clip = (s: string | null | undefined, n: number): string =>
  !s ? '' : s.length > n ? `${s.slice(0, n - 1)}…` : s

export const uniq = (a: (string | null | undefined)[]): string[] =>
  [...new Set(a.filter((x): x is string => !!x))].sort((x, y) => x.localeCompare(y))

export function shortName(name: string): string {
  return name.replace(/\s*\(.*?\)/, '')
    .replace(/ (Venture Partners|Ventures|Capital|Partners|Management|Investment Group|Global Management|Equity)$/, '')
}

export function statusKind(s: string): 'priv' | 'pub' | 'acq' | 'dead' {
  const t = (s || '').toLowerCase()
  if (t.startsWith('public')) return 'pub'
  if (t.startsWith('acq') || t.startsWith('taken private')) return 'acq'
  if (t.startsWith('shut') || t.startsWith('delist')) return 'dead'
  return 'priv'
}

export function downloadCsv(filename: string, header: string[], rows: unknown[][]) {
  const q = (v: unknown) => `"${String(v ?? '').replace(/"/g, '""')}"`
  const csv = [header.map(q).join(','), ...rows.map(r => r.map(q).join(','))].join('\n')
  const url = URL.createObjectURL(new Blob([csv], { type: 'text/csv;charset=utf-8' }))
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  document.body.appendChild(a)
  a.click()
  a.remove()
  setTimeout(() => URL.revokeObjectURL(url), 2000)
}

/** USD millions → "$12.5m" / "$1.25bn" */
export function usdm(v: number | null | undefined): string {
  const n = num(v)
  if (n === null) return '—'
  if (n === 0) return '$0'
  if (Math.abs(n) >= 1000) return `$${(n / 1000).toFixed(2)}bn`
  if (Math.abs(n) >= 1) return `$${n.toFixed(1)}m`
  return `$${Math.round(n * 1000)}k`
}

export const pct = (v: number | null | undefined, dp = 1): string => {
  const n = num(v)
  return n === null ? '—' : `${(n * 100).toFixed(dp)}%`
}

export const x2 = (v: number | null | undefined): string => {
  const n = num(v)
  return n === null ? '—' : `${n.toFixed(2)}x`
}
