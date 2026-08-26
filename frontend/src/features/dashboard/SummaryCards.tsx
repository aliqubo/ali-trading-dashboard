import type { DashboardSummary } from '../../api/trading'
import { formatMoney } from './format'

export function SummaryCards({ summary }: { summary: DashboardSummary }) {
  const cards = [
    { label: 'Open positions', value: summary.open_positions_count.toString() },
    { label: 'Open orders', value: summary.open_orders_count.toString() },
    {
      label: 'Unrealized PnL',
      value: formatMoney(summary.unrealized_pnl_total),
      tone: summary.unrealized_pnl_total >= 0 ? 'positive' : 'negative',
    },
    { label: 'Closed trades', value: summary.closed_trades_count.toString() },
    {
      label: 'Realized PnL',
      value: formatMoney(summary.realized_pnl_total),
      tone: summary.realized_pnl_total >= 0 ? 'positive' : 'negative',
    },
  ] as const

  return (
    <div className="summary-cards">
      {cards.map((card) => (
        <div className="summary-card" key={card.label}>
          <span className="summary-card-label">{card.label}</span>
          <span className={`summary-card-value ${'tone' in card ? card.tone : ''}`}>
            {card.value}
          </span>
        </div>
      ))}
    </div>
  )
}
