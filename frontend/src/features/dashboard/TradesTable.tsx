import type { TradeRow } from '../../api/trading'
import { formatDateTime, formatMoney, formatQuantity, pnlClass, symbolLabel } from './format'

export function TradesTable({ trades }: { trades: TradeRow[] }) {
  return (
    <section className="dashboard-section">
      <h2>Recent trades</h2>
      {trades.length === 0 ? (
        <p className="empty-state">No closed trades yet.</p>
      ) : (
        <table>
          <thead>
            <tr>
              <th>Symbol</th>
              <th>Side</th>
              <th>Quantity</th>
              <th>Entry</th>
              <th>Exit</th>
              <th>Net PnL</th>
              <th>Return %</th>
              <th>Closed at</th>
            </tr>
          </thead>
          <tbody>
            {trades.map((trade) => (
              <tr key={trade.id}>
                <td>{symbolLabel(trade.symbol)}</td>
                <td>{trade.side}</td>
                <td>{formatQuantity(trade.quantity)}</td>
                <td>{formatMoney(trade.entry_price)}</td>
                <td>{formatMoney(trade.exit_price)}</td>
                <td className={pnlClass(trade.net_pnl)}>{formatMoney(trade.net_pnl)}</td>
                <td className={pnlClass(trade.return_pct)}>
                  {trade.return_pct === null ? '—' : `${trade.return_pct.toFixed(2)}%`}
                </td>
                <td>{formatDateTime(trade.exit_at)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </section>
  )
}
