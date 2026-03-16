import { clsx, type ClassValue } from 'clsx'
import { twMerge }               from 'tailwind-merge'

export function cn(...inputs: ClassValue[]): string {
  return twMerge(clsx(inputs))
}

export function formatLargeNumber(value: number | null | undefined): string {
  if (value == null) return '—'
  if (value >= 1e12) return `$${(value / 1e12).toFixed(2)}T`
  if (value >= 1e9)  return `$${(value / 1e9).toFixed(2)}B`
  if (value >= 1e6)  return `$${(value / 1e6).toFixed(2)}M`
  return `$${value.toLocaleString()}`
}

export function formatPrice(v: number | null | undefined): string {
  return v != null ? `$${v.toFixed(2)}` : '—'
}

export function formatRatio(v: number | null | undefined, suffix = 'x'): string {
  return v != null ? `${v.toFixed(1)}${suffix}` : '—'
}

export function clamp(value: number, min: number, max: number): number {
  return Math.min(Math.max(value, min), max)
}
