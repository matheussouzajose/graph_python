"""ORM model for a company's brand archetype profile.

One profile per company (`company_id` is unique) — this is the reusable
"brand personality" context that future content-generating agents (Oraculo
Marketing, video script/agent modules, ...) read to produce output in that
company's voice, instead of a generic one. `voice`, `audience`, `guardrails`,
`messaging_pillars` and `reference_examples` are stored as JSONB rather than
normalized tables because they're read as a whole blob (prompt context), not
queried/filtered by their internal fields.
"""

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import ARRAY, DateTime, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.infrastructure.database.base import Base


class BrandArchetypeProfileORM(Base):
    __tablename__ = "brand_archetype_profiles"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    company_id: Mapped[UUID] = mapped_column(
        ForeignKey(
            "companies.id", ondelete="CASCADE", name="fk_brand_archetype_profiles_company_id"
        ),
        nullable=False,
        unique=True,
    )
    # One of the 12 Jungian brand archetypes (Mark & Pearson). Plain text, not
    # a DB enum — see `BrandArchetype` in schemas.py for the application-level
    # allow-list, mirroring `IntegrationProvider`.
    primary_archetype: Mapped[str] = mapped_column(String(50), nullable=False)
    secondary_archetype: Mapped[str | None] = mapped_column(String(50), nullable=True)
    # Raw per-archetype tally from the diagnostic questionnaire (docs/arquetipos-de-marca.md),
    # kept for auditability/re-scoring even after primary/secondary are set.
    archetype_scores: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    core_desire: Mapped[str | None] = mapped_column(String(500), nullable=True)
    fear: Mapped[str | None] = mapped_column(String(500), nullable=True)
    strategy: Mapped[str | None] = mapped_column(String(500), nullable=True)
    # {tone: [...], sentence_style: str, vocabulary_prefer: [...], vocabulary_avoid: [...]}
    voice: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    # {who: str, speaks_to_them_as: str}
    audience: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    messaging_pillars: Mapped[list[str]] = mapped_column(
        ARRAY(String), nullable=False, default=list
    )
    # {do: [...], dont: [...]}
    guardrails: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    reference_examples: Mapped[list[str]] = mapped_column(
        ARRAY(String), nullable=False, default=list
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
