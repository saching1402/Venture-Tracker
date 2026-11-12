/**
 * Research store: Add manager / Add company jobs. Polls the API while jobs are active
 * and reloads the universe when one finishes, so new rows fill in on their own.
 */
import { create } from 'zustand'
import { api, errorText } from '../lib/api'
import type { AddOptions, ResearchState } from '../types'
import { useData } from './data'

interface AddResult { ok: boolean; id?: string; exists?: boolean; message?: string }

interface ResearchStore extends ResearchState {
  loaded: boolean
  trayOpen: boolean
  setTray: (open: boolean) => void
  refresh: () => Promise<void>
  add: (kind: 'manager' | 'company', name: string, website: string, opts: AddOptions) => Promise<AddResult>
  reresearch: (kind: 'manager' | 'company', id: string, model?: string) => Promise<AddResult>
  retry: (jobId: string) => Promise<void>
}

let timer: ReturnType<typeof setTimeout> | null = null
let lastDone = ''

export const useResearch = create<ResearchStore>((set, get) => ({
  enabled: false, can_research: false, active: 0, jobs: [], loaded: false, trayOpen: false,
  models: [], defaults: { manager: '', portfolio: '', company: '' }, max_portfolio: 25,

  setTray: open => set({ trayOpen: open }),

  async refresh() {
    try {
      const { data } = await api.get<ResearchState>('/research/')
      const doneKey = data.jobs.filter(j => j.kind !== 'coprofile' && j.kind !== 'gpprofile').map(j => `${j.id}:${j.status}:${j.children_done}`).join('|')
      const changed = get().loaded && doneKey !== lastDone
      lastDone = doneKey
      set({ ...data, loaded: true })
      if (changed) await useData.getState().load()   // pick up newly researched rows
      if (timer) clearTimeout(timer)
      if (data.active > 0) timer = setTimeout(() => void get().refresh(), 5000)
    } catch { /* keep last state; next action retries */ }
  },

  async add(kind, name, website, opts) {
    try {
      const { data } = await api.post<{ id: string }>('/research/', { kind, name, website, ...opts })
      await useData.getState().load()
      await get().refresh()
      set({ trayOpen: true })
      return { ok: true, id: data.id }
    } catch (e) {
      const d = (e as { response?: { status?: number; data?: { id?: string; exists?: boolean } } }).response
      return { ok: false, id: d?.data?.id, exists: d?.status === 409, message: errorText(e) }
    }
  },

  async reresearch(kind, id, model) {
    try {
      await api.post('/research/', { kind, id, model })
      await useData.getState().load()
      await get().refresh()
      set({ trayOpen: true })
      return { ok: true, id }
    } catch (e) {
      return { ok: false, message: errorText(e) }
    }
  },

  async retry(jobId) {
    await api.post(`/research/${jobId}/retry/`)
    await useData.getState().load()
    await get().refresh()
  },
}))
