import clsx from 'clsx'
import { ThumbsUp, ThumbsDown } from 'lucide-react'
import ReactMarkdown from 'react-markdown'
import { api, ChatMessage as ChatMsg, Citation } from '../api'
import { DenominationTag } from './DenominationTag'
import { RefusalCard } from './RefusalCard'
import { VerificationBadge } from './VerificationBadge'
import { WhyThisAnswer } from './WhyThisAnswer'

type Props = {
  msg: ChatMsg
  onCitationClick: (c: Citation) => void
}

function primaryDenomination(docs: ChatMsg['retrieved_json']): string | null {
  if (!docs?.length) return null
  const commentary = docs.find((d) => d.source_type === 'commentary')
  return commentary?.denomination || docs[0]?.denomination || null
}

export function ChatMessage({ msg, onCitationClick }: Props) {
  const isUser = msg.role === 'user'
  const safety = msg.safety_flags_json
  const refused = !!safety?.refused
  const citations = msg.citations_json || []
  const verifiedCitations = citations.filter((c) => c.verified)
  const traditions = safety?.traditions_compared || null

  if (isUser) {
    return (
      <div className="flex justify-end">
        <div className="max-w-[80%] rounded-2xl bg-ink-700 text-parchment px-4 py-2.5 shadow-soft whitespace-pre-wrap">
          {msg.content}
        </div>
      </div>
    )
  }

  return (
    <div className="flex justify-start">
      <div className="max-w-[85%] w-full">
        {refused ? (
          <RefusalCard content={msg.content} label={safety?.label} />
        ) : (
          <div className="card px-4 py-3">
            {msg.image_url && (
              <img src={msg.image_url} alt="generated" className="mb-3 rounded-lg border border-ink-100 max-h-[480px] object-contain" />
            )}
            <div className="prose prose-sm max-w-none text-ink-800 prose-headings:font-serif prose-headings:text-ink-800 prose-strong:text-ink-800">
              <ReactMarkdown>{msg.content}</ReactMarkdown>
            </div>
            <div className="mt-3 flex flex-wrap items-center gap-2">
              <VerificationBadge verified={msg.citations_verified} nCitations={verifiedCitations.length} />
              {safety?.input_label && safety.input_label !== 'safe' && (
                <span className="rounded-full bg-amber-50 text-amber-800 border border-amber-200 px-2 py-0.5 text-xs">
                  Input flagged: {safety.input_label}
                </span>
              )}
              <DenominationTag denom={primaryDenomination(msg.retrieved_json)} traditions={traditions} />
            </div>
            {citations.length > 0 && (
              <div className="mt-3 flex flex-wrap gap-1.5">
                {citations.map((c, i) => (
                  <button
                    key={i}
                    className={clsx('chip', !c.verified && 'opacity-60 line-through')}
                    onClick={() => c.verified && onCitationClick(c)}
                    title={c.verified ? 'View canonical verse text' : 'This citation could not be verified'}
                  >
                    {c.ref}
                  </button>
                ))}
              </div>
            )}
            <WhyThisAnswer docs={msg.retrieved_json} />
            <div className="mt-3 flex items-center gap-2 text-ink-400">
              <button
                className="hover:text-ink-700"
                onClick={() => api.feedback(msg.id, 1).catch(() => {})}
                title="Helpful"
              >
                <ThumbsUp className="h-3.5 w-3.5" />
              </button>
              <button
                className="hover:text-ink-700"
                onClick={() => api.feedback(msg.id, -1).catch(() => {})}
                title="Not helpful"
              >
                <ThumbsDown className="h-3.5 w-3.5" />
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
