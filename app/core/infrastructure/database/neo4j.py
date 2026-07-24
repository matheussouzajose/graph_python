"""
Gerenciador de conexão Neo4j.

Por que singleton: abrir um GraphDatabase.driver() por chamada de função é
caro (handshake TLS + pool novo toda vez). O driver já gerencia um pool de
conexões internamente — você cria UM driver para a vida inteira do processo
e reusa em todas as sessions.
"""

from __future__ import annotations

import asyncio
import threading
from collections.abc import Iterator
from contextlib import contextmanager

from neo4j import Driver, GraphDatabase, Session
from neo4j.exceptions import ServiceUnavailable, SessionExpired, TransientError
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from app.core.config import settings
from app.core.logger import logger

_RETRYABLE_ERRORS = (ServiceUnavailable, SessionExpired, TransientError)

_driver: Driver | None = None
_driver_lock = threading.Lock()

# Schema do grafo: aplicado (idempotente, via IF NOT EXISTS) uma vez no
# startup por setup_schema(). Sem histórico/versionamento como o Alembic do
# Postgres — mudar uma constraint existente exige DROP manual.
CONSTRAINTS = [
    "CREATE CONSTRAINT order_id IF NOT EXISTS FOR (o:Order) REQUIRE o.id IS UNIQUE",
    "CREATE CONSTRAINT customer_id IF NOT EXISTS FOR (c:Customer) REQUIRE c.id IS UNIQUE",
    "CREATE CONSTRAINT product_id IF NOT EXISTS FOR (p:Product) REQUIRE p.id IS UNIQUE",
    "CREATE CONSTRAINT sku_id IF NOT EXISTS FOR (s:SKU) REQUIRE s.id IS UNIQUE",
    "CREATE CONSTRAINT seller_id IF NOT EXISTS FOR (s:Seller) REQUIRE s.id IS UNIQUE",
    "CREATE CONSTRAINT company_id IF NOT EXISTS FOR (c:Company) REQUIRE c.id IS UNIQUE",
    "CREATE CONSTRAINT color_id IF NOT EXISTS FOR (c:Color) REQUIRE c.id IS UNIQUE",
    "CREATE CONSTRAINT size_id IF NOT EXISTS FOR (s:Size) REQUIRE s.id IS UNIQUE",
    "CREATE CONSTRAINT coupon_code IF NOT EXISTS FOR (c:Coupon) REQUIRE c.code IS UNIQUE",
    "CREATE CONSTRAINT status_name IF NOT EXISTS FOR (s:OrderStatus) REQUIRE s.name IS UNIQUE",
    "CREATE CONSTRAINT address_id IF NOT EXISTS FOR (a:Address) REQUIRE a.id IS UNIQUE",
    "CREATE CONSTRAINT payment_id IF NOT EXISTS FOR (p:Payment) REQUIRE p.id IS UNIQUE",
    "CREATE CONSTRAINT city_name IF NOT EXISTS FOR (c:City) REQUIRE c.name IS UNIQUE",
    "CREATE CONSTRAINT state_initials IF NOT EXISTS FOR (s:State) REQUIRE s.initials IS UNIQUE",
]

# Índices extras (não-unique) para consultas frequentes — acelera lookups
# por campos usados em filtros de dashboard/RAG que não são chave primária.
INDEXES = [
    "CREATE INDEX order_status_idx IF NOT EXISTS FOR (o:Order) ON (o.status)",
    "CREATE INDEX order_created_at_idx IF NOT EXISTS FOR (o:Order) ON (o.created_at)",
    "CREATE INDEX customer_document_idx IF NOT EXISTS FOR (c:Customer) ON (c.document)",
    "CREATE INDEX product_name_idx IF NOT EXISTS FOR (p:Product) ON (p.name)",
]


def get_driver() -> Driver:
    global _driver
    if _driver is None:
        with _driver_lock:
            if _driver is None:
                _driver = GraphDatabase.driver(
                    settings.NEO4J_URI,
                    auth=(settings.NEO4J_USER, settings.NEO4J_PASSWORD),
                    max_connection_pool_size=50,
                )
                _driver.verify_connectivity()
                logger.info("neo4j_driver_initialized", uri=settings.NEO4J_URI)
    return _driver


def close_driver() -> None:
    global _driver
    if _driver is not None:
        _driver.close()
        _driver = None
        logger.info("neo4j_driver_closed")


@contextmanager
def get_session() -> Iterator[Session]:
    driver = get_driver()
    session = driver.session(database="neo4j")
    try:
        yield session
    finally:
        session.close()


@retry(
    retry=retry_if_exception_type(_RETRYABLE_ERRORS),
    stop=stop_after_attempt(4),
    wait=wait_exponential(multiplier=1, min=1, max=10),
    reraise=True,
)
def run_query(query: str, params: dict | None = None) -> list[dict]:
    """
    Executa uma query com retry automático em caso de instabilidade transitória
    de rede/cluster ou de transação (deadlock, lock contention). Não faz retry
    em erros de sintaxe Cypher ou de constraint (esses são bugs, não
    instabilidade — retry só mascararia o problema).
    """
    with get_session() as session:
        result = session.run(query, params or {})
        return [record.data() for record in result]


@retry(
    retry=retry_if_exception_type(_RETRYABLE_ERRORS),
    stop=stop_after_attempt(4),
    wait=wait_exponential(multiplier=1, min=1, max=10),
    reraise=True,
)
def run_write_batch(query: str, batch_params: list[dict]) -> None:
    """
    Executa a mesma query para uma lista de parâmetros dentro de UMA transação.
    Usado com queries que fazem UNWIND $rows AS row internamente — assim uma
    ingestão de 200 pedidos vira 1 round-trip de rede, não 200.

    Mesmo retry de `run_query`: sem ele, um `TransientError` (deadlock/lock
    contention — esperado quando duas escritas concorrentes tentam criar o
    mesmo nó novo pela primeira vez) derruba a linha/lote permanentemente na
    primeira tentativa em vez de só esperar a outra transação liberar.
    """
    with get_session() as session:
        session.execute_write(lambda tx: tx.run(query, rows=batch_params).consume())


async def setup_schema() -> None:
    """Aplica constraints e índices do grafo (idempotente). Chamado uma vez no
    startup da app (ver `main.py`'s lifespan)."""
    for constraint in CONSTRAINTS:
        await asyncio.to_thread(run_query, constraint)
        logger.info("constraint_applied", constraint=constraint.split(" FOR")[0])

    for index in INDEXES:
        await asyncio.to_thread(run_query, index)
        logger.info("index_applied", index=index.split(" FOR")[0])

    logger.info("schema_setup_complete", constraints=len(CONSTRAINTS), indexes=len(INDEXES))
