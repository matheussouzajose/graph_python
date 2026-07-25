from datetime import datetime
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class BrandArchetype(StrEnum):
    """The 12 Jungian brand archetypes (Mark & Pearson, "The Hero and the Outlaw").

    Stored as plain text in the DB (see `BrandArchetypeProfileORM.primary_archetype`
    / `secondary_archetype`) — an application-level allow-list, no migration
    needed to reference an archetype, mirroring `IntegrationProvider`.
    """

    INNOCENT = "innocent"
    EXPLORER = "explorer"
    SAGE = "sage"
    HERO = "hero"
    OUTLAW = "outlaw"
    MAGICIAN = "magician"
    EVERYMAN = "everyman"
    JESTER = "jester"
    LOVER = "lover"
    RULER = "ruler"
    CREATOR = "creator"
    CAREGIVER = "caregiver"


class Voice(BaseModel):
    tone: list[str] = Field(default_factory=list)
    sentence_style: str | None = None
    vocabulary_prefer: list[str] = Field(default_factory=list)
    vocabulary_avoid: list[str] = Field(default_factory=list)


class Audience(BaseModel):
    who: str | None = None
    speaks_to_them_as: str | None = None


class Guardrails(BaseModel):
    do: list[str] = Field(default_factory=list)
    dont: list[str] = Field(default_factory=list)


class BrandArchetypeProfileCreate(BaseModel):
    company_id: UUID
    primary_archetype: BrandArchetype
    secondary_archetype: BrandArchetype | None = None
    archetype_scores: dict[str, int] = Field(default_factory=dict)
    core_desire: str | None = None
    fear: str | None = None
    strategy: str | None = None
    voice: Voice = Field(default_factory=Voice)
    audience: Audience = Field(default_factory=Audience)
    messaging_pillars: list[str] = Field(default_factory=list)
    guardrails: Guardrails = Field(default_factory=Guardrails)
    reference_examples: list[str] = Field(default_factory=list)


class BrandArchetypeProfileUpdate(BaseModel):
    """`company_id` is intentionally not editable — moving a profile to another
    company means deleting and recreating it.
    """

    primary_archetype: BrandArchetype | None = None
    secondary_archetype: BrandArchetype | None = None
    archetype_scores: dict[str, int] | None = None
    core_desire: str | None = None
    fear: str | None = None
    strategy: str | None = None
    voice: Voice | None = None
    audience: Audience | None = None
    messaging_pillars: list[str] | None = None
    guardrails: Guardrails | None = None
    reference_examples: list[str] | None = None


class BrandArchetypeProfileResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    company_id: UUID
    primary_archetype: str
    secondary_archetype: str | None
    archetype_scores: dict[str, int]
    core_desire: str | None
    fear: str | None
    strategy: str | None
    voice: Voice
    audience: Audience
    messaging_pillars: list[str]
    guardrails: Guardrails
    reference_examples: list[str]
    created_at: datetime
    updated_at: datetime
