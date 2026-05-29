type Props = {
  denom?: string | null
  traditions?: string[] | null
}

const LABELS: Record<string, string> = {
  catholic: 'Catholic',
  protestant: 'Protestant',
  orthodox: 'Orthodox',
  shared: 'Shared',
}

export function DenominationTag({ denom, traditions }: Props) {
  if (traditions && traditions.length > 1) {
    const names = traditions
      .filter((t) => t && t !== 'none')
      .map((t) => LABELS[t] || t)
      .join(' · ')
    return (
      <span className="inline-flex items-center rounded-full bg-ink-50 px-2.5 py-0.5 text-xs font-medium text-ink-700 border border-ink-100">
        Comparing traditions: {names}
      </span>
    )
  }

  if (!denom || denom === 'none') return null
  const label = `${LABELS[denom] || denom} perspective`
  return (
    <span className="inline-flex items-center rounded-full bg-ink-50 px-2.5 py-0.5 text-xs font-medium text-ink-700 border border-ink-100">
      {label}
    </span>
  )
}
