"""Renders a `BrandArchetypeProfileORM` into a prompt-ready text block.

Shared by any future LLM-facing feature that needs to inject a company's
brand voice into a system prompt (currently `app.features.agents`) — kept
here, next to the ORM, so callers never need to know the JSONB shape of
`voice`/`audience`/`guardrails` themselves.
"""

from app.features.brand_archetype.orm import BrandArchetypeProfileORM


def format_brand_archetype_context(profile: BrandArchetypeProfileORM) -> str:
    lines = [f"Arquétipo de marca primário: {profile.primary_archetype}"]
    if profile.secondary_archetype:
        lines.append(f"Arquétipo de marca secundário: {profile.secondary_archetype}")
    if profile.core_desire:
        lines.append(f"Desejo central da marca: {profile.core_desire}")
    if profile.fear:
        lines.append(f"Medo da marca: {profile.fear}")
    if profile.strategy:
        lines.append(f"Estratégia da marca: {profile.strategy}")

    voice = profile.voice or {}
    if voice.get("tone"):
        lines.append(f"Tom de voz: {', '.join(voice['tone'])}")
    if voice.get("sentence_style"):
        lines.append(f"Estilo de frase: {voice['sentence_style']}")
    if voice.get("vocabulary_prefer"):
        lines.append(f"Vocabulário preferido: {', '.join(voice['vocabulary_prefer'])}")
    if voice.get("vocabulary_avoid"):
        lines.append(f"Vocabulário a evitar: {', '.join(voice['vocabulary_avoid'])}")

    audience = profile.audience or {}
    if audience.get("who"):
        lines.append(f"Público-alvo: {audience['who']}")
    if audience.get("speaks_to_them_as"):
        lines.append(f"Como a marca fala com o público: {audience['speaks_to_them_as']}")

    if profile.messaging_pillars:
        lines.append(f"Pilares de mensagem: {', '.join(profile.messaging_pillars)}")

    guardrails = profile.guardrails or {}
    if guardrails.get("do"):
        lines.append(f"Pode: {', '.join(guardrails['do'])}")
    if guardrails.get("dont"):
        lines.append(f"Não pode: {', '.join(guardrails['dont'])}")

    if profile.reference_examples:
        lines.append("Exemplos de referência: " + " | ".join(profile.reference_examples))

    return "\n".join(lines)
