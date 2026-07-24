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
