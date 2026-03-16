import { cn } from '@/lib/utils'
import type { SignalValue } from '@/types'

const variants: Record<SignalValue, string> = {
  BULLISH: 'badge-bullish',
  BEARISH: 'badge-bearish',
  NEUTRAL: 'badge-neutral',
  MIXED:   'badge-mixed',
}

export function SignalBadge({
  value, className,
}: { value: SignalValue; className?: string }) {
  return (
    <span className={cn(variants[value], className)}>
      {value === 'BULLISH' ? '▲' : value === 'BEARISH' ? '▼' : '●'} {value}
    </span>
  )
}
