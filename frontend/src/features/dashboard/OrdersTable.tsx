import type { OrderRow } from '../../api/trading'
import { formatDateTime, formatMoney, formatQuantity, symbolLabel } from './format'

export function OrdersTable({ orders }: { orders: OrderRow[] }) {
  return (
    <section className="dashboard-section">
      <h2>Orders</h2>
      {orders.length === 0 ? (
        <p className="empty-state">No orders yet.</p>
      ) : (
        <table>
          <thead>
            <tr>
              <th>Symbol</th>
              <th>Side</th>
              <th>Type</th>
              <th>Quantity</th>
              <th>Filled</th>
              <th>Price</th>
              <th>Avg fill</th>
              <th>Status</th>
              <th>Submitted</th>
            </tr>
          </thead>
          <tbody>
            {orders.map((order) => (
              <tr key={order.id}>
                <td>{symbolLabel(order.symbol)}</td>
                <td>{order.side}</td>
                <td>{order.order_type}</td>
                <td>{formatQuantity(order.quantity)}</td>
                <td>{formatQuantity(order.filled_quantity)}</td>
                <td>{formatMoney(order.price)}</td>
                <td>{formatMoney(order.avg_fill_price)}</td>
                <td>{order.status}</td>
                <td>{formatDateTime(order.submitted_at)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </section>
  )
}
