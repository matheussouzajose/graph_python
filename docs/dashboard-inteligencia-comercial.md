# Dashboard de Inteligencia Comercial

Este documento define a direcao recomendada para evoluir o produto para um
dashboard. A ideia nao e criar um BI generico, mas uma camada operacional de
inteligencia comercial em cima do grafo, dos algoritmos e do RAG.

## Posicionamento

Dashboard de inteligencia comercial para e-commerce que transforma pedidos do
ERP em recomendacoes, segmentos de clientes, oportunidades de cross-sell e
respostas analiticas em linguagem natural.

## Principio de Produto

O dashboard deve mostrar estado do negocio, oportunidades e acoes. O RAG deve
ser usado para exploracao livre, nao para carregar os cards principais.

Regra pratica:

- Dashboard: queries deterministicas.
- Assistente: RAG/LangChain.
- Recomendacao: endpoints proprios.
- Alertas: jobs e algoritmos.

## MVP Recomendado

### 1. Home Executiva

Objetivo: responder "como esta o negocio agora?"

Cards principais:

- faturamento total;
- total de pedidos;
- ticket medio;
- clientes compradores;
- produtos vendidos;
- status dos pedidos;
- ultima sincronizacao;
- ultima execucao dos algoritmos.

Acoes:

- sincronizar pedidos;
- projetar pedidos no grafo;
- rodar algoritmos;
- rodar embeddings opcionalmente.

### 2. Produtos

Objetivo: responder "o que vender, recomendar ou promover?"

Blocos:

- produtos mais vendidos;
- produtos com maior faturamento;
- produtos mais importantes no grafo via PageRank;
- produtos comprados juntos;
- recomendacoes por produto;
- explicacao da recomendacao.

Explicacoes desejadas:

- similaridade;
- lift;
- confidence;
- support;
- PageRank;
- sinal de coocorrencia.

Esta deve ser uma das primeiras telas, porque concentra valor comercial direto.

### 3. Clientes

Objetivo: responder "quem merece atencao?"

Blocos:

- distribuicao por segmento RFM;
- clientes campeoes;
- clientes em risco;
- clientes novos;
- detalhe do cliente;
- produtos comprados;
- recomendacoes para o cliente.

Essa tela transforma o produto em ferramenta de acao comercial e CRM leve.

### 4. Recomendacoes

Objetivo: ser uma central de acao.

Funcionalidades:

- escolher um produto e ver recomendacoes;
- escolher um cliente e ver recomendacoes;
- mostrar motivo da recomendacao;
- mostrar score;
- mostrar lift/confidence quando vier de associacao;
- mostrar PageRank quando vier de importancia estrutural.

### 5. Oraculo

Objetivo: exploracao livre.

Funcionalidades:

- input para perguntar em linguagem natural;
- resposta;
- rota usada: `LOCAL` ou `GLOBAL`;
- Cypher gerado;
- fontes;
- historico das ultimas perguntas.

## Arquitetura Recomendada

### Frontend

Opcao recomendada:

- Next.js ou React/Vite;
- layout de dashboard simples;
- tabelas fortes;
- poucos graficos no inicio;
- visual operacional, nao marketing.

Direcao visual:

- denso, claro e escaneavel;
- cards apenas para metricas e itens repetidos;
- tabelas para rankings e recomendacoes;
- filtros simples por periodo, integracao e segmento;
- acoes visiveis para sync e processamento.

### Backend

Criar uma feature nova:

```text
app/features/dashboard/
```

Formato recomendado:

```text
app/features/dashboard/router.py
app/features/dashboard/service.py
app/features/dashboard/schemas.py
```

Inicialmente, as consultas podem ser diretas no Neo4j, porque os dados de
produto, cliente, recomendacao e grafo ja estao projetados la.

## Endpoints MVP

Endpoints determinisiticos para o dashboard:

```text
GET /dashboard/overview
GET /dashboard/products/top-selling
GET /dashboard/products/top-revenue
GET /dashboard/products/top-pagerank
GET /dashboard/products/bought-together
GET /dashboard/customers/rfm-summary
GET /dashboard/customers?segment=campeoes
GET /dashboard/sync-status
```

Endpoints existentes que o dashboard deve reutilizar:

```text
POST /integrations/{id}/sync
POST /orders/graph-sync
POST /graph-algorithms/run
POST /embeddings/run
POST /rag/ask
POST /graph-algorithms/recommendations/product
POST /graph-algorithms/recommendations/customer
```

## Ordem de Construcao

### Fase 1

Construir:

- endpoints `/dashboard/*`;
- Home Executiva;
- Produtos;
- Oraculo.

Motivo: isso ja demonstra o diferencial principal do produto.

### Fase 2

Construir:

- Clientes;
- Recomendacoes;
- filtros por periodo;
- filtros por integracao;
- historico de perguntas do Oraculo.

### Fase 3

Evoluir:

- alertas de oportunidade;
- estoque e ruptura;
- conversao e funil;
- margem e ranking comercial;
- campanhas e publico-alvo.

## Primeiro Recorte Recomendado

Comecar com:

```text
Home + Produtos + Oraculo
```

Depois adicionar:

```text
Clientes + Recomendacoes
```

## Por Que Nao Comecar Com BI Generico

Um dashboard generico tende a virar uma colecao de graficos sem acao clara.
Este produto tem um diferencial melhor:

- grafo comercial;
- recomendacoes;
- explicabilidade;
- RFM;
- produtos comprados juntos;
- perguntas em linguagem natural.

O dashboard deve evidenciar esse diferencial, nao competir com ferramentas de
BI tradicionais.

## Decisoes Que O Dashboard Deve Apoiar

- O que esta vendendo mais?
- O que deve ser recomendado?
- Quais produtos combinam entre si?
- Quais clientes merecem atencao?
- Quais clientes estao em risco?
- Quais produtos sao importantes na rede de compras?
- Quais oportunidades de cross-sell existem?
- O que aconteceu nos pedidos recentemente?
- Que pergunta comercial posso explorar livremente?

## Dados Que Devem Ser Integrados Depois

Para evoluir alem do MVP, integrar:

- estoque atual;
- estoque historico;
- custo/margem;
- trafego;
- visualizacoes;
- add-to-cart;
- campanhas;
- conversao;
- categorias;
- marcas;
- canais de venda.

Esses dados habilitam perguntas mais fortes sobre ruptura, performance,
campanhas, margem e ranking comercial real.
