import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import Login from './pages/Login'
import Portfolio from './pages/Portfolio'
import AccountDetail from './pages/AccountDetail'
import Briefing from './pages/Briefing'
import { getToken } from './api/client'

function RequireAuth({ children }: { children: React.ReactNode }) {
  const token = getToken()
  if (!token) return <Navigate to="/login" replace />
  return <>{children}</>
}

export default function App() {
  return (
    <BrowserRouter>
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
    </BrowserRouter>
  )
}
