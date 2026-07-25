# Perguntas de Negocio Suportadas

Este documento lista perguntas que o produto ja deve conseguir responder ou
apoiar com a arquitetura atual, alem de perguntas que fazem sentido como
proximas capacidades do produto.

Use esta lista como roteiro de validacao do Graph RAG, dos algoritmos de grafo
e das futuras integracoes de dados comerciais.

## Perguntas que o produto ja deve suportar bem

- Quais sao os produtos mais vendidos?
- Quais produtos geraram mais faturamento?
- Qual foi o ticket medio dos pedidos?
- Quantos pedidos existem por status?
- Quais clientes mais compraram?
- Quais vendedores venderam mais?
- Quais produtos aparecem juntos nos mesmos pedidos?
- Quais produtos sao similares a um produto especifico?
- Quais produtos devo recomendar para um cliente?
- Quais produtos devo recomendar a partir de um produto?
- Quais clientes estao no segmento `campeoes`, `leais`, `em_risco`, `novos` ou `hibernando`?
- Qual o segmento RFM de um cliente?
- Quais produtos tem maior PageRank na rede de compras?
- Quais comunidades de clientes existem?
- Quais pedidos usaram cupom?
- Qual faturamento por estado ou cidade?
- Quais clientes compraram determinado produto?
- Quais pedidos contem determinado produto?
- Quais produtos tem maior potencial de cross-sell?

## Boas perguntas para testar no `/rag/ask`

- Quais produtos mais aparecem juntos nos pedidos?
- Quais sao os produtos mais importantes na rede de compras?
- Quais clientes parecem estar em risco?
- Quais produtos eu deveria recomendar para o cliente X?
- Quais produtos sao parecidos com o produto Y?
- Qual vendedor teve maior volume de vendas?
- Qual estado concentra mais pedidos?
- Quais pedidos tiveram cupom?
- Quais produtos tem maior valor vendido?
- Explique o comportamento de compra do cliente X.

## Perguntas de "por quê" (explicabilidade)

Perguntas de causa/explicação sobre um cliente específico (não agregada) já
respondem bem hoje via `/rag/ask`, sem precisar de nenhum dado novo — o RFM já
grava os componentes (`rfm_recency_days`, `rfm_frequency`, `rfm_monetary`) por
trás de cada `rfm_segment`, e a rota LOCAL já expõe esses componentes no
contexto do LLM. Validado ao vivo (2026-07-25) contra uma cliente real
`em_risco` (respostas conferidas manualmente, não é suite automatizada):

- Por que o cliente X está no segmento `em_risco`/`hibernando`/`campeoes`? —
  validado.
- Por que o cliente X parece ter parado de comprar? — validado.
- Explique o comportamento de compra do cliente X. — validado.

Regra prática: pergunta de "por quê" sobre uma entidade nomeada (um cliente
específico) deve cair na rota LOCAL, não GLOBAL — é lá que o contexto com os
componentes RFM já está disponível. Perguntas de "por quê" agregadas (ex:
"por que a categoria X caiu?") continuam exigindo dado novo (série temporal),
ver a seção de perguntas que exigem dados adicionais.

**Atualizado em 2026-07-25**: `rag/retriever.py` (`EXPAND_PRODUCT_CONTEXT`/
`EXPAND_CUSTOMER_CONTEXT`) e `rag/chain.py` passaram a puxar `SIMILAR_TO.score`
e `BOUGHT_WITH.support_count/confidence/lift` para o contexto do LLM — os
mesmos números que `recommend_by_customer`/`recommend_by_product`
(`graph_algorithms/gds.py`) usam, só que agora também acessíveis via
`/rag/ask` em linguagem natural, não só via
`POST /graph-algorithms/recommendations/{product,customer}`. Validado ao vivo:

- Por que o produto Y é comprado junto com o produto Z / por que
  recomendariam comprar os dois juntos? — validado (resposta cita
  support_count/confidence/lift reais).
- Que produto vocês recomendariam para o cliente X (e por quê)? — validado
  (resposta cita o produto complementar real do histórico dela, com
  confidence/lift).
