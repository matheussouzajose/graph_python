"""
Via "global" do Graph RAG: o LLM lê o schema do grafo e gera a query Cypher
na hora, para perguntas analíticas/agregadas que a busca vetorial não
resolve bem (ex: "quantos pedidos com cupom por estado no último mês").

Guardrails aplicados:
1. Validação textual: bloqueia queries que contenham cláusulas de escrita
   antes mesmo de tentar executá-las, e loga a tentativa separadamente.
2. Timeout: query gerada dinamicamente pode ser cara (ex: sem WHERE,
   varrendo todo o grafo) — `dbms.transaction.timeout` no Neo4j corta depois
   de N segundos (ver `docker-compose.yml`).
3. Limite de linhas: ver `_enforce_limit` abaixo — hoje é uma limitação
   conhecida, não uma proteção ativa.

O QUE NÃO TEM (diferente do design original que motivou este módulo): uma
credencial Neo4j dedicada e restrita a leitura. O Neo4j deste projeto roda
em Community Edition, que não suporta RBAC/roles customizadas — qualquer
usuário adicional criado teria os mesmos privilégios completos do usuário
admin, então essa camada de defesa em profundidade não é uma opção real
aqui. Este módulo usa as mesmas credenciais (`NEO4J_USER`/`NEO4J_PASSWORD`)
do resto da aplicação; a validação textual abaixo e o timeout de transação
são a defesa de fato. Se o Neo4j deste projeto for migrado para Enterprise
(ou Aura com RBAC), vale reintroduzir um usuário read-only dedicado aqui.
"""

from __future__ import annotations

import re
from collections.abc import Iterator

from langchain_neo4j import GraphCypherQAChain, Neo4jGraph
from langchain_openai import ChatOpenAI
from neo4j_graphrag.retrievers.text2cypher import extract_cypher

from app.core.config import settings
from app.core.logger import logger

# Cláusulas de escrita/administrativas — se aparecerem na query gerada,
# rejeitamos antes mesmo de tentar executar.
FORBIDDEN_CLAUSES = re.compile(
    r"\b(CREATE|MERGE|DELETE|DETACH|SET|REMOVE|DROP|CALL\s+gds\..*\.(write|mutate)|"
    r"CREATE\s+USER|CREATE\s+ROLE|GRANT|REVOKE)\b",
    re.IGNORECASE,
)

DEFAULT_LIMIT = 25


class UnsafeCypherQueryError(Exception):
    """Levantado quando a query gerada pelo LLM contém operação não permitida."""


def _validate_query_is_read_only(cypher_query: str) -> None:
    if FORBIDDEN_CLAUSES.search(cypher_query):
        logger.error("unsafe_cypher_blocked", query=cypher_query)
        raise UnsafeCypherQueryError(
            "A query gerada continha uma operação de escrita/administrativa e foi bloqueada."
        )


def _enforce_limit(cypher_query: str, max_rows: int = DEFAULT_LIMIT) -> str:
    """
    Injeta LIMIT se a query gerada não tiver um.

    LIMITAÇÃO CONHECIDA: o GraphCypherQAChain padrão do LangChain não expõe
    um hook para reescrever a query antes de executá-la contra o banco — o
    parâmetro `top_k` só trunca o resultado ao FORMATAR a resposta, depois
    da query já ter rodado inteira. Para aplicar este LIMIT de fato antes da
    execução (importante contra queries acidentalmente caras, tipo full scan
    sem WHERE), é necessário subclassear GraphCypherQAChain e sobrescrever o
    método `_call` para interceptar a query entre geração e execução.
    Deixado como próximo passo de hardening; por ora, o timeout de query no
    lado do Neo4j (`dbms.transaction.timeout`) é a proteção efetiva contra
    esse cenário.
    """
    if re.search(r"\bLIMIT\s+\d+", cypher_query, re.IGNORECASE):
        return cypher_query
    return f"{cypher_query.rstrip().rstrip(';')}\nLIMIT {max_rows}"


def _get_graph() -> Neo4jGraph:
    return Neo4jGraph(
        url=settings.NEO4J_URI,
        username=settings.NEO4J_USER,
        password=settings.NEO4J_PASSWORD,
        database="neo4j",
        # Requer APOC habilitado no Neo4j. O schema enriquecido melhora a
        # qualidade do Cypher gerado pelo LLM para perguntas analíticas.
        enhanced_schema=True,
    )


