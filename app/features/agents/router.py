import json
from collections.abc import AsyncIterator
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.infrastructure.database.session import get_session
from app.features.agents.actions import ACTION_HANDLERS, AgentRunNotApplicableError
from app.features.agents.repository import AgentRepository
from app.features.agents.run_repository import AgentRunRepository
from app.features.agents.schemas import (
    AgentCreate,
    AgentGlobalSeedResponse,
    AgentResponse,
    AgentRunApplyResponse,
    AgentRunRequest,
    AgentRunResponse,
    AgentRunUpdate,
    AgentUpdate,
)
from app.features.agents.service import (
    AgentImageNotAvailableError,
    AgentInvalidRunInputError,
    AgentNotActiveError,
    AgentRunNotEditableError,
    AgentService,
    AgentVideoNotAvailableError,
    CompanyNotFoundError,
)
from app.features.brand_archetype.repository import BrandArchetypeProfileRepository
from app.features.company.repository import CompanyRepository
from app.features.user.schemas import CurrentUser
from app.features.user.security import get_current_user

router = APIRouter(prefix="/agents", tags=["agents"])
# Separate path root (not nested under /agents/{agent_id}) so it never
# collides with that path shape — /agents/runs/{run_id} would otherwise be
# ambiguous with /agents/{agent_id}.
runs_router = APIRouter(prefix="/agent-runs", tags=["agents"])


def get_agent_service(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> AgentService:
    return AgentService(
        AgentRepository(session),
        AgentRunRepository(session),
        CompanyRepository(session),
        BrandArchetypeProfileRepository(session),
    )


ServiceDep = Annotated[AgentService, Depends(get_agent_service)]
CurrentUserDep = Annotated[CurrentUser, Depends(get_current_user)]
SessionDep = Annotated[AsyncSession, Depends(get_session)]


@router.post("", response_model=AgentResponse, status_code=status.HTTP_201_CREATED)
async def create_agent(
    data: AgentCreate, service: ServiceDep, current_user: CurrentUserDep
) -> AgentResponse:
    if data.company_id != current_user.company_id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Cannot create an agent for another company")
    if data.is_global and current_user.role != "admin":
        raise HTTPException(
            status.HTTP_403_FORBIDDEN, "Only a company admin can create a global agent"
        )
    try:
        agent = await service.create(data)
    except CompanyNotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Company not found") from exc
    return AgentResponse.model_validate(agent)


@router.get("", response_model=list[AgentResponse])
async def list_agents(
    service: ServiceDep,
    current_user: CurrentUserDep,
    limit: int = 100,
    offset: int = 0,
    category: str | None = None,
) -> list[AgentResponse]:
    agents = await service.list(
        current_user.company_id, limit=limit, offset=offset, category=category
    )
    return [AgentResponse.model_validate(agent) for agent in agents]


@router.post("/global-defaults/moda-b2b", response_model=AgentGlobalSeedResponse)
async def seed_moda_b2b_global_agents(
    service: ServiceDep, current_user: CurrentUserDep
) -> AgentGlobalSeedResponse:
    """Creates the curated Moda B2B global agents from
    `docs/agentes-moda-b2b-prompts.md`.

    Idempotent by global agent name: if a global agent with the same name
    already exists, it is returned under `skipped` instead of duplicated.
    """
    if current_user.role != "admin":
        raise HTTPException(
            status.HTTP_403_FORBIDDEN, "Only a company admin can seed global agents"
        )
    created, skipped = await service.seed_moda_b2b_global_agents(current_user.company_id)
    return AgentGlobalSeedResponse(
        created=[AgentResponse.model_validate(agent) for agent in created],
        skipped=[AgentResponse.model_validate(agent) for agent in skipped],
    )


@router.get("/{agent_id}", response_model=AgentResponse)
async def get_agent(
    agent_id: UUID, service: ServiceDep, current_user: CurrentUserDep
) -> AgentResponse:
    agent = await service.get_visible_to_company(agent_id, current_user.company_id)
    if agent is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Agent not found")
    return AgentResponse.model_validate(agent)


@router.patch("/{agent_id}", response_model=AgentResponse)
async def update_agent(
    agent_id: UUID,
    data: AgentUpdate,
    service: ServiceDep,
    current_user: CurrentUserDep,
) -> AgentResponse:
    existing = await service.get_owned_by_company(agent_id, current_user.company_id)
    if existing is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Agent not found")
    if data.is_global is True and current_user.role != "admin":
        raise HTTPException(
            status.HTTP_403_FORBIDDEN, "Only a company admin can make an agent global"
        )
    agent = await service.update(agent_id, data)
    if agent is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Agent not found")
    return AgentResponse.model_validate(agent)


@router.delete("/{agent_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_agent(agent_id: UUID, service: ServiceDep, current_user: CurrentUserDep) -> None:
    existing = await service.get_owned_by_company(agent_id, current_user.company_id)
    if existing is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Agent not found")
    await service.delete(agent_id)


@router.post("/{agent_id}/run", response_model=AgentRunResponse)
async def run_agent(
    agent_id: UUID,
    data: AgentRunRequest,
    service: ServiceDep,
    current_user: CurrentUserDep,
) -> AgentRunResponse:
    agent = await service.get_visible_to_company(agent_id, current_user.company_id)
    if agent is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Agent not found")
    try:
        run = await service.run(
            agent, current_user.company_id, data.message, data.variables, data.image_urls
        )
    except AgentNotActiveError as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, "Agent is not active") from exc
    except AgentInvalidRunInputError as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(exc)) from exc
    return AgentRunResponse.model_validate(run)


