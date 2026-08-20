import { Link, useNavigate } from 'react-router-dom'

import { useAuth } from '../context/AuthContext'

export function AppShell({ children }: { children: React.ReactNode }) {
  const { user, logout } = useAuth()
  const navigate = useNavigate()

  return (
    <div className="relative min-h-screen text-foreground">
      <header className="sticky top-0 z-50 border-b border-white/5 bg-void/80 backdrop-blur-md">
        <div className="mx-auto flex max-w-6xl items-center justify-between px-6 py-4">
          <Link to="/" className="font-body text-sm text-foreground transition hover:text-aurora">
            HOME
          </Link>

          <nav className="flex items-center gap-4">
            {user ? (
              <>
                <span className="hidden font-body text-sm text-muted sm:inline">
                  {user.email}
                  <span className="ml-2 rounded-full border border-white/10 px-2 py-0.5 text-xs uppercase tracking-wider text-aurora">
                    {user.role}
                  </span>
                </span>
                <Link
                  to="/dashboard"
                  className="font-body text-sm text-muted transition hover:text-aurora"
                >
                  Dashboard
                </Link>
                {user.role === 'participant' && (
                  <Link
                    to="/join"
                    className="font-body text-sm text-muted transition hover:text-plasma"
                  >
                    Join room
                  </Link>
                )}
                <button
                  type="button"
                  onClick={() => {
                    logout()
                    navigate('/')
                  }}
                  className="btn-ghost font-body text-sm"
                >
                  Sign out
                </button>
              </>
            ) : (
              <>
                <Link to="/login" className="btn-ghost font-body text-sm">
                  Sign in
                </Link>
                <Link to="/register" className="btn-primary font-body text-sm">
                  Get started
                </Link>
              </>
            )}
          </nav>
        </div>
      </header>

      <main>{children}</main>
    </div>
  )
}
