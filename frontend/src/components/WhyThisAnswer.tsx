import { useState } from 'react'
import { ChevronDown, ChevronRight } from 'lucide-react'
import { RetrievedDoc } from '../api'

type Props = { docs: RetrievedDoc[] | null | undefined }

export function WhyThisAnswer({ docs }: Props) {
  const [open, setOpen] = useState(false)
  if (!docs || docs.length === 0) return null
  return (
    <div className="mt-2">
      <button className="inline-flex items-center gap-1 text-xs text-ink-500 hover:text-ink-800" onClick={() => setOpen((o) => !o)}>
        {open ? <ChevronDown className="h-3 w-3" /> : <ChevronRight className="h-3 w-3" />}
        Why this answer? ({docs.length} sources)
      </button>
      {open && (
        <ul className="mt-2 space-y-2">
          {docs.map((d, i) => (
            <li key={i} className="rounded-md border border-ink-100 bg-ink-50 p-3 text-xs text-ink-700">
              <div className="text-[10px] uppercase tracking-wide text-ink-400 mb-1">
                {d.source_type === 'scripture'
                  ? `Scripture - ${d.book} ${d.chapter}:${d.verse_start}-${d.verse_end} (${d.translation})`
                  : `Commentary - ${d.title || ''} (${d.denomination || 'shared'})`}
              </div>
              <div className="line-clamp-4">{d.text}</div>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}
