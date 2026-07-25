# Arquétipos de Marca

Este documento define o framework de arquétipo de marca usado para enriquecer
os futuros agentes de geração de conteúdo (Oráculo Marketing, agentes de
roteiro/vídeo, etc.) com a voz e a personalidade de cada empresa-cliente. O
arquétipo é dado de domínio por `company` (multi-tenant) — cada empresa que
usa o Oráculo define o próprio arquétipo, não existe um arquétipo único do
produto.

Implementação: `app/features/brand_archetype/` (feature slice completa —
`orm.py`, `schemas.py`, `repository.py`, `service.py`, `router.py`), exposta
em `POST/GET /brand-archetype-profiles` e `GET/PATCH/DELETE
/brand-archetype-profiles/{profile_id}`. Um perfil por `company` (FK
`company_id` única).

## O framework

Baseado nos arquétipos junguianos aplicados a marca por Margaret Mark & Carol
Pearson (*The Hero and the Outlaw*). 12 arquétipos, organizados em 4
motivações centrais:

| Motivação | Arquétipos |
| --- | --- |
| Estabilidade/controle | Governante, Criador, Cuidador |
| Pertencimento/prazer | Cara Comum, Bobo da Corte, Amante |
| Risco/domínio | Herói, Fora-da-lei, Mago |
| Independência/realização | Inocente, Explorador, Sábio |

Cada arquétipo carrega: desejo central, medo, estratégia e tom de voz
típicos. Na prática usa-se **1 arquétipo primário + 1 secundário
complementar** — raramente mais que isso, senão a voz de marca fica
inconsistente.

## Estrutura do perfil (`brand_archetype_profile`)

O rótulo do arquétipo sozinho ("a marca é Sábia") não é algo que um agente de
geração de conteúdo consiga consumir diretamente. Por isso o perfil guarda o
arquétipo como classificação de referência, mais camadas operacionais que os
agentes de fato usam como contexto de prompt:

```yaml
brand_archetype_profile:
  company_id: <fk, único>

  # classificação
  primary_archetype: sage        # um dos 12 (ver enum BrandArchetype)
  secondary_archetype: creator   # opcional, complementa o primário
  archetype_scores:              # tally bruto do questionário de diagnóstico
    sage: 4
    creator: 3
    ...

  # substância psicológica (herdada do arquétipo, ajustável por marca)
  core_desire: "ajudar o cliente a tomar a melhor decisão de compra"
  fear: "parecer genérico, prometer o que não entrega"
  strategy: "educar antes de vender"

  # o que os agentes de conteúdo realmente consomem
  voice:
    tone: ["direto", "confiante", "acolhedor"]
    sentence_style: "frases curtas, sem jargão técnico"
    vocabulary_prefer: ["conforto", "caimento perfeito", "praticidade"]
    vocabulary_avoid: ["imperdível", "corre que acaba", "clichê de urgência"]

  audience:
    who: "mulheres 25-40, classe B, compra por indicação"
    speaks_to_them_as: "amiga que entende de moda, não vendedora"

  messaging_pillars:
    - "qualidade que dura"
    - "caimento para o corpo real"

  guardrails:
    do: ["citar benefício concreto", "usar prova social quando houver dado"]
    dont: ["prometer desconto que não existe", "tom apelativo"]

  reference_examples:
    - "Não é sobre seguir tendência. É sobre vestir o que combina com você."
```

`voice`, `audience`, `guardrails`, `messaging_pillars` e `reference_examples`
são guardados como JSONB/array — são lidos como blob de contexto para prompt,
não filtrados por campo interno em query.

## Questionário de diagnóstico

12 perguntas, cada uma com 4 alternativas — cada alternativa representa um
dos 4 grupos motivacionais acima, então toda pergunta força uma escolha entre
os 4 polos. No total do questionário, cada um dos 12 arquétipos aparece
exatamente 4 vezes, distribuído — pontuação equilibrada sem precisar de 12
opções por pergunta.

**Pontuação**: 1 ponto para o arquétipo de cada resposta escolhida. Soma no
final; o de maior pontuação é o `primary_archetype`, o segundo é o
`secondary_archetype`. Empate → pergunta de desempate ou decisão manual.

> Nota de implementação futura: quando isso virar UI (onboarding), embaralhar
> a ordem das alternativas em cada pergunta — aqui elas seguem sempre a ordem
> Independência/Domínio/Pertencimento/Estrutura só para ficar legível e
> auditável. O cálculo de `archetype_scores`/`primary_archetype`/
> `secondary_archetype` a partir das respostas do diagnóstico ainda não está
> implementado no backend — hoje o perfil é criado/atualizado diretamente via
> API com esses campos já definidos.

**1. Um cliente reclama publicamente nas redes sobre um produto que
decepcionou. Qual a reação mais natural da marca?**
- (Inocente) Pede desculpas com simplicidade e honestidade, sem enrolar, e corrige o erro.
- (Herói) Age rápido e mostra, com prova concreta, que resolveu — a crise vira exemplo de compromisso.
- (Cara Comum) Responde de forma próxima e humana, como quem também erra às vezes.
- (Governante) Responde com controle e formalidade, reforçando padrão de qualidade — a marca não perde a compostura.

