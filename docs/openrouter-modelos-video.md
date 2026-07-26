# Modelos de vídeo disponíveis no OpenRouter

Lista de modelos `image_to_video` que o `OpenRouterVideoProvider`
(`app/features/agents/video_providers/openrouter.py`) consegue rodar sem nenhuma mudança de
código — basta trocar o campo `model` do agente. Levantada direto em `GET
https://openrouter.ai/api/v1/videos/models` (dados podem mudar; essa é uma foto de 2026-07-26).

Todos aceitam imagem de referência via `input_references`, exceto o `openai/sora-2-pro`, que via
OpenRouter só aceita texto (pra usar Sora com imagem, é o `video_provider="openai"` — Sora direto
pela OpenAI — que já existe no projeto).

Ordenado do mais barato pro mais caro (preço por segundo de vídeo gerado):

| Modelo (`model` no agente) | Duração | Resoluções | Preço/s (aprox) | Observação |
|---|---|---|---|---|
| `bytedance/seedance-1-5-pro` | 4-12s | 480p-1080p | cobra por token, bem barato | gera áudio junto |
| `bytedance/seedance-2.0-fast` | 4-15s | 480p/720p | cobra por token, bem barato | prioriza velocidade |
| `x-ai/grok-imagine-video` | 1-15s | 480p/720p | ~$0,05-0,07/s | Grok, rápido |
| `minimax/hailuo-2.3` | 6 ou 10s | 1080p | ~$0,08/s | sem áudio |
| `alibaba/happyhorse-1.1` | 3-15s | 720p/1080p | ~$0,10-0,13/s | aceita várias imagens de referência |
| `alibaba/happyhorse-1.0` | 3-15s | 720p/1080p | ~$0,10-0,17/s | versão anterior |
| `google/veo-3.1-lite` | 4/6/8s | 720p/1080p | $0,03-0,08/s | **default atual do agente** |
| `kwaivgi/kling-v3.0-std` | 3-15s | 720p | ~$0,08-0,13/s (c/ áudio) | first+last frame |
| `alibaba/wan-2.6` | 5 ou 10s | 720p/1080p | ~$0,10-0,15/s | |
| `x-ai/grok-imagine-video-1.5` | 1-15s | 480p-1080p | ~$0,08-0,25/s | versão nova do Grok |
| `google/veo-3.1-fast` | 4/6/8s | 720p-4K | $0,08-0,30/s | meio-termo Veo |
| `alibaba/wan-2.7` | 2-10s | 720p/1080p | ~$0,10/s | first+last+multi-referência |
| `kwaivgi/kling-video-o1` | 5 ou 10s | 720p | ~$0,11/s | |
| `kwaivgi/kling-v3.0-pro` | 3-15s | 720p | ~$0,11-0,17/s (c/ áudio) | tier premium do Kling |
| `bytedance/seedance-2.0` | 4-15s | 480p-4K | cobra por token | mais caro que o "fast" |
| `google/veo-3.1` | 4/6/8s | 720p-4K | $0,20-0,60/s | custou ~$3,20 num teste 1080p/8s |
| `openai/sora-2-pro` | 4-20s | 720p/1080p | $0,30-0,50/s | sem imagem via OpenRouter |

## Recomendação

Pra continuar barato mas testar algo diferente do Veo Lite: `bytedance/seedance-1-5-pro` ou
`alibaba/happyhorse-1.1` — ambos mais em conta que o `veo-3.1-lite` e o Seedance em particular é
descrito pelo fabricante como bom em preservar a identidade do personagem/produto entre frames, o
que pode ajudar com problemas de fidelidade à imagem original.

## Como trocar

No painel de Agentes, editar o agente `image_to_video` e colocar o `model` desejado (campo texto
livre em "Configurações avançadas") — `video_size`/`video_seconds` também precisam bater com o que
o modelo escolhido suporta (ver coluna "Resoluções"/"Duração" acima).
