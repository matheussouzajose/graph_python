import type { AgentOutputAction } from '@/types/api'

// Espelha app/features/agents/schemas.py::AgentOutputAction — cada entrada
// aqui é só rótulo/copy; a ação em si (o que "aplicar" faz de fato) é
// código no backend, registrado em app/features/agents/actions.py. Uma
// ação nova sempre precisa de um handler novo lá + uma entrada nova aqui.
export const AGENT_OUTPUT_ACTIONS: { value: AgentOutputAction; label: string; hint: string }[] = [
  {
    value: 'none',
    label: 'Só mostrar o resultado',
    hint: 'O resultado fica disponível pra copiar/editar, sem nenhuma ação automática.',
  },
  {
    value: 'apply_brand_archetype',
    label: 'Aplicar como arquétipo de marca da empresa',
    hint: 'Cria (ou atualiza, se já existir) o perfil de arquétipo de marca da empresa com o resultado.',
  },
]

export const AGENT_OUTPUT_ACTION_APPLY_LABEL: Record<string, string> = {
  apply_brand_archetype: 'Aplicar como arquétipo de marca',
}

export function outputActionLabel(value: string): string {
  return AGENT_OUTPUT_ACTIONS.find((action) => action.value === value)?.label ?? value
}