@router.post("/{agent_id}/run/stream")
async def run_agent_stream(
    agent_id: UUID,
    data: AgentRunRequest,
    service: ServiceDep,
    current_user: CurrentUserDep,
) -> StreamingResponse:
    """Same as `POST /{agent_id}/run`, but streams the answer via
    Server-Sent Events as tokens arrive, instead of waiting for the full
    response — same contract as `/rag/ask/stream`.

    Events, one `data: {...}\\n\\n` per line, each with a `type`:
    - `token`: `{"text": "..."}` — a chunk of the answer, repeated.
    - `error`: `{"message": "..."}` — if something fails mid-stream.
    - `done`: `{"run": AgentRunResponse}` — always the last event.
    """
    agent = await service.get_visible_to_company(agent_id, current_user.company_id)
    if agent is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Agent not found")
    if not agent.is_active:
        raise HTTPException(status.HTTP_409_CONFLICT, "Agent is not active")
    if agent.kind != "chat":
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "This agent doesn't support streaming — use POST /agents/{id}/run instead",
        )

    async def event_stream() -> AsyncIterator[str]:
        async for event in service.run_stream(
            agent, current_user.company_id, data.message, data.variables
        ):
            if event["type"] == "done":
                event = {
                    "type": "done",
                    "run": AgentRunResponse.model_validate(event["run"]).model_dump(mode="json"),
                }
            yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@runs_router.get("", response_model=list[AgentRunResponse])
async def list_agent_runs(
    service: ServiceDep,
    current_user: CurrentUserDep,
    agent_id: UUID | None = None,
    limit: int = 50,
    offset: int = 0,
) -> list[AgentRunResponse]:
    runs = await service.list_runs(
        current_user.company_id, agent_id=agent_id, limit=limit, offset=offset
    )
    return [AgentRunResponse.model_validate(run) for run in runs]


@runs_router.get("/{run_id}", response_model=AgentRunResponse)
async def get_agent_run(
    run_id: UUID, service: ServiceDep, current_user: CurrentUserDep
) -> AgentRunResponse:
    run = await service.get_run_for_company(run_id, current_user.company_id)
    if run is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Agent run not found")
    return AgentRunResponse.model_validate(run)


@runs_router.patch("/{run_id}", response_model=AgentRunResponse)
async def update_agent_run(
    run_id: UUID,
    data: AgentRunUpdate,
    service: ServiceDep,
    current_user: CurrentUserDep,
) -> AgentRunResponse:
    try:
        run = await service.update_run_output(run_id, current_user.company_id, data.text)
    except AgentRunNotEditableError as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, "This run has no output yet to edit") from exc
    if run is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Agent run not found")
    return AgentRunResponse.model_validate(run)


@runs_router.post("/{run_id}/apply", response_model=AgentRunApplyResponse)
async def apply_agent_run(
    run_id: UUID,
    service: ServiceDep,
    session: SessionDep,
    current_user: CurrentUserDep,
) -> AgentRunApplyResponse:
    """Applies a completed run's structured output using the handler
    registered for its agent's `output_action` (see `actions.py`) — e.g.
    creating/updating the company's brand archetype profile from a run of
    an agent configured with `output_action=apply_brand_archetype`."""
    run = await service.get_run_for_company(run_id, current_user.company_id)
    if run is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Agent run not found")

    agent = await service.get_visible_to_company(run.agent_id, current_user.company_id)
    if agent is None or agent.output_action == "none":
        raise HTTPException(status.HTTP_409_CONFLICT, "This agent has no action to apply")

    if run.output is None or run.output.get("data") is None:
        raise HTTPException(status.HTTP_409_CONFLICT, "This run has no structured output to apply")

    handler = ACTION_HANDLERS.get(agent.output_action)
    if handler is None:
        raise HTTPException(status.HTTP_409_CONFLICT, "Unknown action")

    try:
        result = await handler(session, current_user.company_id, run.output["data"])
    except AgentRunNotApplicableError as exc:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY, f"Could not apply run output: {exc}"
        ) from exc

    return AgentRunApplyResponse(action=agent.output_action, result=result)


@runs_router.get("/{run_id}/video")
async def get_agent_run_video(
    run_id: UUID, service: ServiceDep, current_user: CurrentUserDep
) -> StreamingResponse:
    """Proxies the generated video's bytes from OpenAI — never a direct
    OpenAI URL, since downloading requires our server-side API key. Note:
    OpenAI expires video content ~48h after generation, so this can start
    raising (uncaught OpenAI SDK error, not `AgentVideoNotAvailableError`)
    for old runs once the content is gone server-side — there is no
    re-hosting to our own storage yet."""
    run = await service.get_run_for_company(run_id, current_user.company_id)
    if run is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Agent run not found")

    try:
        content = await service.get_video_content(run)
    except AgentVideoNotAvailableError as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, "Video not available for this run") from exc

    return StreamingResponse(iter([content]), media_type="video/mp4")


@runs_router.get("/{run_id}/image")
async def get_agent_run_image(
    run_id: UUID, service: ServiceDep, current_user: CurrentUserDep
) -> StreamingResponse:
    """Proxies generated image bytes from the run output. The image itself is
    stored as base64 in `agent_runs.output` for now; this endpoint keeps the
    frontend contract consistent with video, which also needs authenticated
    backend fetching instead of a public vendor URL."""
    run = await service.get_run_for_company(run_id, current_user.company_id)
    if run is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Agent run not found")

    try:
        content, media_type = await service.get_image_content(run)
    except AgentImageNotAvailableError as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, "Image not available for this run") from exc

    return StreamingResponse(iter([content]), media_type=media_type)
