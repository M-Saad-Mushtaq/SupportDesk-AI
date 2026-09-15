export type TicketStatus = 'Open' | 'In progress' | 'Resolved'
export type Handling = 'Needs handover' | 'AI handling' | 'You are handling'
export type MessageKind = 'customer' | 'ai' | 'reply' | 'note'
export type Source = { title: string; section: string; excerpt: string }
export type Message = {
  id: string
  kind: MessageKind
  text: string
  time: string
  sources?: Source[]
}
export type Activity = {
  id: string
  title: string
  time: string
  input?: Record<string, string>
  result: string
}
export type Ticket = {
  id: string
  subject: string
  preview: string
  updated: string
  updatedAt: string
  createdAt: string
  channel: 'Email' | 'Web chat'
  priority: 'Urgent' | 'Normal' | 'Low' | 'High'
  status: TicketStatus
  handling: Handling
  customer: { name: string; initials: string; email: string; location: string; since: string; tier: string }
  order: {
    id: string
    placed: string
    items: { name: string; variant: string; amount: number }[]
    delivery: string
    tracking: string
    timeline: { label: string; detail: string }[]
  }
  messages: Message[]
  activity: Activity[]
}

export type InboxFilter = 'All' | 'Needs handover' | 'AI handling' | 'Open' | 'In progress' | 'Resolved'
export const inboxFilters: InboxFilter[] = ['All', 'Needs handover', 'AI handling', 'Open', 'In progress', 'Resolved']
export const ticketStatuses: TicketStatus[] = ['Open', 'In progress', 'Resolved']

export function filterTickets(tickets: Ticket[], query: string, filter: InboxFilter) {
  const search = query.trim().toLocaleLowerCase()
  return tickets.filter((ticket) => {
    const matchesFilter = filter === 'All' || ticket.status === filter ||
      (ticket.status !== 'Resolved' && ticket.handling === filter)
    const haystack = [ticket.customer.name, ticket.customer.email, ticket.id, ticket.order.id, ticket.subject, ticket.preview].join(' ').toLocaleLowerCase()
    return matchesFilter && haystack.includes(search)
  })
}

export type TicketAction =
  | { type: 'takeover'; time: string; id: string }
  | { type: 'resume'; time: string; id: string }
  | { type: 'customer-message'; time: string; id: string }
  | { type: 'status'; status: TicketStatus; time: string; id: string }
  | { type: 'message'; kind: 'reply' | 'note'; text: string; time: string; id: string }

export function formatMoney(amount: number) {
  return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(amount)
}
