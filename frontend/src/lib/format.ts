import { formatDistanceToNow, format as formatDateFns } from 'date-fns'
import { ptBR } from 'date-fns/locale'

const currencyFormatter = new Intl.NumberFormat('pt-BR', {
  style: 'currency',
  currency: 'BRL',
})

const numberFormatter = new Intl.NumberFormat('pt-BR')

export function formatCurrency(value: number | null | undefined): string {
  return currencyFormatter.format(value ?? 0)
}

export function formatNumber(value: number | null | undefined): string {
  return numberFormatter.format(value ?? 0)
}

export function formatPercent(value: number | null | undefined, digits = 1): string {
  if (value === null || value === undefined) return '—'
  return `${(value * 100).toFixed(digits)}%`
}

export function formatDecimal(value: number | null | undefined, digits = 3): string {
  if (value === null || value === undefined) return '—'
  return value.toFixed(digits)
}

export function formatRelativeTime(value: string | null | undefined): string {
  if (!value) return 'Nunca'
  try {
    return formatDistanceToNow(new Date(value), { addSuffix: true, locale: ptBR })
  } catch {
    return '—'
  }
}

export function formatDateTime(value: string | null | undefined): string {
  if (!value) return '—'
  try {
    return formatDateFns(new Date(value), "dd/MM/yyyy 'às' HH:mm", { locale: ptBR })
  } catch {
    return '—'
  }
}
