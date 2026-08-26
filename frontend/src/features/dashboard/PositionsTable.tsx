import type { PositionRow } from '../../api/trading'
import { formatMoney, formatQuantity, pnlClass, symbolLabel } from './format'

export function PositionsTable({ positions }: { positions: PositionRow[] }) {
  return (
    <section className="dashboard-section">
      <h2>Positions</h2>
      {positions.length === 0 ? (
        <p className="empty-state">No open positions.</p>
      ) : (
        <table>
          <thead>
            <tr>
              <th>Symbol</th>
              <th>Side</th>
              <th>Quantity</th>
              <th>Avg entry</th>
              <th>Current price</th>
              <th>Unrealized PnL</th>
              <th>Realized PnL</th>
              <th>Status</th>
            </tr>
          </thead>
          <tbody>
            {positions.map((position) => (
              <tr key={position.id}>
                <td>{symbolLabel(position.symbol)}</td>
                <td>{position.side}</td>
                <td>{formatQuantity(position.quantity)}</td>
                <td>{formatMoney(position.avg_entry_price)}</td>
                <td>{formatMoney(position.current_price)}</td>
                <td className={pnlClass(position.unrealized_pnl)}>
                  {formatMoney(position.unrealized_pnl)}
                </td>
                <td className={pnlClass(position.realized_pnl)}>
                  {formatMoney(position.realized_pnl)}
                </td>
                <td>{position.status}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </section>
  )
}
