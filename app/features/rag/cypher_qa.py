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

# Passado como `{examples}` no prompt padrão do GraphCypherQAChain (opcional,
# mas antes sempre None). Existe pra corrigir um erro observado ao vivo: pra
# "quais produtos mais vendidos", o LLM assumia que `CONTAINS.added` era a
# quantidade vendida (nome mais intuitivo em inglês) e retornava "nenhum
# produto vendido" — na prática `added` é um campo de workflow de separação
# de estoque do ERP, populado em só ~1/3 dos itens (confirmado ao vivo:
# 16052/49346), enquanto `requested` (a quantidade que o cliente pediu) está
# presente em 100% dos itens e é a métrica certa pra "vendido"/"mais
# vendidos". O company_id no exemplo é só placeholder — a instrução real de
# escopo (`_scoped_question`) já injeta o id verdadeiro.
_CYPHER_EXAMPLES = """# A relação (:Order)-[:CONTAINS]->(:Product) tem as propriedades requested,
# reserved, added e status. `requested` é a quantidade que o cliente pediu —
# é essa a propriedade certa pra "quantidade vendida"/"produtos mais
# vendidos". NÃO use `added` pra isso: é um campo de workflow de separação
# de estoque do ERP e fica nulo pra boa parte dos pedidos.

# Pergunta: Quais são os produtos mais vendidos?
MATCH (o:Order)-[:BELONGS_TO]->(:Company {id: '00000000-0000-0000-0000-000000000000'})
MATCH (o)-[c:CONTAINS]->(p:Product)
RETURN p.name AS product_name, sum(c.requested) AS quantity_sold
ORDER BY quantity_sold DESC
LIMIT 10"""


class UnsafeCypherQueryError(Exception):
    """Levantado quando a query gerada pelo LLM contém operação não permitida."""


def _validate_query_is_read_only(cypher_query: str) -> None:
    if FORBIDDEN_CLAUSES.search(cypher_query):
        logger.error("unsafe_cypher_blocked", query=cypher_query)
        raise UnsafeCypherQueryError(
            "A query gerada continha uma operação de escrita/administrativa e foi bloqueada."
        )


def _validate_query_is_company_scoped(cypher_query: str, company_id: str) -> None:
    if company_id not in cypher_query or "BELONGS_TO" not in cypher_query:
        logger.error("unscoped_cypher_blocked", query=cypher_query, company_id=company_id)
        raise UnsafeCypherQueryError("A query gerada não continha o filtro obrigatório de empresa.")


