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
    if (!localStorage.getItem('access_token')) {
      setState({ username: null, loading: false })
      return
    }
    fetchCurrentUser()
      .then((data) => setState({ username: data.username, loading: false }))
      .catch(() => {
        localStorage.removeItem('access_token')
        setState({ username: null, loading: false })
      })
  }, [])

  return <AuthContext.Provider value={state}>{children}</AuthContext.Provider>
}

export const useAuth = () => useContext(AuthContext)
