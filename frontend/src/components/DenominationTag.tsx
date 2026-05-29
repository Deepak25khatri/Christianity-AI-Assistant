type Props = { denom?: string | null }

const LABELS: Record<string, string> = {
  catholic: 'Catholic perspective',
  protestant: 'Protestant perspective',
  orthodox: 'Orthodox perspective',
  shared: 'Shared Christian teaching',
}

export function DenominationTag({ denom }: Props) {
  if (!denom || denom === 'none') return null
  const label = LABELS[denom] || denom
  return (
    <span className="inline-flex items-center rounded-full bg-ink-50 px-2.5 py-0.5 text-xs font-medium text-ink-700 border border-ink-100">
      {label}
    </span>
  )
}
