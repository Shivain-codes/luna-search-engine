import { create } from 'zustand'
import { api } from '@/services/api'

interface AuthState {
  isAuthenticated: boolean
  login: (email: string, password: string) => Promise<void>
  logout: () => void
  check: () => void
}

export const useAuthStore = create<AuthState>((set) => ({
  isAuthenticated: api.isAuthenticated(),
  login: async (email, password) => {
    await api.login(email, password)
    set({ isAuthenticated: true })
  },
  logout: () => {
    api.clearToken()
    set({ isAuthenticated: false })
  },
  check: () => set({ isAuthenticated: api.isAuthenticated() }),
}))
