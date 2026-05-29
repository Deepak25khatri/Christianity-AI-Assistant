import clsx from 'clsx'
import { ShieldCheck, ShieldAlert, ShieldX } from 'lucide-react'

type Props = { verified: 'full' | 'partial' | 'none' | null | undefined; nCitations: number }

export function VerificationBadge({ verified, nCitations }: Props) {
  if (!verified || (verified === 'full' && nCitations === 0)) {
    return null
  }
  const cfg =
    verified === 'full'
      ? { icon: ShieldCheck, label: `All ${nCitations} citation${nCitations === 1 ? '' : 's'} verified`, cls: 'bg-green-50 text-green-800 border-green-200' }
      : verified === 'partial'
      ? { icon: ShieldAlert, label: 'Some citations adjusted or removed', cls: 'bg-amber-50 text-amber-800 border-amber-200' }
      : { icon: ShieldX, label: 'No verifiable citations', cls: 'bg-red-50 text-red-800 border-red-200' }
  const Icon = cfg.icon
  return (
    <span className={clsx('inline-flex items-center gap-1.5 rounded-full border px-2.5 py-0.5 text-xs font-medium', cfg.cls)}>
      <Icon className="h-3.5 w-3.5" />
      {cfg.label}
    </span>
  )
}
