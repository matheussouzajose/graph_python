# Algoritmos de E-commerce: Status e Roadmap

Este documento resume quais algoritmos e tecnicas de e-commerce ja existem no
produto, quais estao parcialmente cobertos e quais devem ser priorizados.

O produto atual e uma API de inteligencia comercial baseada em grafo: pedidos
vindos de ERP sao persistidos no Postgres, projetados no Neo4j e consultados por
Graph RAG, algoritmos de grafo e embeddings.

## Algoritmos ja implementados

| Algoritmo / tecnica | Status | Uso atual |
| --- | --- | --- |
| KNN / produtos similares | Implementado | Gera relacionamento `SIMILAR_TO` entre produtos. |
| FastRP structural embedding | Implementado | Cria embedding estrutural baseado na rede de compras. |
| Co-occurrence graph | Implementado como base | Produtos conectados indiretamente por pedidos via `Order` -> `Product`. |
| Product similarity hibrido | Implementado | Combina sinal estrutural do FastRP com embedding textual OpenAI. |
| PageRank global de produto | Implementado | Calcula importancia estrutural do produto na rede de compras. |
| Personalized PageRank | Implementado | Recomenda/rankeia produtos a partir de produtos-semente. |
| Leiden / comunidades | Implementado | Segmenta clientes por estrutura de compra no grafo. |
| RFM | Implementado v1 | Segmenta clientes por recencia, frequencia e valor monetario. |
| Association Rules | Implementado v1 | Cria relacoes `BOUGHT_WITH` com suporte, confianca e lift. |
| Recomendacao por produto | Implementado v1 | Combina `SIMILAR_TO`, `BOUGHT_WITH` e PageRank. |
| Recomendacao por cliente | Implementado v1 | Usa historico de compras, RFM, `SIMILAR_TO` e `BOUGHT_WITH`. |
| Vector similarity | Implementado | Busca semantica em `Order` e `Product` via indices vetoriais Neo4j. |
| Hybrid Graph RAG | Implementado | Busca vetorial + expansao estrutural no grafo. |
| Cypher QA para analise agregada | Implementado | LLM gera Cypher para perguntas globais/agregadas. |

## Algoritmos parcialmente cobertos

| Algoritmo / tecnica | Status | Lacuna |
| --- | --- | --- |
| Item-to-item recommendation | Parcial | Produto e cliente existem; ainda falta recomendacao por carrinho/pedido e filtros comerciais mais ricos. |
| Market Basket Analysis | Parcial | Support, confidence e lift existem; ainda falta analise por categoria, periodo e variantes. |
| Segmentacao de clientes | Parcial | Leiden e RFM existem; ainda falta tela/API de exploracao de segmentos e comparativos entre segmentos. |
| Busca e ranking comercial | Parcial | Existe busca semantica, mas falta ranking por sinais comerciais como estoque, margem, conversao, preco e popularidade. |

## Algoritmos ainda nao implementados

| Algoritmo / tecnica | Prioridade | Justificativa |
| --- | --- | --- |
| Collaborative Filtering classico | Media | Util quando houver bastante historico cliente-produto. |
| Matrix Factorization | Media | Escala bem para recomendacao quando o volume crescer. |
| Learning to Rank | Media/Alta | Importante para busca de catalogo quando existirem cliques, conversao, estoque e sinais comerciais. |
| BM25 / busca lexical | Media | Complementa embeddings em buscas por codigo, SKU, nome exato e termos literais. |
| Demand Forecasting por SKU | Alta futura | Relevante para planejamento, mas depende de historico temporal consistente. |
| Stockout Prediction | Alta futura | Muito valioso para e-commerce, mas exige estoque e venda por periodo. |
| Churn Prediction | Media | Pode ser construido depois de RFM e historico de recompra. |
| CLV Prediction | Media | Depende de historico confiavel por cliente. |
| Elasticidade de preco | Media futura | Exige historico de preco, promocao e demanda. |
| Uplift Modeling | Baixa agora | Exige dados de campanhas e grupos de controle. |
| Fraude / Anomaly Detection | Baixa/Media | Prioridade depende de o produto atacar risco/pagamento. |

## Roadmap recomendado

### 1. RFM de clientes

Implementar segmentacao por:

- recencia: ha quantos dias o cliente comprou;
- frequencia: quantas compras realizou;
- valor monetario: quanto comprou no periodo.

Saida recomendada:

