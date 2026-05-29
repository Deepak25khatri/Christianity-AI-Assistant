import { useAuth } from './store'

export const API_BASE = '/api'

async function call<T>(path: string, init: RequestInit = {}): Promise<T> {
  const token = useAuth.getState().user?.token
  const headers: HeadersInit = {
    'Content-Type': 'application/json',
    ...(init.headers || {}),
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
  }
  const res = await fetch(`${API_BASE}${path}`, { ...init, headers })
  if (!res.ok) {
    const body = await res.text()
    throw new Error(`${res.status}: ${body}`)
  }
  if (res.status === 204) return undefined as unknown as T
  return res.json() as Promise<T>
}

export type Denomination = 'catholic' | 'protestant' | 'orthodox' | 'none'

export type Conversation = {
  id: string
  title: string
  summary: string | null
  created_at: string
}

export type Citation = {
  ref: string
  book: string
  chapter: number
  verse_start: number
  verse_end: number
  exists: boolean
  canonical_text: string | null
  quoted_text: string | null
  text_match_ratio: number | null
  verified: boolean
}

export type SafetyFlags = {
  refused?: boolean
  label?: string
  reason?: string | null
  citations_verified?: 'full' | 'partial' | 'none'
  input_label?: string
  output_blocked?: boolean
}

export type RetrievedDoc = {
  text: string
  score: number
  source_type: string
  book?: string | null
  chapter?: number | null
  verse_start?: number | null
  verse_end?: number | null
  translation?: string | null
  denomination?: string | null
  title?: string | null
}

export type ChatMessage = {
  id: number
  role: 'user' | 'assistant' | 'system'
  content: string
  citations_json: Citation[] | null
  safety_flags_json: SafetyFlags | null
  retrieved_json: RetrievedDoc[] | null
  citations_verified: 'full' | 'partial' | 'none' | null
  image_url: string | null
  created_at: string
}

export const api = {
  register: (email: string, password: string, denom?: Denomination) =>
    call<any>('/auth/register', { method: 'POST', body: JSON.stringify({ email, password, denomination_pref: denom }) }),
  login: (email: string, password: string) =>
    call<any>('/auth/login', { method: 'POST', body: JSON.stringify({ email, password }) }),
  updateDenom: (denomination_pref: Denomination) =>
    call<any>('/auth/me/denomination', { method: 'PATCH', body: JSON.stringify({ denomination_pref }) }),
  listConversations: () => call<Conversation[]>('/conversations'),
  createConversation: (title?: string) =>
    call<Conversation>('/conversations', { method: 'POST', body: JSON.stringify({ title }) }),
  listMessages: (id: string) => call<ChatMessage[]>(`/conversations/${id}/messages`),
  sendMessage: (id: string, content: string) =>
    call<ChatMessage>(`/conversations/${id}/messages`, {
      method: 'POST',
      body: JSON.stringify({ content }),
    }),
  deleteConversation: (id: string) =>
    call<{ deleted: string }>(`/conversations/${id}`, { method: 'DELETE' }),
  generateImage: (prompt: string) =>
    call<{ image_url: string | null; refused_reason: string | null; sanitized_prompt: string | null }>(
      '/images',
      { method: 'POST', body: JSON.stringify({ prompt }) },
    ),
  lookupVerse: (book: string, chapter: number, vStart: number, vEnd?: number, translation = 'WEB') => {
    const q = new URLSearchParams({ book, chapter: String(chapter), verse_start: String(vStart), translation })
    if (vEnd) q.set('verse_end', String(vEnd))
    return call<{
      book: string; chapter: number; verse_start: number; verse_end: number
      translation: string; text: string; exists: boolean
    }>(`/verses?${q.toString()}`)
  },
  feedback: (message_id: number, rating: 1 | -1, note?: string) =>
    call<{ ok: true; id: number }>('/feedback', { method: 'POST', body: JSON.stringify({ message_id, rating, note }) }),
}

export function streamUrl(conversationId: string, content: string, token: string) {
  const q = new URLSearchParams({ content, token })
  return `${API_BASE}/conversations/${conversationId}/stream?${q.toString()}`
}
