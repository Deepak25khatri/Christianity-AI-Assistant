import clsx from 'clsx'
import { ShieldCheck } from 'lucide-react'

type Props = { verified: 'full' | 'partial' | 'none' | null | undefined; nCitations: number }

/** Demo-facing: only show a positive badge when citations are fully verified. */
export function VerificationBadge({ verified, nCitations }: Props) {
  if (verified !== 'full' || nCitations === 0) {
    return null
  }
  return (
    <span
      className={clsx(
        'inline-flex items-center gap-1.5 rounded-full border px-2.5 py-0.5 text-xs font-medium',
        'bg-green-50 text-green-800 border-green-200',
      )}
    >
      <ShieldCheck className="h-3.5 w-3.5" />
      {`Scripture citations verified (${nCitations})`}
    </span>
  )
}
