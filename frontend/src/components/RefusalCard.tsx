import { Cross } from 'lucide-react'

type Props = { content: string; label?: string }

export function RefusalCard({ content, label }: Props) {
  return (
    <div className="rounded-xl border border-gold-200 bg-gold-50 px-4 py-3 text-ink-800">
      <div className="flex items-center gap-2 mb-1 text-xs uppercase tracking-wide text-gold-600">
        <Cross className="h-3.5 w-3.5" />
        Pastoral note
        {label && <span className="ml-2 rounded-full bg-white/60 px-2 py-0.5 text-[10px] normal-case">{label}</span>}
      </div>
      <p className="text-sm whitespace-pre-wrap">{content}</p>
    </div>
  )
}
