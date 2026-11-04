/**
 * Axios client for the Atlas Django API (same pattern as Dynamo's api.ts),
 * with JWT bearer auth and one silent refresh on 401.
 */
import axios, { AxiosError, type InternalAxiosRequestConfig } from 'axios'
import { useAuthStore } from '../store/auth'

export const API_BASE = (import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1').replace(/\/$/, '')

export const api = axios.create({ baseURL: API_BASE, timeout: 60_000 })

api.interceptors.request.use(cfg => {
  const token = useAuthStore.getState().access
  if (token) cfg.headers.Authorization = `Bearer ${token}`
  return cfg
})

let refreshing: Promise<string | null> | null = null

api.interceptors.response.use(undefined, async (error: AxiosError) => {
  const cfg = error.config as (InternalAxiosRequestConfig & { _retried?: boolean }) | undefined
  if (error.response?.status !== 401 || !cfg || cfg._retried || cfg.url?.includes('/auth/')) throw error
  cfg._retried = true
  refreshing = refreshing ?? useAuthStore.getState().refresh().finally(() => { refreshing = null })
  const token = await refreshing
  if (!token) throw error
  cfg.headers.Authorization = `Bearer ${token}`
  return api(cfg)
})

/** Fetch every row of a DRF paginated list. */
export async function fetchAll<T>(path: string): Promise<T[]> {
  const out: T[] = []
  let url: string | null = `${path}${path.includes('?') ? '&' : '?'}page_size=10000`
  while (url) {
    const res: { data: { results: T[]; next: string | null } } = await api.get(url)
    out.push(...res.data.results)
    url = res.data.next
  }
  return out
}

export function errorText(e: unknown): string {
  if (axios.isAxiosError(e)) {
    const d = e.response?.data as { detail?: string } | undefined
    if (d?.detail) return d.detail
    if (!e.response) return `Cannot reach the API at ${API_BASE}. Check that the backend service is running.`
    return `API error ${e.response.status}`
  }
  return e instanceof Error ? e.message : String(e)
}