def _scoped_question(question: str, company_id: str) -> str:
    # Observado ao vivo: quando a consulta precisa de mais de uma variável
    # Order (ex: "produtos mais vendidos" agregando várias Order), o LLM
    # tentava reaproveitar o nó Company do primeiro MATCH invertendo a seta
    # pra "alcançar" a segunda Order (`-[:BELONGS_TO]->(:Company)-[:BELONGS_TO]<-`),
    # o que é Cypher inválido — a seta de BELONGS_TO só existe num sentido
    # (Order -> Company). A instrução original dava só um fragmento pronto
    # pra copiar, sem dizer o que fazer quando há mais de um Order; por isso
    # agora é explícito: repita o MATCH inteiro por variável, nunca
    # reaproveite o nó Company invertendo a seta.
    return (
        f"{question}\n\n"
        "Restrição obrigatória de segurança: use apenas dados da empresa "
        f"Neo4j Company.id = '{company_id}'. Toda variável de Order na "
        "consulta Cypher deve ter seu próprio MATCH completo no padrão "
        f"(o:Order)-[:BELONGS_TO]->(:Company {{id: '{company_id}'}}), com a "
        "seta sempre saindo de Order e apontando para Company — essa relação "
        "não existe no sentido inverso. Se a consulta precisar de mais de uma "
        "variável Order (ex: agregando vários pedidos, ou comparando dois "
        "pedidos), repita esse MATCH completo para cada variável de Order; "
        "nunca reutilize o nó Company de um MATCH anterior invertendo a seta "
        "para alcançar outra Order."
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


def ask_global(question: str, company_id: str | None = None) -> dict:
    """
    Entry point não-streaming da via GLOBAL. Consome `ask_global_stream` e
    junta os tokens numa resposta só, em vez de reimplementar geração ->
    validação -> execução -> síntese uma segunda vez via
    `GraphCypherQAChain.invoke()` direto — o `.invoke()` roda essas quatro
    etapas como uma caixa preta só, então qualquer falha (build da chain,
    Cypher com erro de sintaxe, execução falhando no Neo4j, guardrail de
    segurança) virava a mesma exceção genérica e a mesma mensagem
    ("não consegui gerar uma consulta segura"), mesmo quando o problema não
    tinha nada de segurança — só um Cypher malformado, por exemplo.
    `ask_global_stream` já expõe cada etapa com sua própria mensagem de erro;
    reusar essa lógica em vez de duplicá-la é o que corrige isso aqui.
    """
    generated_query: str | None = None
    answer_parts: list[str] = []
    error: str | None = None

    for event in ask_global_stream(question, company_id=company_id):
        event_type = event["type"]
        if event_type == "meta":
            generated_query = event.get("generated_query", generated_query)
        elif event_type == "token":
            answer_parts.append(event.get("text", ""))
        elif event_type == "error":
            error = event.get("message")
            generated_query = event.get("generated_query", generated_query)

    if error:
        return {"answer": error, "generated_query": generated_query, "error": error}

    logger.info("cypher_qa_answered", question=question, generated_query=generated_query)
    return {
        "answer": "".join(answer_parts),
        "generated_query": generated_query,
        "error": None,
    }


# Quantas vezes tentar gerar+validar+rodar a query antes de desistir e
# expor o erro. LLMs em temperature=0 ainda têm variância de geração real
# (observado ao vivo: ~1 em cada 3 chamadas pra uma pergunta idêntica
# produzia Cypher sintaticamente inválido, ex: `-[:BELONGS_TO]<-` em vez de
# `<-[:BELONGS_TO]-`, sobretudo depois que `_scoped_question` passou a
# injetar a exigência de filtro por empresa no texto da pergunta) — uma
# segunda tentativa quase sempre resolve, então vale mais que expor a falha
# direto pro usuário na primeira instabilidade.
_MAX_GENERATION_ATTEMPTS = 2


def ask_global_stream(question: str, company_id: str | None = None) -> Iterator[dict]:
    """Variante em streaming da via GLOBAL. `GraphCypherQAChain.invoke` roda
    geração de Cypher + execução + síntese da resposta como uma chamada só,
    sem hook pra transmitir a etapa final token a token — por isso aqui as
    duas primeiras etapas (`cypher_generation_chain`, execução no grafo) são
    chamadas diretamente, na mesma ordem e com os mesmos guardrails de
    `ask_global`, e só a etapa final (`qa_chain`, que é um Runnable LCEL)
    usa `.stream()` de verdade. Como a query já está em mãos antes de
    executá-la (diferente de `ask_global`, que só a vê depois do
    `chain.invoke` completo), também dá pra aplicar `_enforce_limit` aqui —
    o hardening que o docstring de `_enforce_limit` descreve como pendente.

    Geração, validação e execução rodam dentro de um loop de retry (ver
    `_MAX_GENERATION_ATTEMPTS`) — cada tentativa nova pede uma query gerada
    do zero, não uma correção da anterior, já que o LLM não vê o erro da
    tentativa passada. Só o último erro é exposto se todas as tentativas
    falharem."""
    try:
        chain = build_cypher_qa_chain()
    except Exception as e:
        logger.error("cypher_qa_chain_build_failed", question=question, error=str(e))
        yield {
            "type": "error",
            "message": "Não consegui preparar a consulta ao grafo. Tente novamente.",
        }
        return

    secured_question = _scoped_question(question, company_id) if company_id else question
    generated_query: str | None = None
    context: list = []
    error_event: dict | None = None

    for attempt in range(1, _MAX_GENERATION_ATTEMPTS + 1):
        try:
            raw_cypher = chain.cypher_generation_chain.invoke(
                {
                    "question": secured_question,
                    "examples": _CYPHER_EXAMPLES,
                    "schema": chain.graph_schema,
                }
            )
            generated_query = extract_cypher(raw_cypher)
        except Exception as e:
            logger.warning(
                "cypher_generation_failed", question=question, attempt=attempt, error=str(e)
            )
            error_event = {
                "type": "error",
                "message": "Não consegui gerar uma consulta para essa pergunta. Tente reformular.",
            }
            continue

        try:
            _validate_query_is_read_only(generated_query)
            if company_id:
                _validate_query_is_company_scoped(generated_query, company_id)
        except UnsafeCypherQueryError as e:
            logger.warning(
                "cypher_qa_stream_blocked", question=question, attempt=attempt, error=str(e)
            )
            error_event = {
                "type": "error",
                "message": "A consulta gerada foi bloqueada por motivos de segurança.",
                "generated_query": generated_query,
            }
            continue

        generated_query = _enforce_limit(generated_query)

        try:
            context = chain.graph.query(generated_query)[:DEFAULT_LIMIT] if generated_query else []
        except Exception as e:
            logger.warning(
                "cypher_execution_failed", question=question, attempt=attempt, error=str(e)
            )
            error_event = {
                "type": "error",
                "message": "A consulta gerada falhou ao rodar no grafo.",
                "generated_query": generated_query,
            }
            continue

        error_event = None
        break

    if error_event is not None:
        logger.error(
            "cypher_qa_stream_failed_after_retries",
            question=question,
            attempts=_MAX_GENERATION_ATTEMPTS,
        )
        yield error_event
        return

    yield {"type": "meta", "generated_query": generated_query}

    for chunk in chain.qa_chain.stream({"question": question, "context": context}):
        if chunk:
            yield {"type": "token", "text": chunk}

    logger.info("cypher_qa_answered_stream", question=question, generated_query=generated_query)
