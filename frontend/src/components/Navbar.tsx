import { Link, useNavigate, useLocation } from 'react-router-dom'
import { authLogout } from '../api/client'

export default function Navbar() {
  const navigate = useNavigate()
  const location = useLocation()

  const handleLogout = async () => {
    await authLogout().catch(() => {})
    navigate('/login')
  }

  const navLink = (to: string, label: string) => {
    const active = location.pathname === to
    return (
      <Link
        to={to}
        className={`px-3 py-2 rounded-md text-sm font-medium transition-colors ${
          active
            ? 'bg-tenzing-700 text-white'
            : 'text-tenzing-100 hover:bg-tenzing-600 hover:text-white'
        }`}
      >
        {label}
      </Link>
    )
  }

  return (
    <nav className="bg-tenzing-500 shadow-md">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-14">
          <div className="flex items-center gap-6">
            <Link to="/" className="text-white font-bold text-lg tracking-tight">
              Tenzing AI
            </Link>
            <div className="flex items-center gap-1">
              {navLink('/', 'Portfolio')}
              {navLink('/briefing', 'Leadership Brief')}
            </div>
          </div>
          <button
            onClick={handleLogout}
            className="text-tenzing-100 hover:text-white text-sm font-medium"
          >
            Sign out
          </button>
        </div>
      </div>
    </nav>
  )
}
