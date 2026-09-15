import type { Ticket } from '../data/inbox'
import { formatMoney } from '../data/inbox'
import { Icon } from './Icon'

export function CustomerDetails({ ticket }: { ticket: Ticket }) {
  const { customer, order } = ticket
  return (
    <div className="customer-details">
      <section className="detail-section">
        <p className="section-label">Customer</p>
        <div className="customer-profile"><span className={`avatar avatar--large avatar--${customer.initials.toLowerCase()}`}>{customer.initials}</span><div><h3>{customer.name}</h3><span className="muted">{customer.tier}</span></div></div>
        <dl className="customer-fields"><div><dt>Email</dt><dd>{customer.email}</dd></div><div><dt>Location</dt><dd>{customer.location}</dd></div><div><dt>Customer since</dt><dd>{customer.since}</dd></div></dl>
      </section>
      <section className="detail-section">
        <div className="order-heading"><Icon name="box" size={18} /><h3>Order {order.id}</h3></div><p className="muted">Placed {order.placed} · USD</p>
        <div className="order-items">{order.items.map((item) => <div className="order-item" key={item.name}><div><strong>{item.name}</strong><p>{item.variant}</p></div><span>{formatMoney(item.amount)}</span></div>)}<div className="order-total"><span>Total paid</span><strong>{formatMoney(order.items.reduce((sum, item) => sum + item.amount, 0))}</strong></div></div>
        <div className="delivery-state"><span className="section-label">Delivery</span><strong>{order.delivery}</strong><span>{order.tracking}</span></div>
        <ol className="timeline">{order.timeline.map((step, index) => <li key={step.label} className={index === order.timeline.length - 1 ? 'is-latest' : ''}><strong>{step.label}</strong><span>{step.detail}</span></li>)}</ol>
      </section>
      <p className="details-footnote">Sample customer and order information.<br />No store or carrier is connected.</p>
    </div>
  )
}
