import type { Activity, Message, Ticket, TicketAction, TicketStatus } from './data/inbox'
import type { DemoSettings } from './data/workspace'

export type OverviewMetrics = { total: number; active: number; ai: number; awaiting_human: number; resolved: number; handover_ids: string[]; historical_volume_available: false }
type ApiMessage = Omit<Message, 'time'> & { created_at: string }
type ApiActivity = Omit<Activity, 'time' | 'input'> & { created_at: string; conversation_id: string; input: Record<string, string> | null }
export type ApiConversation = Omit<Ticket, 'status' | 'handling' | 'updated' | 'updatedAt' | 'createdAt' | 'messages' | 'activity'> & {
  status: 'open' | 'in_progress' | 'resolved'; handling_mode: 'ai' | 'human' | 'awaiting_human'
  created_at: string; updated_at: string; messages: ApiMessage[]; activity: ApiActivity[]
}

const statusLabels = { open: 'Open', in_progress: 'In progress', resolved: 'Resolved' } as const
const handlingLabels = { ai: 'AI handling', human: 'You are handling', awaiting_human: 'Needs handover' } as const
const statuses: Record<TicketStatus, ApiConversation['status']> = { Open: 'open', 'In progress': 'in_progress', Resolved: 'resolved' }
const formatTime = (value: string) => new Date(value).toLocaleTimeString('en-GB', { hour: '2-digit', minute: '2-digit' })

export function toTicket(value: ApiConversation): Ticket {
  if (!(value.status in statusLabels) || !(value.handling_mode in handlingLabels)) throw new Error('The API returned an unsupported conversation state. Refresh after updating both servers.')
  return {
    ...value, status: statusLabels[value.status], handling: handlingLabels[value.handling_mode],
    updated: formatTime(value.updated_at), updatedAt: value.updated_at, createdAt: value.created_at,
    messages: value.messages.map((message) => ({ ...message, time: formatTime(message.created_at) })),
    activity: value.activity.map((event) => ({ ...event, time: formatTime(event.created_at), input: event.input ?? undefined })),
  }
}

class ApiError extends Error {
  readonly status: number
  constructor(message: string, status: number) { super(message); this.status = status }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const controller = new AbortController()
  const timer = window.setTimeout(() => controller.abort(), 20000)
  try {
    const response = await fetch(`/api${path}`, { ...init, signal: controller.signal, cache: 'no-store' })
    if (!response.ok) {
      const data = await response.json().catch(() => null)
      const detail = typeof data?.detail === 'string' ? data.detail : response.status === 422 ? 'Some fields are invalid. Check your input and try again.' : `Request failed (HTTP ${response.status}). Check the backend and try again.`
      throw new ApiError(detail, response.status)
    }
    return await response.json() as T
  } catch (error) {
    if (error instanceof ApiError) throw error
    throw new Error('Could not reach the backend or the request timed out. Your input is kept. Check port 8000, then retry the same action safely.')
  } finally { window.clearTimeout(timer) }
}

// Retain the key after uncertain network/server failure. Repeating the same
// action uses the original key until acknowledged, preventing duplicate writes.
const pendingKeys = new Map<string, string>()
async function write<T>(path: string, method: string, body?: unknown, preferredKey?: string) {
  const signature = JSON.stringify([path, method, body ?? null])
  const key = pendingKeys.get(signature) ?? preferredKey ?? crypto.randomUUID()
  pendingKeys.set(signature, key)
  try {
    const result = await request<T>(path, { method, headers: { 'Content-Type': 'application/json', 'Idempotency-Key': key }, ...(body === undefined ? {} : { body: JSON.stringify(body) }) })
    pendingKeys.delete(signature)
    return result
  } catch (error) {
    if (error instanceof ApiError && error.status < 500) pendingKeys.delete(signature)
    throw error
  }
}

export const api = {
  conversations: async () => (await request<ApiConversation[]>('/conversations')).map(toTicket),
  conversation: async (id: string) => toTicket(await request<ApiConversation>(`/conversations/${encodeURIComponent(id)}`)),
  overview: () => request<OverviewMetrics>('/overview'),
  settings: () => request<DemoSettings>('/settings'),
  saveSettings: (settings: DemoSettings) => write<DemoSettings>('/settings', 'PUT', settings),
  action: async (id: string, action: TicketAction) => {
    const base = `/conversations/${encodeURIComponent(id)}`
    if (action.type === 'message') return toTicket(await write<ApiConversation>(`${base}/messages`, 'POST', { kind: action.kind, text: action.text }, action.id))
    if (action.type === 'status') return toTicket(await write<ApiConversation>(`${base}/status`, 'PATCH', { status: statuses[action.status] }, action.id))
    return toTicket(await write<ApiConversation>(`${base}/${action.type === 'customer-message' ? 'simulate-customer' : action.type}`, 'POST', undefined, action.id))
  },
}
