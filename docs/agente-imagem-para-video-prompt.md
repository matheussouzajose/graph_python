# Exemplo — Agente de Imagem para Vídeo (Sora)

Exemplo de como criar, pelo próprio painel (`/agentes`), um agente que gera
um vídeo de propaganda de verdade a partir da foto de um produto do
catálogo, usando a API de vídeo da OpenAI (Sora). Diferente dos agentes de
texto, este tipo de agente (`kind = Imagem → vídeo`) não conversa — ele
recebe uma imagem selecionada e devolve um arquivo de vídeo.

> Antes de criar: veja `docs/agente-roteiro-video-ecommerce-prompt.md` se o
> que você quer é só o *roteiro* em texto (mais rápido, sem custo de geração
> de vídeo). Use este agente quando quiser o vídeo pronto de fato.

## Passo a passo no painel

1. Abra **Agentes** no menu lateral e clique em **Criar agente**.
2. Em **Tipo de agente**, escolha **Imagem → vídeo**. Esse campo não pode
   ser alterado depois de criado — se errar, crie outro agente.
3. Preencha os campos da tabela abaixo. O campo "Direção criativa base"
   substitui o "system prompt" dos agentes de conversa.
4. Salve. Na execução, você escolhe a imagem direto do catálogo de produtos
   — não precisa fazer upload manual.

## Configuração do formulário

| Campo | Valor |
| --- | --- |
| Nome | `Vídeo de produto` |
| Descrição curta | `Gera um vídeo publicitário curto a partir da foto de um produto` |
| Instruções para quem for usar | ver abaixo |
| Direção criativa base | ver abaixo |
| Formato do vídeo | `Retrato pequeno (720×1280)` — formato vertical, ideal pra Reels/TikTok/Shopee |
| Duração | `8s` (ou `4s` pra testar mais barato) |
| Modelo Sora (avançado) | deixar em branco (usa `sora-2`, o mais barato) |
| Agente ativo | Sim |
| Global | depende — se só uma equipe usa, deixe privado |

**Instruções para quem for usar** (campo do formulário):

```
Escolha a imagem do produto no catálogo e, se quiser, descreva algo
específico pra esse vídeo (ex: "mostrar o caimento em movimento"). Deixe em
branco pra usar a direção criativa padrão do agente. A geração leva alguns
minutos — a tela atualiza sozinha quando o vídeo fica pronto.
```

## Direção criativa base (system prompt)

Este é um prompt já testado e validado nesta conta — adaptado do que já
gerou vídeos reais pra ÓPERA KIDS antes deste agente existir no painel.
Cole no campo **"Direção criativa base"**:

```
Transforme a imagem fornecida em um vídeo publicitário premium para
e-commerce, utilizando exclusivamente o produto da imagem como referência
visual. O produto deve permanecer absolutamente idêntico ao original.
Preserve rigorosamente formato, modelagem, caimento, tecido, textura,
costuras, bordados, estampas, cores, tonalidades, botões, zíperes,
etiquetas, acabamentos, proporções e todos os detalhes visuais. Não
invente, remova ou modifique qualquer característica do produto. A imagem
deve manter aparência de fotografia profissional de catálogo, com
qualidade ultra realista, alta definição, iluminação de estúdio suave,
foco preciso, excelente reprodução de cores e acabamento premium.

Anime apenas a cena, nunca o produto. Utilize movimentos cinematográficos
discretos, como dolly-in lento, leve pan lateral, pequeno efeito de
parallax, micro movimento de câmera e iluminação sutilmente dinâmica para
transmitir profundidade e sofisticação.

Caso exista uma modelo vestindo o produto, preserve integralmente sua
identidade, rosto, corpo, pose, expressão, cabelo e proporções. Permita
apenas movimentos humanos naturais, como respiração, piscar, leve
movimentação dos cabelos e pequenas mudanças de postura. Nunca altere a
aparência da pessoa. Caso o produto esteja sem modelo (flat lay ou
manequim), mantenha-o completamente estático, movimentando apenas a câmera
e a iluminação. Caso existam tecidos leves, permita apenas movimento
natural causado por uma brisa suave, sem alterar o caimento original da
peça.

Utilize composição vertical (9:16), ideal para TikTok, Instagram Reels,
Shopee e marketplaces, mantendo o produto sempre centralizado, totalmente
visível e ocupando a maior parte do enquadramento. O fundo deve permanecer
limpo, elegante e profissional. Caso seja necessário enriquecê-lo, utilize
apenas elementos minimalistas e desfocados que valorizem o produto sem
competir pela atenção.

Não adicionar pessoas, acessórios, joias, bolsas, calçados, móveis,
plantas, objetos decorativos ou qualquer elemento inexistente na imagem
original. Nunca gerar textos, logotipos, marcas d'água, preços, legendas,
banners, promoções, botões, ícones ou elementos gráficos. Evite
completamente deformações, distorções, mudanças de cor, troca de tecido,
alteração de estampa, artefatos visuais, mãos extras, membros duplicados,
cintilação (flickering), baixa resolução, efeito plástico, aparência de
IA, movimentos bruscos ou transições agressivas.

O resultado final deve parecer um vídeo gravado por uma câmera profissional
de publicidade para uma grande marca, transmitindo elegância, qualidade,
sofisticação e confiança, mantendo fidelidade absoluta ao produto
original.
```

## Exemplo de execução

1. Na tela do agente, clique em **Selecionar imagem do catálogo** e busque
   o produto (ex: "Vestido Ana Flávia").
2. Deixe a mensagem em branco ou adicione algo específico, ex:
   `Enfatizar o brilho do tecido jeans com luz natural.`
3. Clique em **Gerar vídeo**. A tela mostra "Gerando vídeo... isso pode
   levar alguns minutos" e atualiza sozinha.
4. Quando pronto, o player aparece direto no resultado.

## Limitações a saber

- **Uma imagem por execução.** A Sora aceita só uma imagem de referência
  por vídeo — não dá pra combinar várias fotos num vídeo só ainda.
- **O vídeo expira em ~48h** no lado da OpenAI. Depois disso o player para
  de carregar — não há re-hospedagem em storage próprio ainda; baixe o
  vídeo (botão do player) se quiser guardar.
- **A API de vídeo da OpenAI (Sora 2) desliga em 24/09/2026**, sem
  substituta anunciada até agora — bom pra validar o fluxo hoje, mas vai
  precisar revisar o provedor antes dessa data.
- Duração máxima hoje é `12s` e o formato precisa ser um dos 4 tamanhos
  fixos da Sora (720×1280, 1280×720, 1024×1792, 1792×1024) — a imagem é
  ajustada automaticamente pra caber, sem distorcer o produto.
