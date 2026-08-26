import { useAuth } from '../auth/AuthContext'
import { ExecutionsTable } from '../features/dashboard/ExecutionsTable'
import { OrdersTable } from '../features/dashboard/OrdersTable'
import { PositionsTable } from '../features/dashboard/PositionsTable'
import { SummaryCards } from '../features/dashboard/SummaryCards'
import { TradesTable } from '../features/dashboard/TradesTable'
import { useDashboardData } from '../features/dashboard/useDashboardData'

export function DashboardPage() {
  const { user, logout } = useAuth()
  const { summary, positions, orders, executions, trades, loading, error, reload } =
    useDashboardData()

  return (
    <div className="dashboard-page">
      <header className="dashboard-header">
        <h1>Dashboard</h1>
        <div className="dashboard-header-actions">
          <span>Welcome, {user?.username}.</span>
          <button onClick={() => reload()} disabled={loading}>
            Refresh
          </button>
          <button onClick={() => void logout()}>Sign out</button>
        </div>
      </header>

      {error && <p className="auth-error">{error}</p>}
      {loading && !summary && <p className="empty-state">Loading dashboard…</p>}

      {summary && <SummaryCards summary={summary} />}
      <PositionsTable positions={positions} />
      <OrdersTable orders={orders} />
      <ExecutionsTable executions={executions} />
      <TradesTable trades={trades} />
    </div>
  )
}
