import { Navigate, Outlet } from 'react-router-dom'
import { useAuth } from './AuthContext'

export function ProtectedRoute() {
  const { status } = useAuth()
  if (status === 'unauthenticated') return <Navigate to="/login" replace />
  return <Outlet />
}
