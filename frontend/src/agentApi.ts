import { request } from './api'
export type AIStatus = { provider: string; model: string; state: 'mock' | 'not_configured' | 'unverified' | 'connected' | 'error'; verified_at: string | null; error: string | null }
export type AgentTool = { id: string; name: string; arguments: Record<string, unknown>; result: Record<string, unknown>; created_at: string; attempt: number }
export type AgentRun = {
  id: string; conversation_id: string; customer_message_id: string; response_message_id: string | null
  provider: string; model: string; status: 'pending' | 'running' | 'completed' | 'failed' | 'cancelled' | 'interrupted'
  attempt: number; created_at: string; started_at: string | null; finished_at: string | null
  retry_at: string | null; error: string | null; error_code: string | null; duration_ms: number | null
  request_count: number; tool_count: number; usage: { input_tokens?: number; output_tokens?: number; total_tokens?: number }
  tools: AgentTool[]; attempts: Record<string, unknown>[]
}
export const agentApi = {
  status: () => request<AIStatus>('/ai/status'),
  runs: () => request<AgentRun[]>('/agent/runs'),
}
export function providerLabel(status: AIStatus | null) {
  if (!status) return 'Provider status unavailable'
  if (status.state === 'mock') return 'Mock simulation'
  if (status.state === 'connected') return 'Gemini request verified'
  if (status.state === 'unverified') return 'Gemini not yet verified'
  return status.state === 'not_configured' ? 'AI configuration needed' : 'Provider needs attention'
}
