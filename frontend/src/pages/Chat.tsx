import { useEffect, useMemo, useRef, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { Plus, Send, Settings as SettingsIcon, Image as ImageIcon, MessageSquare } from 'lucide-react'
import { api, ChatMessage as ChatMsg, Citation, Conversation, SafetyFlags, streamUrl } from '../api'
import { ChatMessage } from '../components/ChatMessage'
import { VerseDrawer } from '../components/VerseDrawer'
import { ImagePanel } from '../components/ImagePanel'
import { useAuth } from '../store'

type NodeEvent = { node?: string; latency_ms?: number; [k: string]: any }

export default function Chat() {
  const { conversationId } = useParams()
  const navigate = useNavigate()
  const user = useAuth((s) => s.user)
  const [conversations, setConversations] = useState<Conversation[]>([])
  const [messages, setMessages] = useState<ChatMsg[]>([])
  const [input, setInput] = useState('')
  const [streaming, setStreaming] = useState(false)
  const [streamText, setStreamText] = useState('')
  const [streamError, setStreamError] = useState<string | null>(null)
  const [streamImage, setStreamImage] = useState<string | null>(null)
  const [activeNodes, setActiveNodes] = useState<NodeEvent[]>([])
  const [drawer, setDrawer] = useState<Citation | null>(null)
  const [tab, setTab] = useState<'chat' | 'image'>('chat')
  const scrollRef = useRef<HTMLDivElement>(null)
  const streamingConvRef = useRef<string | null>(null)

  const activeConvId = conversationId
  const denomLabel = useMemo(() => user?.denomination_pref || 'none', [user])

  async function refreshConversations() {
    try {
      const list = await api.listConversations()
      setConversations(list)
    } catch (err) {
      console.error(err)
    }
  }

  async function loadMessages(id: string) {
    if (streamingConvRef.current === id) return
    try {
      const msgs = await api.listMessages(id)
      setMessages(msgs)
    } catch {
      setMessages([])
    }
  }

  useEffect(() => {
    refreshConversations()
  }, [])

  useEffect(() => {
    if (activeConvId) loadMessages(activeConvId)
    else setMessages([])
  }, [activeConvId])

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: 'smooth' })
  }, [messages, streamText, streamError])

  const newConversation = async () => {
    const c = await api.createConversation()
    setConversations((cs) => [c, ...cs])
    navigate(`/chat/${c.id}`)
  }

  const finishStream = async (convId: string) => {
    streamingConvRef.current = null
    setStreaming(false)
    setStreamText('')
    setStreamImage(null)
    setActiveNodes([])
    await loadMessages(convId)
    refreshConversations()
  }

  const sendSync = async (convId: string, userText: string) => {
    try {
      setStreamError(null)
      setStreaming(true)
      streamingConvRef.current = convId
      await api.sendMessage(convId, userText)
      await finishStream(convId)
    } catch (err: any) {
      setStreamError(err?.message || 'Failed to get a response. Run `make ingest` if this is a fresh install.')
      streamingConvRef.current = null
      setStreaming(false)
    }
  }

  const send = async () => {
    if (!input.trim() || !user || streaming) return
    let convId = activeConvId
    if (!convId) {
      const c = await api.createConversation()
      convId = c.id
      setConversations((cs) => [c, ...cs])
      navigate(`/chat/${c.id}`)
    }
    const userText = input.trim()
    streamingConvRef.current = convId!
    setMessages((m) => [
      ...m,
      {
        id: -Date.now(),
        role: 'user',
        content: userText,
        citations_json: null,
        safety_flags_json: null,
        retrieved_json: null,
        citations_verified: null,
        image_url: null,
        created_at: new Date().toISOString(),
      } as ChatMsg,
    ])
    setInput('')
    setStreaming(true)
    setStreamText('')
    setStreamError(null)
    setStreamImage(null)
    setActiveNodes([])

    let gotTokens = false
    let finished = false

    const es = new EventSource(streamUrl(convId!, userText, user.token))

    const cleanup = () => {
      if (!finished) {
        finished = true
        es.close()
      }
    }

    es.addEventListener('node', (e: MessageEvent) => {
      try {
        setActiveNodes((n) => [...n, JSON.parse(e.data)])
      } catch {}
    })
    es.addEventListener('token', (e: MessageEvent) => {
      try {
        gotTokens = true
        setStreamText((t) => t + JSON.parse(e.data).text)
      } catch {}
    })
    es.addEventListener('image', (e: MessageEvent) => {
      try {
        setStreamImage(JSON.parse(e.data).url)
      } catch {}
    })
    es.addEventListener('stream_error', async (e: MessageEvent) => {
      cleanup()
      try {
        const data = JSON.parse(e.data)
        setStreamError(data.error || 'Something went wrong while generating a reply.')
      } catch {
        setStreamError('Something went wrong while generating a reply.')
      }
      await sendSync(convId!, userText)
    })
    es.addEventListener('done', async () => {
      cleanup()
      await finishStream(convId!)
    })
    es.onerror = async () => {
      if (finished) return
      cleanup()
      if (!gotTokens) {
        setStreamError('Connection lost — retrying without streaming...')
        await sendSync(convId!, userText)
      } else {
        await finishStream(convId!)
      }
    }
  }

  return (
    <div className="min-h-screen flex">
      <aside className="w-72 border-r border-ink-100 bg-white/70 backdrop-blur-sm flex flex-col">
        <div className="p-4 border-b border-ink-100 flex items-center justify-between">
          <Link to="/chat" className="font-serif text-xl text-ink-800">Christianity AI</Link>
          <Link to="/settings" className="btn-ghost p-1.5"><SettingsIcon className="h-4 w-4" /></Link>
        </div>
        <button className="btn-primary m-3" onClick={newConversation}><Plus className="h-4 w-4" /> New chat</button>
        <div className="flex-1 overflow-y-auto px-2 pb-4">
          {conversations.length === 0 && <p className="text-xs text-ink-400 px-2">No conversations yet.</p>}
          {conversations.map((c) => (
            <Link
              key={c.id}
              to={`/chat/${c.id}`}
              className={`block rounded-md px-3 py-2 text-sm hover:bg-ink-50 ${c.id === activeConvId ? 'bg-ink-50 text-ink-800 font-medium' : 'text-ink-600'}`}
            >
              <div className="truncate">{c.title}</div>
            </Link>
          ))}
        </div>
        <div className="border-t border-ink-100 p-3 text-xs text-ink-400">
          <div className="truncate">{user?.email}</div>
          <div className="mt-1">Tradition: <span className="font-medium text-ink-700 capitalize">{denomLabel}</span></div>
        </div>
      </aside>

      <main className="flex-1 flex flex-col min-h-0">
        <div className="border-b border-ink-100 px-6 py-3 flex items-center gap-2 bg-white">
          <button
            className={`btn-ghost ${tab === 'chat' ? 'bg-ink-50 text-ink-800' : ''}`}
            onClick={() => setTab('chat')}
          >
            <MessageSquare className="h-4 w-4" /> Chat
          </button>
          <button
            className={`btn-ghost ${tab === 'image' ? 'bg-ink-50 text-ink-800' : ''}`}
            onClick={() => setTab('image')}
          >
            <ImageIcon className="h-4 w-4" /> Image
          </button>
        </div>

        {tab === 'image' ? (
          <div className="p-6 overflow-y-auto"><ImagePanel /></div>
        ) : (
          <>
            <div ref={scrollRef} className="flex-1 overflow-y-auto px-6 py-6 space-y-4 min-h-0">
              {messages.length === 0 && !streaming && (
                <div className="text-center text-ink-400 mt-24">
                  <div className="font-serif text-3xl text-ink-600 mb-2">Ask. Reflect. Listen.</div>
                  <p className="text-sm max-w-md mx-auto">
                    Every Bible citation is verified against a canonical text store. Contested theology shows multiple traditions. Refusals come as pastoral notes, not red errors.
                  </p>
                </div>
              )}
              {messages.map((m) => (
                <ChatMessage key={m.id} msg={m} onCitationClick={setDrawer} />
              ))}
              {streaming && (
                <div className="card px-4 py-3 max-w-[85%]">
                  {activeNodes.length > 0 && (
                    <div className="mb-2 text-xs text-ink-400">
                      <span className="font-medium">Pipeline:</span>{' '}
                      {activeNodes.map((n, i) => (
                        <span key={i} className="mr-2">
                          {n.node}{n.latency_ms != null ? ` (${n.latency_ms}ms)` : ''}
                          {i < activeNodes.length - 1 ? ' \u2192' : ''}
                        </span>
                      ))}
                    </div>
                  )}
                  {streamImage && (
                    <img src={streamImage} alt="generated" className="mb-3 rounded-lg border border-ink-100 max-h-[480px] object-contain" />
                  )}
                  <div className="whitespace-pre-wrap text-ink-800 text-sm">
                    {streamText || (streamError ? '' : 'Thinking...')}
                  </div>
                </div>
              )}
              {streamError && !streaming && (
                <div className="rounded-md border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-800 max-w-[85%]">
                  {streamError}
                </div>
              )}
            </div>
            <div className="border-t border-ink-100 bg-white p-4">
              <form
                onSubmit={(e) => { e.preventDefault(); send() }}
                className="flex items-end gap-2 max-w-3xl mx-auto"
              >
                <textarea
                  className="input min-h-[44px] max-h-40 resize-none"
                  placeholder="Ask a question, request a reflection, or describe an image..."
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter' && !e.shiftKey) {
                      e.preventDefault()
                      send()
                    }
                  }}
                />
                <button className="btn-primary" type="submit" disabled={streaming || !input.trim()}>
                  <Send className="h-4 w-4" />
                </button>
              </form>
            </div>
          </>
        )}
      </main>

      <VerseDrawer citation={drawer} onClose={() => setDrawer(null)} />
    </div>
  )
}
