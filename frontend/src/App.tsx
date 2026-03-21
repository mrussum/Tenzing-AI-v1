import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import Login from './pages/Login'
import Portfolio from './pages/Portfolio'
import AccountDetail from './pages/AccountDetail'
import Briefing from './pages/Briefing'
import { AuthProvider, useAuth } from './AuthContext'

function RequireAuth({ children }: { children: React.ReactNode }) {
  const { username, loading } = useAuth()
  if (loading) return null  // brief blank while cookie is verified
  if (!username) return <Navigate to="/login" replace />
  return <>{children}</>
}

function AppRoutes() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route
        path="/"
        element={
          <RequireAuth>
            <Portfolio />
          </RequireAuth>
        }
      />
      <Route
        path="/accounts/:id"
        element={
          <RequireAuth>
            <AccountDetail />
          </RequireAuth>
        }
      />
      <Route
        path="/briefing"
        element={
          <RequireAuth>
            <Briefing />
          </RequireAuth>
        }
      />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}

export default function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <AppRoutes />
      </AuthProvider>
    </BrowserRouter>
  )
}
