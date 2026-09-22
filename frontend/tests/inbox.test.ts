import assert from 'node:assert/strict'
import test from 'node:test'
import { readFileSync } from 'node:fs'
import { api, toTicket } from '../src/api.ts'
import type { ApiConversation } from '../src/api.ts'
import { defaultSettings, validateSettings } from '../src/data/workspace.ts'

const fixture = JSON.parse(readFileSync(new URL('../../backend/seed_data.json', import.meta.url), 'utf8')).tickets[0]
const stored = {
  ...fixture, status: 'open', handling_mode: 'awaiting_human', created_at: '2025-10-27T10:41:00Z', updated_at: '2025-10-27T10:45:00Z',
  messages: fixture.messages.map((message: { time: string }) => ({ ...message, created_at: `2025-10-27T${message.time}:00Z`, sources: [] })),
  activity: fixture.activity.map((event: { time: string }) => ({ ...event, conversation_id: fixture.id, created_at: `2025-10-27T${event.time}:00Z`, input: null })),
} as ApiConversation

test('API status and handling map independently into the existing UI', () => {
  assert.equal(toTicket(stored).status, 'Open')
  assert.equal(toTicket(stored).handling, 'Needs handover')
  const human = toTicket({ ...stored, status: 'in_progress', handling_mode: 'human' })
  assert.equal(human.status, 'In progress')
  assert.equal(human.handling, 'You are handling')
  const resolved = toTicket({ ...stored, status: 'resolved', handling_mode: 'ai' })
  assert.equal(resolved.status, 'Resolved')
  assert.equal(resolved.handling, 'AI handling')
  assert.equal(resolved.messages.length, stored.messages.length)
  assert.equal(resolved.updatedAt, stored.updated_at)
})

test('uncertain network failures keep the same retry key; confirmed writes release it', async (t) => {
  const originalFetch = globalThis.fetch
  Object.defineProperty(globalThis, 'window', { value: globalThis, configurable: true })
  t.after(() => { globalThis.fetch = originalFetch })
  const keys: string[] = []
  globalThis.fetch = async (_input, init) => {
    keys.push(new Headers(init?.headers).get('Idempotency-Key') ?? '')
    if (keys.length === 1) throw new Error('Connection lost after commit')
    return new Response(JSON.stringify(stored), { status: 200, headers: { 'Content-Type': 'application/json' } })
  }
  const message = { type: 'message', kind: 'note', text: 'Retry test', id: 'first-request-key', time: '12:00' } as const
  await assert.rejects(api.action(fixture.id, message), /retry the same action safely/)
  await api.action(fixture.id, { ...message, id: 'new-click-key' })
  await api.action(fixture.id, { ...message, id: 'new-intent-key' })
  assert.deepEqual(keys, ['first-request-key', 'first-request-key', 'new-intent-key'])
})

test('demo settings validate same-day hours and supported preferences', () => {
  assert.ok(validateSettings(defaultSettings))
  for (const input of [null, {}, { ...defaultSettings, days: [] }, { ...defaultSettings, start: '19:00', end: '09:00' }, { ...defaultSettings, email: 'invalid' }]) assert.equal(validateSettings(input), false)
})


test('agent test-message retries keep their key and preserve provider/citation metadata', async (t) => {
  const originalFetch = globalThis.fetch
  Object.defineProperty(globalThis, 'window', { value: globalThis, configurable: true })
  t.after(() => { globalThis.fetch = originalFetch })
  const calls: { path: string; key: string }[] = []
  const message = { ...stored.messages[0], kind: 'ai', origin: 'gemini', sources: [{ source_id: 'doc:1:passage:2', document_id: '1', title: 'Returns', section: 'Page 2', page: 2, excerpt: 'Returns accepted.', quote: 'Returns accepted.' }] }
  const response = { ...stored, messages: [...stored.messages, message] }
  globalThis.fetch = async (input, init) => {
    calls.push({ path: String(input), key: new Headers(init?.headers).get('Idempotency-Key') ?? '' })
    if (calls.length === 1) throw new Error('Lost after commit')
    return new Response(JSON.stringify({ conversation: response, run_id: 'saved-run' }), { status: 200 })
  }
  const action = { type: 'test-customer', text: 'Policy question', time: '12:00', id: 'customer-intent-key' } as const
  await assert.rejects(api.action(fixture.id, action))
  const saved = await api.action(fixture.id, { ...action, id: 'retry-click-key' })
  assert.equal(calls[0].key, calls[1].key)
  assert.ok(calls[1].path.endsWith('/customer-messages'))
  assert.equal(saved.messages.at(-1)?.origin, 'gemini')
  assert.equal(saved.messages.at(-1)?.sources?.[0].source_id, 'doc:1:passage:2')
})