- score RFM por cliente;
- segmento textual: `campeoes`, `leais`, `em risco`, `novos`, `hibernando`;
- endpoint para listar clientes por segmento;
- propriedades gravadas no Neo4j para enriquecer o Graph RAG.

Motivo: e o menor esforco com maior valor comercial imediato. Tambem melhora a
explicabilidade da segmentacao ja feita por Leiden.

### 2. Association Rules com support, confidence e lift

Gerar regras do tipo:

- se o cliente compra produto A, tende a comprar produto B;
- se compra categoria X, tende a comprar categoria Y;
- produtos frequentemente vendidos juntos.

Metricas minimas:

- suporte: frequencia da combinacao no total de pedidos;
- confianca: probabilidade de comprar B dado que comprou A;
- lift: quanto a relacao A -> B e mais forte que o acaso.

Motivo: complementa o grafo com regras simples de explicar para operacao
comercial, vendas e marketing.

### 3. API de recomendacao comercial

Criar endpoints orientados a uso real:

- recomendacao por cliente;
- recomendacao por carrinho;
- recomendacao por produto;
- recomendacao por pedido.

Combinar sinais:

- Personalized PageRank;
- `SIMILAR_TO`;
- regras de associacao;
- PageRank global;
- disponibilidade de estoque, quando existir;
- filtros de preco/categoria, quando existirem.

Motivo: o produto ja tem os algoritmos de base, mas ainda precisa de uma camada
de produto que entregue recomendacoes prontas para consumo.

### 4. Ranking comercial

Criar um score final configuravel para ordenar produtos em recomendacoes e
busca:

```text
score_final =
  similaridade * peso_similaridade +
  pagerank * peso_popularidade +
  lift * peso_cesta +
  disponibilidade * peso_estoque +
  margem * peso_margem
```

Inicialmente, usar apenas sinais disponiveis hoje:

- similaridade;
- PageRank;
- coocorrencia;
- preco/promocao.

Depois, adicionar:

- estoque;
- margem;
- conversao;
- sazonalidade.

Motivo: recomendacao pura por similaridade pode sugerir produtos pouco
vendaveis, sem estoque ou ruins comercialmente. O ranking precisa refletir o
objetivo do negocio.

### 5. Previsao de demanda e ruptura

Priorizar quando houver dados confiaveis de estoque e historico temporal por
SKU.

Saidas desejadas:

- previsao de venda por SKU;
- data estimada de ruptura;
- alertas de reposicao;
- produtos com demanda crescente ou queda.

Motivo: alto valor para operacao, mas depende mais da qualidade e completude dos
dados do que os algoritmos anteriores.

## Ordem pratica de implementacao

1. Refinar thresholds do RFM quando houver mais historico.
2. Criar recomendacao por carrinho e por pedido.
3. Criar score comercial configuravel.
4. Adicionar busca lexical/BM25 ou estrategia equivalente para SKU, codigo e nome exato.
5. Adicionar filtros comerciais: estoque, categoria, preco, margem e disponibilidade.
6. Expandir association rules por categoria, periodo e variante.
7. Evoluir para previsao de demanda e ruptura quando estoque historico estiver disponivel.

## Endpoints adicionados

- `POST /graph-algorithms/rfm/run`: calcula RFM de clientes.
- `POST /graph-algorithms/association-rules/run`: calcula `BOUGHT_WITH` com support, confidence e lift.
- `POST /graph-algorithms/recommendations/product`: recomenda produtos a partir de um produto.
- `POST /graph-algorithms/recommendations/customer`: recomenda produtos a partir de um cliente.

Embeddings continuam existindo em `/embeddings/run`, mas nao sao obrigatorios
para RFM, association rules ou recomendacoes estruturadas. Quando embeddings
existirem, eles melhoram a similaridade `SIMILAR_TO`; quando nao existirem, o
KNN usa o sinal estrutural do FastRP.

## Observacao tecnica

O produto ja possui uma base forte de Graph Intelligence. A principal lacuna
nao e falta de algoritmos sofisticados, mas sim a camada de produto que traduz
esses sinais em decisoes comerciais explicaveis:

- por que este produto foi recomendado;
- para qual cliente ou contexto ele faz sentido;
- qual confianca existe nessa recomendacao;
- qual impacto comercial esperado;
- quais filtros operacionais devem ser respeitados.

Essa camada deve ser priorizada antes de adicionar modelos mais complexos.
