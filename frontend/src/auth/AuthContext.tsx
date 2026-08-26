import { createContext, useCallback, useContext, useEffect, useState, type ReactNode } from 'react'
import * as authApi from '../api/auth'
import type { User } from '../api/auth'
import { onSessionExpired } from '../api/client'

interface AuthContextValue {
  user: User | null
  status: 'unauthenticated' | 'authenticated'
  login: (identifier: string, password: string) => Promise<void>
  logout: () => Promise<void>
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null)

  useEffect(() => onSessionExpired(() => setUser(null)), [])

  const login = useCallback(async (identifier: string, password: string) => {
    const loggedInUser = await authApi.login(identifier, password)
    setUser(loggedInUser)
  }, [])

  const logout = useCallback(async () => {
    try {
      await authApi.logout()
    } finally {
      setUser(null)
    }
  }, [])

  const value: AuthContextValue = {
    user,
    status: user ? 'authenticated' : 'unauthenticated',
    login,
    logout,
  }

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used within an AuthProvider')
  return ctx
}
