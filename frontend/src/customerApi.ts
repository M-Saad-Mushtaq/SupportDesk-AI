import { request, write } from './api.ts'
export type DemoIdentity = { id: string; name: string }
export type PublicTicket = { id: string; subject: string; order_id: string; status: 'open' | 'in_progress' | 'resolved' }
export type CustomerHome = { customer: DemoIdentity; order_ids: string[]; conversations: PublicTicket[] }
export type PublicConversation = PublicTicket & {
  customer: DemoIdentity; handling_mode: 'ai' | 'human' | 'awaiting_human'
  messages: { id: string; kind: 'customer' | 'ai' | 'reply'; text: string; created_at: string; origin: 'customer' | 'human' | 'ai' | 'mock' | 'sample' }[]
  run: { id: string; status: 'pending' | 'running' | 'completed' | 'failed' | 'cancelled' | 'interrupted'; retry_allowed: boolean; retry_at: string | null; message: string | null } | null
}
const base = (customer: string) => `/demo/customers/${encodeURIComponent(customer)}`
const conversationPath = (customer: string, ticket: string) => `${base(customer)}/conversations/${encodeURIComponent(ticket)}`
export const customerApi = {
  identities: (signal?: AbortSignal) => request<DemoIdentity[]>('/demo/customers', { signal }),
  home: (id: string, signal?: AbortSignal) => request<CustomerHome>(base(id), { signal }),
  conversation: (id: string, ticket: string, signal?: AbortSignal) => request<PublicConversation>(conversationPath(id, ticket), { signal }),
  start: (id: string, order: string) => write<PublicConversation>(`${base(id)}/conversations`, 'POST', { order_id: order }),
  send: (id: string, ticket: string, text: string, key: string) => write<PublicConversation>(`${conversationPath(id, ticket)}/messages`, 'POST', { text }, key),
  retry: (id: string, ticket: string, run: string) => write<PublicConversation>(`${conversationPath(id, ticket)}/runs/${encodeURIComponent(run)}/retry`, 'POST'),
}
