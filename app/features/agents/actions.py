"""Registry of "apply this run's structured output" actions.

Each entry here is deliberately real code, not agent config — applying a
run's JSON output means writing it into a real domain table with real
validation (e.g. creating/updating a `BrandArchetypeProfile`), which can't
be expressed generically from a JSON blob alone. `Agent.output_action` just
says *which* of these (if any) a given agent's completed runs offer; adding
a new action means registering a new handler here, never touching the
no-code agent execution engine in `service.py`.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any
from uuid import UUID

from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.brand_archetype.repository import BrandArchetypeProfileRepository
from app.features.brand_archetype.schemas import (
    BrandArchetypeProfileCreate,
    BrandArchetypeProfileResponse,
    BrandArchetypeProfileUpdate,
)
from app.features.brand_archetype.service import BrandArchetypeProfileService
from app.features.company.repository import CompanyRepository


class AgentRunNotApplicableError(Exception):
    """Raised when a run's structured output doesn't match what its
    declared action expects (e.g. missing/invalid `primary_archetype`)."""


async def _apply_brand_archetype(
    session: AsyncSession, company_id: UUID, data: dict[str, Any]
) -> dict[str, Any]:
    service = BrandArchetypeProfileService(
        BrandArchetypeProfileRepository(session), CompanyRepository(session)
    )
    fields = {key: value for key, value in data.items() if key != "company_id"}
    existing = await service.get_by_company_id(company_id)

    try:
        if existing is None:
            profile = await service.create(
                BrandArchetypeProfileCreate(company_id=company_id, **fields)
            )
        else:
            profile = await service.update(existing.id, BrandArchetypeProfileUpdate(**fields))
    except ValidationError as exc:
        raise AgentRunNotApplicableError(str(exc)) from exc

    if profile is None:
        raise AgentRunNotApplicableError("Profile disappeared mid-update")

    return BrandArchetypeProfileResponse.model_validate(profile).model_dump(mode="json")


ACTION_HANDLERS: dict[
    str, Callable[[AsyncSession, UUID, dict[str, Any]], Awaitable[dict[str, Any]]]
] = {
    "apply_brand_archetype": _apply_brand_archetype,
}
