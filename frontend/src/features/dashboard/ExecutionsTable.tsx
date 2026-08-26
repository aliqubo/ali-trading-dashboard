import type { ExecutionRow } from '../../api/trading'
import { formatDateTime, formatMoney, formatQuantity, symbolLabel } from './format'

export function ExecutionsTable({ executions }: { executions: ExecutionRow[] }) {
  return (
    <section className="dashboard-section">
      <h2>Recent executions</h2>
      {executions.length === 0 ? (
        <p className="empty-state">No executions yet.</p>
      ) : (
        <table>
          <thead>
            <tr>
              <th>Symbol</th>
              <th>Price</th>
              <th>Quantity</th>
              <th>Fee</th>
              <th>Liquidity</th>
              <th>Executed at</th>
            </tr>
          </thead>
          <tbody>
            {executions.map((execution) => (
              <tr key={execution.id}>
                <td>{symbolLabel(execution.symbol)}</td>
                <td>{formatMoney(execution.exec_price)}</td>
                <td>{formatQuantity(execution.exec_quantity)}</td>
                <td>
                  {formatMoney(execution.fee)}
                  {execution.fee_currency ? ` ${execution.fee_currency}` : ''}
                </td>
                <td>{execution.liquidity}</td>
                <td>{formatDateTime(execution.executed_at)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </section>
  )
}
