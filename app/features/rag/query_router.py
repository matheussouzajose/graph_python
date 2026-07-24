"""
Decide qual via de Graph RAG usar para uma pergunta:

- LOCAL: pergunta sobre entidade específica ("o que é/tem o pedido X",
  "produtos parecidos com Y") -> hybrid_retrieve (busca vetorial + expansão
  de grafo fixa). Mais rápido, mais previsível, sem custo de gerar Cypher.

- GLOBAL: pergunta agregada/analítica ("quantos", "qual a média", "compare",
  "por estado/período") -> ask_global (GraphCypherQAChain). Só esse caminho
  resolve agregações, porque busca vetorial não soma nem agrupa nada.

A classificação usa um LLM barato e rápido (mesmo modelo de chat, com prompt
curto) em vez de regras de palavra-chave frágeis — mas ainda assim inclui um
fallback por palavra-chave caso a chamada de classificação falhe.

Chamado `query_router` (não `router`) para não colidir com a convenção deste
projeto de que `router.py` é sempre o módulo do `APIRouter` do FastAPI (ver
`app/features/rag/router.py`).
"""

from __future__ import annotations

import re

from openai import OpenAI

from app.core.config import settings
from app.core.logger import logger
from app.features.rag.chain import ask as ask_local
from app.features.rag.cypher_qa import ask_global

_client = OpenAI(api_key=settings.OPENAI_API_KEY)

CLASSIFIER_PROMPT = """Classifique a pergunta abaixo em uma única palavra:
- "LOCAL" se pergunta sobre um pedido, cliente ou produto específico,
ou pede recomendação/similaridade.
- "GLOBAL" se pede contagem, soma, média, comparação, agrupamento,
ou análise sobre múltiplos registros.

Pergunta: {question}

Responda apenas com LOCAL ou GLOBAL."""

# Fallback simples caso a chamada de classificação falhe (ex: API fora do ar)
GLOBAL_KEYWORDS = re.compile(
    r"\b(quantos|quantas|total de|média|media|soma|compare|comparar|por estado|"
    r"por período|periodo|ao longo do tempo|distribuição|distribuicao|percentual|taxa de|"
    r"segmento|segmentos|rfm|campe[oõ]es|leais|em risco|em_risco|novos|hibernando|"
    r"pagerank|page rank|importantes?|importância|importancia)\b",
    re.IGNORECASE,
)


def _classify(question: str) -> str:
    if GLOBAL_KEYWORDS.search(question):
        return "GLOBAL"

    try:
        response = _client.chat.completions.create(
            model=settings.OPENAI_CHAT_MODEL,
            messages=[{"role": "user", "content": CLASSIFIER_PROMPT.format(question=question)}],
            temperature=0,
            max_tokens=5,
        )
        label = (response.choices[0].message.content or "").strip().upper()
        if label in ("LOCAL", "GLOBAL"):
            return label
    except Exception as e:
        logger.warning("classification_failed_using_fallback", error=str(e))

    return "GLOBAL" if GLOBAL_KEYWORDS.search(question) else "LOCAL"


def ask(question: str, top_k: int = 5) -> dict:
    route = _classify(question)
    logger.info("query_routed", question=question, route=route)

    if route == "GLOBAL":
        result = ask_global(question)
        return {
            "route": "GLOBAL",
            "answer": result["answer"],
            "generated_query": result.get("generated_query"),
            "sources": None,
        }

    result = ask_local(question, top_k=top_k)
    return {
        "route": "LOCAL",
        "answer": result["answer"],
        "generated_query": None,
        "sources": result["sources"],
    }