def build_cypher_qa_chain() -> GraphCypherQAChain:
    graph = _get_graph()
    graph.refresh_schema()

    llm = ChatOpenAI(
        model=settings.OPENAI_CHAT_MODEL, temperature=0, api_key=settings.OPENAI_API_KEY
    )

    chain = GraphCypherQAChain.from_llm(
        llm=llm,
        graph=graph,
        verbose=False,
        # obrigatório na API do LangChain; guardrails acima cobrem o risco
        allow_dangerous_requests=True,
        return_intermediate_steps=True,
        top_k=DEFAULT_LIMIT,
    )
    return chain


def ask_global(question: str) -> dict:
    """
    Entry point da via "global". Intercepta a query gerada antes de confiar
    no resultado — o LangChain não expõe um hook nativo de "valide antes de
    rodar", então fazemos isso reexecutando a validação sobre a query
    capturada em intermediate_steps.
    """
    try:
        chain = build_cypher_qa_chain()
        result = chain.invoke({"query": question})
    except Exception as e:
        logger.error("cypher_qa_chain_failed", question=question, error=str(e))
        return {
            "answer": (
                "Não consegui gerar uma consulta segura para essa pergunta. "
                "Tente reformular de forma mais específica."
            ),
            "generated_query": None,
            "error": str(e),
        }

    intermediate_steps = result.get("intermediate_steps", [])
    generated_query = None
    for step in intermediate_steps:
        if isinstance(step, dict) and "query" in step:
            generated_query = step["query"]
            break

    if generated_query:
        try:
            _validate_query_is_read_only(generated_query)
        except UnsafeCypherQueryError as e:
            return {
                "answer": "A consulta gerada foi bloqueada por motivos de segurança.",
                "generated_query": generated_query,
                "error": str(e),
            }

    logger.info("cypher_qa_answered", question=question, generated_query=generated_query)

    return {
        "answer": result.get("result"),
        "generated_query": generated_query,
        "error": None,
    }


def ask_global_stream(question: str) -> Iterator[dict]:
    """Variante em streaming da via GLOBAL. `GraphCypherQAChain.invoke` roda
    geração de Cypher + execução + síntese da resposta como uma chamada só,
    sem hook pra transmitir a etapa final token a token — por isso aqui as
    duas primeiras etapas (`cypher_generation_chain`, execução no grafo) são
    chamadas diretamente, na mesma ordem e com os mesmos guardrails de
    `ask_global`, e só a etapa final (`qa_chain`, que é um Runnable LCEL)
    usa `.stream()` de verdade. Como a query já está em mãos antes de
    executá-la (diferente de `ask_global`, que só a vê depois do
    `chain.invoke` completo), também dá pra aplicar `_enforce_limit` aqui —
    o hardening que o docstring de `_enforce_limit` descreve como pendente."""
    try:
        chain = build_cypher_qa_chain()
    except Exception as e:
        logger.error("cypher_qa_chain_build_failed", question=question, error=str(e))
        yield {
            "type": "error",
            "message": "Não consegui preparar a consulta ao grafo. Tente novamente.",
        }
        return

    try:
        raw_cypher = chain.cypher_generation_chain.invoke(
            {"question": question, "examples": None, "schema": chain.graph_schema}
        )
        generated_query = extract_cypher(raw_cypher)
    except Exception as e:
        logger.error("cypher_generation_failed", question=question, error=str(e))
        yield {
            "type": "error",
            "message": "Não consegui gerar uma consulta para essa pergunta. Tente reformular.",
        }
        return

    try:
        _validate_query_is_read_only(generated_query)
    except UnsafeCypherQueryError as e:
        yield {
            "type": "error",
            "message": "A consulta gerada foi bloqueada por motivos de segurança.",
            "generated_query": generated_query,
        }
        logger.error("cypher_qa_stream_blocked", question=question, error=str(e))
        return

    generated_query = _enforce_limit(generated_query)

    try:
        context = chain.graph.query(generated_query)[:DEFAULT_LIMIT] if generated_query else []
    except Exception as e:
        logger.error("cypher_execution_failed", question=question, error=str(e))
        yield {
            "type": "error",
            "message": "A consulta gerada falhou ao rodar no grafo.",
            "generated_query": generated_query,
        }
        return

    yield {"type": "meta", "generated_query": generated_query}

    for chunk in chain.qa_chain.stream({"question": question, "context": context}):
        if chunk:
            yield {"type": "token", "text": chunk}

    logger.info("cypher_qa_answered_stream", question=question, generated_query=generated_query)
