"""One-off migration: re-chave nós existentes de Product/SKU/Color/Size/
Seller/Customer no Neo4j pra usar IDs compostos por empresa
(`f"{company_id}:{raw_id}"`), o mesmo esquema que
`order/graph_normalizer.py::_scoped` passou a gravar pra ingestões novas.

Por que precisa: esses nós eram `MERGE`ados só pelo ID bruto do ERP — se
duas empresas usarem o mesmo provider, IDs de catálogo podem colidir e
fundir os nós (ver docstring de `graph_normalizer.py`). Renomear a
propriedade `.id` não quebra nenhum relacionamento (relações apontam pro nó,
não pro valor da propriedade) — RFM, pagerank, community, embeddings,
SIMILAR_TO, BOUGHT_WITH continuam intactos no mesmo nó.

Idempotente: cada query só mexe em nós cujo `.id` ainda não começa com
`"{company_id}:"`, então rodar de novo não faz nada na segunda vez.

Uso: `DB_HOST=localhost uv run python scripts/migrate_tenant_scoped_ids.py`
(precisa de `DB_HOST=localhost` só se `NEO4J_URI` no `.env` apontar pro
hostname interno do compose — ver `NEO4J_URI` em `.env`; rodando de dentro
do container/rede do compose não precisa).
"""

from __future__ import annotations

from app.core.infrastructure.database.neo4j import run_query

# (rótulo, MATCH da empresa -> nó alvo) — ordem não importa: a derivação da
# empresa de cada nó é feita por travessia de relacionamento, nunca a partir
# do valor de `.id` de outro nó, então não há dependência entre labels.
_MIGRATIONS: list[tuple[str, str]] = [
    (
        "Product",
        "MATCH (comp:Company)<-[:BELONGS_TO]-(:Order)-[:CONTAINS]->(target:Product)",
    ),
    (
        "SKU",
        "MATCH (comp:Company)<-[:BELONGS_TO]-(:Order)-[:CONTAINS]->(:Product)"
        "-[:HAS_VARIANT]->(target:SKU)",
    ),
    (
        "Color",
        "MATCH (comp:Company)<-[:BELONGS_TO]-(:Order)-[:CONTAINS]->(:Product)"
        "-[:HAS_VARIANT]->(:SKU)-[:HAS_COLOR]->(target:Color)",
    ),
    (
        "Size",
        "MATCH (comp:Company)<-[:BELONGS_TO]-(:Order)-[:CONTAINS]->(:Product)"
        "-[:HAS_VARIANT]->(:SKU)-[:HAS_SIZE]->(target:Size)",
    ),
    (
        "Seller",
        "MATCH (comp:Company)<-[:BELONGS_TO]-(:Order)-[:SOLD_BY]->(target:Seller)",
    ),
    (
        "Customer",
        "MATCH (comp:Company)<-[:BELONGS_TO]-(:Order)-[:PLACED_BY]->(target:Customer)",
    ),
]

_PREFLIGHT_TEMPLATE = """
{match_clause}
WHERE NOT target.id STARTS WITH (comp.id + ':')
WITH target, collect(DISTINCT comp.id) AS company_ids
WHERE size(company_ids) <> 1
RETURN target.id AS id, company_ids
LIMIT 20
"""

_MIGRATE_TEMPLATE = """
{match_clause}
WHERE NOT target.id STARTS WITH (comp.id + ':')
WITH target, collect(DISTINCT comp.id) AS company_ids
WHERE size(company_ids) = 1
SET target.id = company_ids[0] + ':' + target.id
RETURN count(target) AS migrated
"""


def main() -> None:
    for label, match_clause in _MIGRATIONS:
        ambiguous = run_query(_PREFLIGHT_TEMPLATE.format(match_clause=match_clause))
        if ambiguous:
            print(
                f"[{label}] ATENÇÃO: {len(ambiguous)} nó(s) alcançável(is) por mais de uma "
                f"empresa — pulados, não renomeados automaticamente:"
            )
            for row in ambiguous:
                print(f"    id={row['id']!r} company_ids={row['company_ids']!r}")

        result = run_query(_MIGRATE_TEMPLATE.format(match_clause=match_clause))
        migrated = result[0]["migrated"] if result else 0
        print(f"[{label}] migrados: {migrated}")


if __name__ == "__main__":
    main()
