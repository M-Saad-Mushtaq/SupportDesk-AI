import { request } from './api'

export type DocumentStatus = 'processing' | 'ready' | 'needs_ocr' | 'failed' | 'deleting'
export type StoredDocument = {
  id: string; title: string; filename: string; format: string; size: number; content_hash: string
  status: DocumentStatus; error: string | null; warning: string | null
  created_at: string; updated_at: string; page_count: number; chunk_count: number
}
export type Segment = { text: string; page: number | null; section: string | null }
export type DocumentPreview = StoredDocument & { segments: Segment[] }
export type SearchHit = Segment & { id: number; document_id: string; position: number; title: string; location: string }
export type SearchResults = { query: string; mode: 'fts5' | 'keyword'; match: 'all_terms' | 'partial_terms' | 'none'; results: SearchHit[]; message: string }
export const documentStatusLabels: Record<DocumentStatus, string> = { processing: 'Processing', ready: 'Ready', needs_ocr: 'Requires OCR', failed: 'Failed', deleting: 'Deletion pending' }

export const documentApi = {
  list: () => request<StoredDocument[]>('/documents'),
  preview: (id: string) => request<DocumentPreview>(`/documents/${encodeURIComponent(id)}`),
  search: (query: string) => request<SearchResults>(`/documents/search?q=${encodeURIComponent(query)}`),
  upload: (file: File) => {
    const body = new FormData()
    body.append('file', file)
    return request<{ document: StoredDocument; duplicate: boolean }>('/documents', { method: 'POST', body }, 60000)
  },
  remove: (id: string) => request<{ deleted: boolean }>(`/documents/${encodeURIComponent(id)}`, { method: 'DELETE' }),
}