**2. Como a marca comunica o lançamento de um produto novo?**
- (Explorador) Convida o cliente a descobrir algo novo antes de todo mundo.
- (Fora-da-lei) Rompe com o que o mercado está fazendo — o produto existe pra desafiar o óbvio.
- (Bobo da Corte) Lança com leveza e humor, sem se levar tão a sério.
- (Criador) Mostra o processo criativo por trás — como o produto foi imaginado e feito.

**3. Qual é a rotina de conteúdo mais natural pra marca?**
- (Sábio) Educa — cada post ensina algo, traz dado ou contexto.
- (Mago) Mostra transformação — o antes e depois que o produto proporciona.
- (Amante) Aposta em estética, sensorialidade, desejo — o produto é objeto de afeto.
- (Cuidador) Foca em cuidado — dicas práticas pra vida do cliente ficar melhor.

**4. Um concorrente lança uma promoção agressiva. Como a marca reage?**
- (Herói) Não entra na guerra de preço — reforça por que vale o esforço extra de escolher a marca.
- (Cara Comum) Mantém o preço justo de sempre, sem drama — "somos os mesmos de sempre".
- (Governante) Reforça autoridade e qualidade superior — não compete no mesmo terreno.
- (Inocente) Mantém a transparência de sempre, sem entrar em disputa.

**5. Como a marca escolheria um rosto/embaixador?**
- (Fora-da-lei) Alguém que incomoda o consenso, que tem opinião própria.
- (Bobo da Corte) Alguém engraçado, espontâneo, que não se leva a sério.
- (Criador) Alguém reconhecido por criar/fazer coisas originais.
- (Explorador) Alguém que vive experiências novas, sem raízes fixas.

**6. Como deveria ser a experiência de pós-compra/unboxing?**
- (Mago) Um momento quase de encantamento — surpresa bem pensada.
- (Amante) Detalhes sensoriais e íntimos — parece um presente, não uma entrega.
- (Cuidador) Conforto e cuidado prático — tudo pensado pra facilitar a vida de quem recebeu.
- (Sábio) Um material que explica o "porquê" do produto, educando o uso.

**7. Qual filosofia de preço combina mais com a marca?**
- (Cara Comum) Preço justo e acessível, sem se diferenciar "de cima pra baixo".
- (Governante) Preço alto e deliberado — reforça exclusividade e status.
- (Inocente) Preço simples e transparente, sem letra miúda.
- (Herói) Preço reflete o esforço/qualidade — "você paga pelo que vale o desafio de fazer bem".

**8. Como a marca se posiciona diante de uma tendência de mercado?**
- (Bobo da Corte) Brinca com a tendência, sem levar a sério demais.
- (Criador) Reinterpreta a tendência à sua própria maneira, original.
- (Explorador) Testa a tendência antes de todo mundo, por curiosidade.
- (Fora-da-lei) Ignora ou zomba da tendência — segue caminho próprio.

**9. O que a marca mais quer que o cliente sinta no momento da compra?**
- (Amante) Desejo, encantamento — "eu preciso disso".
- (Cuidador) Segurança — "estão cuidando de mim".
- (Sábio) Confiança — "sei exatamente o que estou comprando e por quê".
- (Mago) Possibilidade — "isso pode mudar algo pra mim".

**10. Como a marca fala publicamente sobre um erro/recall?**
- (Governante) Comunicado formal e claro, sem se desculpar em excesso — resolve com autoridade.
- (Inocente) Assume o erro com simplicidade e sinceridade total.
- (Herói) Trata como desafio a ser vencido — mostra o plano de ação.
- (Cara Comum) Fala como fala com um amigo — direto, sem esconder nada.

**11. Qual o tom das redes sociais no dia a dia?**
- (Criador) Bastidor do processo criativo — "como fazemos".
- (Explorador) Descoberta constante — viagens, novidades, testes.
- (Fora-da-lei) Opinião forte, sem medo de polarizar.
- (Bobo da Corte) Memes, humor, interação leve com os seguidores.

**12. O que o cliente deve sentir ao usar/vestir o produto?**
- (Cuidador) Cuidado — "alguém pensou em mim ao fazer isso".
- (Sábio) Segurança — "essa é uma escolha inteligente".
- (Mago) Transformação — "eu me sinto diferente/melhor usando isso".
- (Amante) Desejo — "eu me sinto bonito(a)/desejado(a) usando isso".

## Próximos passos sugeridos (fora do escopo atual)

- Endpoint/serviço que recebe as 12 respostas do diagnóstico e calcula
  `archetype_scores` + `primary_archetype`/`secondary_archetype`
  automaticamente, em vez de o cliente da API montar isso na mão.
- Tela de onboarding no frontend que roda o questionário.
- Consumo do perfil pelos futuros agentes (Oráculo Marketing, agente de
  roteiro/vídeo) como contexto de prompt.
