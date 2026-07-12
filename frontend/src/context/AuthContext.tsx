import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from 'react'

import { api } from '../api/client'
import type { User, UserRole } from '../types/api'

const TOKEN_KEY = 'neuracle_token'

interface AuthContextValue {
  user: User | null
  loading: boolean
  login: (email: string, password: string) => Promise<User>
  register: (email: string, password: string, role: UserRole) => Promise<User>
  logout: () => void
}

const AuthContext = createContext<AuthContextValue | null>(null)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const token = localStorage.getItem(TOKEN_KEY)
    if (!token) {
      setLoading(false)
      return
    }

    api.setToken(token)
    api
      .getMe()
      .then(setUser)
      .catch(() => {
        localStorage.removeItem(TOKEN_KEY)
        api.setToken(null)
      })
      .finally(() => setLoading(false))
  }, [])

  const login = useCallback(async (email: string, password: string) => {
    const tokenResponse = await api.login(email, password)
    localStorage.setItem(TOKEN_KEY, tokenResponse.access_token)
    api.setToken(tokenResponse.access_token)
    const currentUser = await api.getMe()
    setUser(currentUser)
    return currentUser
  }, [])

  const register = useCallback(
    async (email: string, password: string, role: UserRole) => {
      await api.register(email, password, role)
      return login(email, password)
    },
    [login],
  )

  const logout = useCallback(() => {
    localStorage.removeItem(TOKEN_KEY)
    api.setToken(null)
    setUser(null)
  }, [])

  const value = useMemo(
    () => ({ user, loading, login, register, logout }),
    [user, loading, login, register, logout],
  )

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth() {
  const context = useContext(AuthContext)
  if (!context) {
    throw new Error('useAuth must be used within AuthProvider')
  }
  return context
}
