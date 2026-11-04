/**
 * Auth store — signs in against the Django SimpleJWT endpoints.
 * Access token is kept in memory; the refresh token lives in sessionStorage
 * so a reload keeps you signed in until the tab closes.
 */
import axios from 'axios'
import { create } from 'zustand'

const BASE = (import.meta.env.VITE_API_URL || '/api/v1').replace(/\/$/, '')
const KEY = 'atlas_refresh'

function readRefresh(): string | null {
  try { return sessionStorage.getItem(KEY) } catch { return null }
}
function writeRefresh(v: string | null) {
  try { v ? sessionStorage.setItem(KEY, v) : sessionStorage.removeItem(KEY) } catch { /* private mode */ }
}

interface AuthState {
  access: string | null
  refreshToken: string | null
  email: string | null
  booting: boolean
  login: (email: string, password: string) => Promise<string | null>
  refresh: () => Promise<string | null>
  logout: () => void
  boot: () => Promise<void>
}

export const useAuthStore = create<AuthState>((set, get) => ({
  access: null,
  refreshToken: readRefresh(),
  email: null,
  booting: true,

  async login(email, password) {
    try {
      const { data } = await axios.post(`${BASE}/auth/token/`, { email, password })
      writeRefresh(data.refresh)
      set({ access: data.access, refreshToken: data.refresh, email })
      return null
    } catch (e) {
      if (axios.isAxiosError(e)) {
        if (!e.response) return 'Cannot reach the server. Check your connection and try again.'
        if (e.response.status === 401) return 'Email or password is incorrect.'
        if (e.response.status === 429) return 'Too many attempts. Wait a minute and try again.'
      }
      return 'Sign-in failed. Try again.'
    }
  },

  async refresh() {
    const rt = get().refreshToken
    if (!rt) return null
    try {
      const { data } = await axios.post(`${BASE}/auth/token/refresh/`, { refresh: rt })
      if (data.refresh) writeRefresh(data.refresh)
      set({ access: data.access, refreshToken: data.refresh ?? rt })
      return data.access as string
    } catch {
      get().logout()
      return null
    }
  },

  logout() {
    writeRefresh(null)
    set({ access: null, refreshToken: null, email: null })
  },

  async boot() {
    if (get().refreshToken) await get().refresh()
    set({ booting: false })
  },
}))
