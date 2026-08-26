import { apiRequest } from './client'

export interface SymbolInfo {
  id: string
  ticker: string
  name: string
}

export interface OrderRow {
  id: string
  symbol: SymbolInfo | null
  side: string
  order_type: string
  time_in_force: string
  quantity: number
  price: number | null
  stop_price: number | null
  filled_quantity: number
  avg_fill_price: number | null
  status: string
  reject_reason: string | null
  submitted_at: string | null
  created_at: string
  updated_at: string
}

export interface ExecutionRow {
  id: string
  order_id: string
  symbol: SymbolInfo | null
  exec_price: number
  exec_quantity: number
  fee: number
  fee_currency: string | null
  liquidity: string
  executed_at: string
}

export interface PositionRow {
  id: string
  symbol: SymbolInfo | null
  side: string
  quantity: number
  avg_entry_price: number
  current_price: number | null
  unrealized_pnl: number | null
  realized_pnl: number
  status: string
  opened_at: string
  closed_at: string | null
}

export interface TradeRow {
  id: string
  symbol: SymbolInfo | null
  side: string
  entry_price: number
  exit_price: number | null
  quantity: number
  gross_pnl: number | null
  net_pnl: number | null
  total_fees: number
  return_pct: number | null
  status: string
  entry_at: string
  exit_at: string | null
}

export interface DashboardSummary {
  open_positions_count: number
  open_orders_count: number
  unrealized_pnl_total: number
  closed_trades_count: number
  realized_pnl_total: number
}

export async function fetchSummary(): Promise<DashboardSummary> {
  return apiRequest<DashboardSummary>('/trading/summary', { auth: true })
}

export async function fetchPositions(): Promise<PositionRow[]> {
  return apiRequest<PositionRow[]>('/trading/positions', { auth: true })
}

export async function fetchOrders(): Promise<OrderRow[]> {
  return apiRequest<OrderRow[]>('/trading/orders', { auth: true })
}

export async function fetchExecutions(): Promise<ExecutionRow[]> {
  return apiRequest<ExecutionRow[]>('/trading/executions', { auth: true })
}

export async function fetchTrades(): Promise<TradeRow[]> {
  return apiRequest<TradeRow[]>('/trading/trades', { auth: true })
}
