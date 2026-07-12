import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'

import { AppShell } from './components/AppShell'
import { AuthProvider } from './context/AuthContext'
import { DashboardPage } from './pages/DashboardPage'
import { HomePage } from './pages/HomePage'
import { HostSessionPage } from './pages/HostSessionPage'
import { JoinPage } from './pages/JoinPage'
import { LoginPage } from './pages/LoginPage'
import { ParticipantRoomPage } from './pages/ParticipantRoomPage'
import { RegisterPage } from './pages/RegisterPage'

function NotFoundPage() {
  return (
    <AppShell>
      <div className="flex min-h-[calc(100vh-73px)] flex-col items-center justify-center gap-4 px-6">
        <h1 className="font-display text-2xl text-foreground">Signal lost</h1>
        <p className="font-body text-muted">This route does not exist.</p>
        <a href="/" className="btn-primary">
          Return home
        </a>
      </div>
    </AppShell>
  )
}

export default function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<HomePage />} />
          <Route path="/login" element={<LoginPage />} />
          <Route path="/register" element={<RegisterPage />} />
          <Route path="/dashboard" element={<DashboardPage />} />
          <Route path="/join" element={<JoinPage />} />
          <Route path="/host/:sessionId" element={<HostSessionPage />} />
          <Route path="/room/:sessionId" element={<ParticipantRoomPage />} />
          <Route path="/home" element={<Navigate to="/" replace />} />
          <Route path="*" element={<NotFoundPage />} />
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  )
}
