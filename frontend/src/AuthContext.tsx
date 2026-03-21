import { createContext, useContext, useEffect, useState, ReactNode } from 'react'
import { fetchCurrentUser } from './api/client'

interface AuthState {
  username: string | null
  loading: boolean
}

const AuthContext = createContext<AuthState>({ username: null, loading: true })

export function AuthProvider({ children }: { children: ReactNode }) {
  const [state, setState] = useState<AuthState>({ username: null, loading: true })

  useEffect(() => {
    fetchCurrentUser()
      .then((data) => setState({ username: data.username, loading: false }))
      .catch(() => setState({ username: null, loading: false }))
  }, [])

  return <AuthContext.Provider value={state}>{children}</AuthContext.Provider>
}

export const useAuth = () => useContext(AuthContext)
