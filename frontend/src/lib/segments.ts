export const SEGMENT_LABELS: Record<string, string> = {
  campeoes: 'Campeões',
  leais: 'Leais',
  novos: 'Novos',
  em_risco: 'Em risco',
  hibernando: 'Hibernando',
  potencial: 'Potencial',
}

export const SEGMENT_COLORS: Record<
  string,
  {
    chart: string
    badge: string
    text: string
    soft: string
  }
> = {
  campeoes: {
    chart: '#059669',
    badge:
      'border-emerald-200 bg-emerald-50 text-emerald-700 dark:border-emerald-900 dark:bg-emerald-950 dark:text-emerald-400',
    text: 'text-emerald-700 dark:text-emerald-400',
    soft: 'bg-emerald-50 dark:bg-emerald-950/40',
  },
  leais: {
    chart: '#2563eb',
    badge:
      'border-blue-200 bg-blue-50 text-blue-700 dark:border-blue-900 dark:bg-blue-950 dark:text-blue-400',
    text: 'text-blue-700 dark:text-blue-400',
    soft: 'bg-blue-50 dark:bg-blue-950/40',
  },
  novos: {
    chart: '#7c3aed',
    badge:
      'border-violet-200 bg-violet-50 text-violet-700 dark:border-violet-900 dark:bg-violet-950 dark:text-violet-400',
    text: 'text-violet-700 dark:text-violet-400',
    soft: 'bg-violet-50 dark:bg-violet-950/40',
  },
  em_risco: {
    chart: '#d97706',
    badge:
      'border-amber-200 bg-amber-50 text-amber-700 dark:border-amber-900 dark:bg-amber-950 dark:text-amber-400',
    text: 'text-amber-700 dark:text-amber-400',
    soft: 'bg-amber-50 dark:bg-amber-950/40',
  },
  hibernando: {
    chart: '#64748b',
    badge:
      'border-slate-200 bg-slate-100 text-slate-700 dark:border-slate-800 dark:bg-slate-900 dark:text-slate-400',
    text: 'text-slate-700 dark:text-slate-400',
    soft: 'bg-slate-100 dark:bg-slate-900/60',
  },
  potencial: {
    chart: '#0891b2',
    badge:
      'border-cyan-200 bg-cyan-50 text-cyan-700 dark:border-cyan-900 dark:bg-cyan-950 dark:text-cyan-400',
    text: 'text-cyan-700 dark:text-cyan-400',
    soft: 'bg-cyan-50 dark:bg-cyan-950/40',
  },
}

export function getSegmentLabel(segment: string | null | undefined) {
  if (!segment) return '—'
  return SEGMENT_LABELS[segment] ?? segment
}

export function getSegmentColor(segment: string | null | undefined) {
  return segment ? SEGMENT_COLORS[segment] : undefined
}
