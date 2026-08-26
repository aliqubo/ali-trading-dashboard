import { useCallback, useEffect, useState } from 'react'
import { ApiError } from '../../api/client'
import * as tradingApi from '../../api/trading'
import type {
  DashboardSummary,
  ExecutionRow,
  OrderRow,
  PositionRow,
  TradeRow,
} from '../../api/trading'

interface DashboardData {
  summary: DashboardSummary | null
  positions: PositionRow[]
  orders: OrderRow[]
  executions: ExecutionRow[]
  trades: TradeRow[]
  loading: boolean
  error: string | null
  reload: () => void
}

export function useDashboardData(): DashboardData {
  const [summary, setSummary] = useState<DashboardSummary | null>(null)
  const [positions, setPositions] = useState<PositionRow[]>([])
  const [orders, setOrders] = useState<OrderRow[]>([])
  const [executions, setExecutions] = useState<ExecutionRow[]>([])
  const [trades, setTrades] = useState<TradeRow[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [reloadKey, setReloadKey] = useState(0)

  useEffect(() => {
    let cancelled = false

    async function load() {
      setLoading(true)
      setError(null)
      try {
        const [summaryData, positionsData, ordersData, executionsData, tradesData] =
          await Promise.all([
            tradingApi.fetchSummary(),
            tradingApi.fetchPositions(),
            tradingApi.fetchOrders(),
            tradingApi.fetchExecutions(),
            tradingApi.fetchTrades(),
          ])
        if (cancelled) return
        setSummary(summaryData)
        setPositions(positionsData)
        setOrders(ordersData)
        setExecutions(executionsData)
        setTrades(tradesData)
      } catch (err) {
        if (cancelled) return
        setError(err instanceof ApiError ? err.message : 'Failed to load dashboard data.')
      } finally {
        if (!cancelled) setLoading(false)
      }
    }

    void load()
    return () => {
      cancelled = true
    }
  }, [reloadKey])

  const reload = useCallback(() => setReloadKey((key) => key + 1), [])

  return { summary, positions, orders, executions, trades, loading, error, reload }
}
