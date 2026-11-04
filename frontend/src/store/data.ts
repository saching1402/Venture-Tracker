/** Global data store: the whole manager + company universe loads once, like Dynamo. */
import { create } from 'zustand'
import { api, fetchAll } from '../lib/api'
import type { CompanyRow, ManagerRow, Meta, Watchlist } from '../types'

interface DataState {
  meta: Meta | null
  managers: ManagerRow[]
  companies: CompanyRow[]
  mgrById: Record<string, ManagerRow>
  coById: Record<string, CompanyRow>
  watch: Watchlist
  loaded: boolean
  load: () => Promise<void>
  toggleWatch: (kind: 'manager' | 'company', id: string) => Promise<void>
}

export const useData = create<DataState>((set, get) => ({
  meta: null,
  managers: [],
  companies: [],
  mgrById: {},
  coById: {},
  watch: { managers: [], companies: [] },
  loaded: false,

  async load() {
    const [meta, managers, companies, watch] = await Promise.all([
      api.get<Meta>('/meta/').then(r => r.data),
      fetchAll<ManagerRow>('/managers/'),
      fetchAll<CompanyRow>('/companies/'),
      api.get<Watchlist>('/watchlist/').then(r => r.data),
    ])
    set({
      meta, managers, companies, watch, loaded: true,
      mgrById: Object.fromEntries(managers.map(m => [m.id, m])),
      coById: Object.fromEntries(companies.map(c => [c.id, c])),
    })
  },

  async toggleWatch(kind, id) {
    const key = kind === 'manager' ? 'managers' : 'companies'
    const on = !get().watch[key].includes(id)
    // optimistic update, then reconcile with the server
    set(s => ({ watch: { ...s.watch, [key]: on ? [...s.watch[key], id] : s.watch[key].filter(x => x !== id) } }))
    try {
      const { data } = await api.post<Watchlist>('/watchlist/', { kind, id, on })
      set({ watch: data })
    } catch {
      set(s => ({ watch: { ...s.watch, [key]: on ? s.watch[key].filter(x => x !== id) : [...s.watch[key], id] } }))
    }
  },
}))