- Por que recomendariam **especificamente o produto Y** (nomeado) para o
  cliente X? — **não confiável ainda**. O contexto do cliente só carrega uma
  fatia limitada e não-determinística (até 8 produtos que ela comprou, até 5
  recomendações) das associações `BOUGHT_WITH` do histórico dela; se o
  produto Y perguntado não cair nessa fatia, o LLM responde "sem dados
  suficientes" mesmo a relação existindo no grafo. Pra essa combinação
  (cliente nomeado + produto nomeado) responder de forma confiável, o
  retriever precisaria de um caminho de expansão dedicado que primeiro ache
  os dois nós e depois verifique a relação `BOUGHT_WITH`/`SIMILAR_TO` entre
  eles diretamente — hoje o retriever só expande "um tipo de entidade por
  vez" (order/product/customer isolados), não pares.

Achado durante a validação, corrigido de graça: a busca lexical de fallback
(usada quando não há embeddings gerados, como é o caso deste dataset — sem
`/embeddings/run` os índices vetoriais nem existem) também tinha o mesmo bug
de duplicação e ranking fraco em `LEXICAL_SEARCH_PRODUCTS`
(`rag/retriever.py`) que já tinha sido corrigido em `LEXICAL_SEARCH_CUSTOMERS`
— sem isso, perguntas sobre um produto específico podiam não achar o produto
certo antes mesmo de chegar na parte de explicabilidade.

## Perguntas que o produto deve suportar em breve

- Quais produtos tem alta procura mas baixa conversao?
- Quais produtos vendem bem juntos por categoria?
- Quais SKUs podem acabar em estoque nos proximos dias?
- Quais produtos estao com queda de demanda?
- Quais clientes tem maior chance de comprar novamente?
- Quais clientes estao prestes a churnar?
- Qual promocao gerou venda incremental real?
- Quais produtos deveriam entrar em campanha?
- Qual combinacao de produtos forma um bom kit?
- Quais produtos substituem outro quando falta estoque?
- Quais clientes deveriam receber cupom?
- Qual faixa de preco performa melhor por categoria?
- Quais produtos tem margem alta e boa chance de venda?
- Quais recomendacoes devo esconder por falta de estoque?
- Quais categorias estao crescendo ao longo do tempo?

## Perguntas que exigem dados adicionais

| Pergunta | Dados necessarios |
| --- | --- |
| Qual produto tem melhor margem? | Custo, margem ou lucro por produto/SKU. |
| Qual produto converte mais? | Sessoes, visualizacoes, add-to-cart e pedidos. |
| Qual produto vai romper estoque? | Estoque atual, estoque historico e venda por periodo. |
| Qual campanha trouxe mais resultado? | Dados de campanha, canal, custo e atribuicao de venda. |
| Qual cliente vai churnar? | Historico suficiente de compras por cliente. |
| Qual preco ideal? | Historico de preco, promocao, demanda e estoque. |

## Como usar esta lista

1. Primeiro valide as perguntas suportadas hoje contra dados pequenos.
2. Depois rode `POST /orders/graph-sync` e `POST /graph-algorithms/run` antes
   de testar recomendacoes, RFM, PageRank e produtos comprados juntos.
3. Use `/embeddings/run` apenas quando quiser melhorar busca semantica; ele nao
   deve ser requisito para as perguntas estruturadas.
4. Se uma pergunta nao responder bem, classifique se o problema e:
   - falta de dado;
   - falta de algoritmo;
   - falha na modelagem do grafo;
   - falha no prompt/roteamento do RAG.

## Prioridade recomendada

1. Garantir respostas boas para vendas, faturamento, clientes e produtos.
2. Validar recomendacoes por produto e por cliente.
3. Melhorar explicabilidade de cross-sell com support, confidence e lift.
4. Integrar estoque para perguntas de ruptura e disponibilidade.
5. Integrar trafego/conversao para perguntas de performance de funil.
6. Integrar custo/margem para ranking comercial real.
