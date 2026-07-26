"""Loads the curated global agent library from docs.

The curated Moda B2B agents are documented in Markdown because that is the
source humans review and edit. This module turns that document into
`AgentCreate` payloads for the admin seed endpoint, keeping runtime setup and
documentation from drifting apart.
"""

from __future__ import annotations

import re
from pathlib import Path

from app.features.agents.schemas import (
    AgentCreate,
    AgentKind,
    AgentOutputAction,
    AgentResponseFormat,
    AgentVideoProvider,
)

PROJECT_ROOT = Path(__file__).resolve().parents[3]
MODA_B2B_DOC = PROJECT_ROOT / "docs" / "agentes-moda-b2b-prompts.md"
ARCHETYPE_DOC = PROJECT_ROOT / "docs" / "agente-gerador-de-arquetipo-prompt.md"

AGENT_SECTION_START = "## Posicionamento B2B"
CODE_BLOCK_RE = re.compile(r"```(?:text)?\n(.*?)\n```", re.DOTALL)
TABLE_ROW_RE = re.compile(r"^\| ([^|]+) \| (.*) \|$")


def load_moda_b2b_global_agent_payloads(company_id) -> list[AgentCreate]:
    markdown = MODA_B2B_DOC.read_text(encoding="utf-8")
    archetype_prompt = _extract_archetype_system_prompt()

    sections = _agent_sections(markdown)
    payloads: list[AgentCreate] = []
    for title, section in sections:
        fields = _table_fields(section)
        name = _strip_ticks(fields.get("Nome", title))
        usage_instructions = _extract_usage_instructions(section)
        system_prompt = (
            archetype_prompt if name == "Arquétipos" else _extract_system_prompt(section)
        )
        if not system_prompt:
            continue

        kind = _kind_from_label(fields.get("Tipo de agente"))
        response_format = (
            AgentResponseFormat.JSON
            if fields.get("Formato de resposta") == "`JSON`"
            else AgentResponseFormat.TEXT
        )
        output_action = (
            AgentOutputAction.APPLY_BRAND_ARCHETYPE
            if name == "Arquétipos"
            else AgentOutputAction.NONE
        )

        payloads.append(
            AgentCreate(
                company_id=company_id,
                name=name,
                category=_strip_ticks(fields.get("Categoria")),
                tags=_split_csv_field(fields.get("Tags")),
                skills=_split_csv_field(fields.get("Skills")),
                description=_strip_ticks(fields.get("Descrição curta")),
                kind=kind,
                usage_instructions=usage_instructions,
                system_prompt=system_prompt,
                temperature=0.4 if name == "Arquétipos" else 0.3,
                uses_brand_archetype=name != "Arquétipos",
                response_format=response_format,
                output_action=output_action,
                video_provider=AgentVideoProvider.OPENAI,
                video_size=_video_size(fields),
                video_seconds=_video_seconds(fields),
                image_size=(
                    _strip_ticks(fields.get("Tamanho")) if _is_image_generation(kind) else None
                ),
                image_quality=(
                    _strip_ticks(fields.get("Qualidade")) if _is_image_generation(kind) else None
                ),
                image_format=(
                    _strip_ticks(fields.get("Formato")) if _is_image_generation(kind) else None
                ),
                is_active=True,
                is_global=True,
            )
        )
    return payloads


def _agent_sections(markdown: str) -> list[tuple[str, str]]:
    start = markdown.index(AGENT_SECTION_START)
    body = markdown[start:]
    matches = list(re.finditer(r"^## (.+)$", body, flags=re.MULTILINE))
    sections: list[tuple[str, str]] = []
    for index, match in enumerate(matches):
        title = match.group(1).strip()
        section_start = match.start()
        section_end = matches[index + 1].start() if index + 1 < len(matches) else len(body)
        sections.append((title, body[section_start:section_end].strip()))
    return sections


def _table_fields(section: str) -> dict[str, str]:
    fields: dict[str, str] = {}
    for line in section.splitlines():
        match = TABLE_ROW_RE.match(line)
        if not match:
            continue
        key = match.group(1).strip()
        value = match.group(2).strip()
        if key in {"Campo", "---"}:
            continue
        fields[key] = value
    return fields


def _extract_usage_instructions(section: str) -> str | None:
    marker = "**Instruções para quem for usar**"
    if marker not in section:
        return None
    tail = section.split(marker, 1)[1]
    blocks = CODE_BLOCK_RE.findall(tail)
    return blocks[0].strip() if blocks else None


def _extract_system_prompt(section: str) -> str | None:
    marker = "**System prompt**"
    if marker not in section:
        return None
    tail = section.split(marker, 1)[1]
    blocks = CODE_BLOCK_RE.findall(tail)
    return blocks[0].strip() if blocks else None


def _extract_archetype_system_prompt() -> str:
    markdown = ARCHETYPE_DOC.read_text(encoding="utf-8")
    marker = "## System prompt"
    tail = markdown.split(marker, 1)[1]
    blocks = CODE_BLOCK_RE.findall(tail)
    return blocks[0].strip()


def _kind_from_label(label: str | None) -> AgentKind:
    normalized = _strip_ticks(label)
    return {
        "Imagem → texto": AgentKind.IMAGE_TO_TEXT,
        "Texto → vídeo": AgentKind.TEXT_TO_VIDEO,
        "Imagem → vídeo": AgentKind.IMAGE_TO_VIDEO,
        "Texto → imagem": AgentKind.TEXT_TO_IMAGE,
        "Imagem → imagem": AgentKind.IMAGE_TO_IMAGE,
    }.get(normalized or "", AgentKind.CHAT)


def _video_size(fields: dict[str, str]) -> str | None:
    kind = _kind_from_label(fields.get("Tipo de agente"))
    if kind not in {AgentKind.TEXT_TO_VIDEO, AgentKind.IMAGE_TO_VIDEO}:
        return None
    return _strip_ticks(fields.get("Formato")) or "720x1280"


def _video_seconds(fields: dict[str, str]) -> str | None:
    kind = _kind_from_label(fields.get("Tipo de agente"))
    if kind not in {AgentKind.TEXT_TO_VIDEO, AgentKind.IMAGE_TO_VIDEO}:
        return None
    value = _strip_ticks(fields.get("Duração")) or "8s"
    match = re.search(r"\d+", value)
    return match.group(0) if match else "8"


def _is_image_generation(kind: AgentKind) -> bool:
    return kind in {AgentKind.TEXT_TO_IMAGE, AgentKind.IMAGE_TO_IMAGE}


def _split_csv_field(value: str | None) -> list[str]:
    clean = _strip_ticks(value)
    if not clean:
        return []
    return [item.strip() for item in clean.split(",") if item.strip()]


def _strip_ticks(value: str | None) -> str | None:
    if value is None:
        return None
    return value.strip().strip("`").strip()
