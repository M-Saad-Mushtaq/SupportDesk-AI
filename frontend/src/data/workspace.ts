import type { Source, Ticket } from './inbox.ts'

export function handlingLabel(ticket: Ticket) {
  if (ticket.status === 'Resolved') return 'Inactive · Resolved'
  return ticket.handling === 'You are handling' ? 'Human handling' : ticket.handling === 'Needs handover' ? 'Awaiting human attention' : 'AI handling'
}

export function getTicketSources(ticket: Ticket): Source[] {
  return [...new Map(ticket.messages.flatMap((message) => message.sources ?? []).map((source) => [`${source.title}:${source.section}`, source])).values()]
}

export const weekDays = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'] as const
export const tones = ['Warm and professional', 'Concise and direct', 'Friendly and casual'] as const
export const timezones = ['America/New_York', 'America/Los_Angeles', 'Europe/London', 'Asia/Karachi', 'UTC'] as const
export type DemoSettings = {
  company: string; email: string; timezone: string; days: string[]; start: string; end: string
  tone: typeof tones[number]; escalateDamage: boolean; escalateDelivery: boolean; escalateOnRequest: boolean
}
export const defaultSettings: DemoSettings = {
  company: 'LuxeWear', email: 'support@example.com', timezone: 'America/New_York',
  days: ['Mon', 'Tue', 'Wed', 'Thu', 'Fri'], start: '09:00', end: '17:00',
  tone: 'Warm and professional', escalateDamage: true, escalateDelivery: true, escalateOnRequest: true,
}

export function validateSettings(value: unknown): value is DemoSettings {
  if (typeof value !== 'object' || value === null) return false
  const item = value as Record<string, unknown>
  return typeof item.company === 'string' && item.company.trim().length > 0 && item.company.length <= 80 &&
    typeof item.email === 'string' && item.email.length <= 120 && /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(item.email) &&
    typeof item.timezone === 'string' && timezones.some((zone) => zone === item.timezone) &&
    Array.isArray(item.days) && item.days.length > 0 && item.days.every((day) => weekDays.some((allowed) => allowed === day)) &&
    new Set(item.days).size === item.days.length &&
    typeof item.start === 'string' && /^(?:[01]\d|2[0-3]):[0-5]\d$/.test(item.start) &&
    typeof item.end === 'string' && /^(?:[01]\d|2[0-3]):[0-5]\d$/.test(item.end) && item.start < item.end &&
    tones.some((tone) => tone === item.tone) &&
    typeof item.escalateDamage === 'boolean' && typeof item.escalateDelivery === 'boolean' && typeof item.escalateOnRequest === 'boolean'
}

export const toneExamples: Record<DemoSettings['tone'], string> = {
  'Warm and professional': 'Thanks for reaching out. I’m sorry your order is delayed. Let me review the delivery options with you.',
  'Concise and direct': 'Your order is delayed. I’ll check the latest delivery estimate and available options.',
  'Friendly and casual': 'Hi there! Sorry your order is taking longer than expected. Let’s see how we can help.',
}
