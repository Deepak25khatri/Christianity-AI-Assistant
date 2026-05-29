import { create } from 'zustand'

export type Denomination = 'catholic' | 'protestant' | 'orthodox' | 'none'

export type AuthUser = {
  user_id: number
  email: string
  denomination_pref: Denomination | null
  token: string
}

type AuthState = {
  user: AuthUser | null
  setUser: (u: AuthUser | null) => void
  logout: () => void
}

const STORAGE_KEY = 'christianity-ai-user'

export const useAuth = create<AuthState>((set) => ({
  user: (() => {
    try {
      const raw = localStorage.getItem(STORAGE_KEY)
      return raw ? (JSON.parse(raw) as AuthUser) : null
    } catch {
      return null
    }
  })(),
  setUser: (u) => {
    if (u) localStorage.setItem(STORAGE_KEY, JSON.stringify(u))
    else localStorage.removeItem(STORAGE_KEY)
    set({ user: u })
  },
  logout: () => {
    localStorage.removeItem(STORAGE_KEY)
    set({ user: null })
  },
}))
