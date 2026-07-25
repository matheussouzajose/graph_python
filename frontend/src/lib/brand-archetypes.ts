import type { BrandArchetype } from '@/types/api'

// Rótulos e resumo em pt-BR dos 12 arquétipos junguianos de marca — ver
// docs/arquetipos-de-marca.md para o framework completo e o questionário de
// diagnóstico usado para chegar num primary/secondary.
export const BRAND_ARCHETYPES: { value: BrandArchetype; label: string; hint: string }[] = [
  { value: 'innocent', label: 'Inocente', hint: 'Otimismo, simplicidade, honestidade' },
  { value: 'explorer', label: 'Explorador', hint: 'Liberdade, descoberta, autenticidade' },
  { value: 'sage', label: 'Sábio', hint: 'Verdade, conhecimento, análise' },
  { value: 'hero', label: 'Herói', hint: 'Coragem, superação, prova de valor' },
  { value: 'outlaw', label: 'Fora-da-lei', hint: 'Ruptura, disrupção, quebra de regras' },
  { value: 'magician', label: 'Mago', hint: 'Transformação, visão, tornar sonhos reais' },
  { value: 'everyman', label: 'Cara Comum', hint: 'Pertencimento, proximidade, sem pretensão' },
  { value: 'jester', label: 'Bobo da Corte', hint: 'Diversão, humor, leveza' },
  { value: 'lover', label: 'Amante', hint: 'Paixão, intimidade, desejo' },
  { value: 'ruler', label: 'Governante', hint: 'Controle, autoridade, excelência' },
  { value: 'creator', label: 'Criador', hint: 'Inovação, expressão, originalidade' },
  { value: 'caregiver', label: 'Cuidador', hint: 'Cuidado, proteção, generosidade' },
]

const LABEL_BY_VALUE = new Map(BRAND_ARCHETYPES.map((archetype) => [archetype.value, archetype.label]))

export function archetypeLabel(value: string | null | undefined): string {
  if (!value) return '—'
  return LABEL_BY_VALUE.get(value as BrandArchetype) ?? value
}
