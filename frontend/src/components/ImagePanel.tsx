import { useState } from 'react'
import { Loader2 } from 'lucide-react'
import { api } from '../api'
import { RefusalCard } from './RefusalCard'

const EXAMPLES = [
  'Stained glass of the Good Shepherd, reverent, no faces',
  'Renaissance-style painting of the Annunciation',
  'Iconography of the Resurrection, traditional Byzantine style',
  'Watercolor of doves descending over a Jordan river scene',
]

export function ImagePanel() {
  const [prompt, setPrompt] = useState('')
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState<{ url: string | null; refused: string | null; sanitized: string | null } | null>(null)

  const submit = async () => {
    if (!prompt.trim()) return
    setLoading(true)
    setResult(null)
    try {
      const r = await api.generateImage(prompt)
      setResult({ url: r.image_url, refused: r.refused_reason, sanitized: r.sanitized_prompt })
    } catch (e: any) {
      setResult({ url: null, refused: e.message || 'Failed', sanitized: null })
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="card p-5">
      <h2 className="text-xl mb-1">Christian image generation</h2>
      <p className="text-sm text-ink-500 mb-4">
        Prompts are rewritten into a reverent, policy-safe form. We won't depict God the Father, use real persons as
        biblical figures, or produce mocking or extremist imagery.
      </p>
      <textarea
        className="input min-h-[80px] mb-2"
        placeholder="Describe a reverent Christian image..."
        value={prompt}
        onChange={(e) => setPrompt(e.target.value)}
      />
      <div className="flex flex-wrap gap-1.5 mb-3">
        {EXAMPLES.map((ex) => (
          <button key={ex} className="chip" onClick={() => setPrompt(ex)} type="button">
            {ex}
          </button>
        ))}
      </div>
      <button className="btn-primary" onClick={submit} disabled={loading}>
        {loading && <Loader2 className="h-4 w-4 animate-spin" />}
        {loading ? 'Generating...' : 'Generate image'}
      </button>
      {result && (
        <div className="mt-4">
          {result.url ? (
            <>
              <img src={result.url} alt="generated" className="rounded-lg border border-ink-100 max-h-[520px] object-contain" />
              {result.sanitized && (
                <p className="mt-2 text-xs text-ink-400">
                  <span className="font-medium">Sanitized prompt used:</span> {result.sanitized}
                </p>
              )}
            </>
          ) : (
            <RefusalCard
              label={result.refused?.includes('API key') ? 'configuration' : 'image_blocked'}
              content={
                result.refused?.includes('API key')
                  ? `${result.refused}\n\nChat and image generation both need a valid OpenAI key.`
                  : `I can't generate that. ${result.refused || ''}\n\nTry rephrasing toward a reverent, traditional Christian art prompt.`
              }
            />
          )}
        </div>
      )}
    </div>
  )
}
