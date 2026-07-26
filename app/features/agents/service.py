"""Business logic layer for the agents library.

`create`/`get`/`list`/`update`/`delete` are catalog CRUD for `Agent`, scoped
to a company — each company creates and owns its own agents, no shared
catalog, no per-agent code (see `orm.py`). `run` is the execution path: it
optionally renders the company's brand archetype into the prompt, calls the
LLM, and persists an `AgentRun`. Every rule is validated explicitly here
(company must exist, agent must be active before running) — never delegated
to a database constraint.
"""

from __future__ import annotations

import json
from collections.abc import AsyncIterator, Sequence
from typing import Any
from uuid import UUID

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

from app.core.config import settings
from app.features.agents import video_client
from app.features.agents.orm import AgentORM
from app.features.agents.repository import AgentRepository
from app.features.agents.run_orm import AgentRunORM
from app.features.agents.run_repository import AgentRunRepository
from app.features.agents.schemas import AgentCreate, AgentUpdate
from app.features.brand_archetype.formatting import format_brand_archetype_context
from app.features.brand_archetype.repository import BrandArchetypeProfileRepository
from app.features.company.repository import CompanyRepository


class CompanyNotFoundError(Exception):
    """Raised when `company_id` does not reference an existing company."""


class AgentNotActiveError(Exception):
    """Raised when trying to run an agent whose `is_active` is False."""


class AgentRunNotEditableError(Exception):
    """Raised when trying to edit the output of a run that has none yet
    (still pending, or failed)."""


class AgentInvalidRunInputError(Exception):
    """Raised when a run's input doesn't match what the agent's `kind`
    requires (e.g. `image_to_video` needs exactly one image URL)."""


class AgentKindNotStreamableError(Exception):
    """Raised when `run_stream` is called on a non-"chat" agent — there is
    no token stream for a video generation job."""


class AgentVideoNotAvailableError(Exception):
    """Raised when trying to download a video for a run that isn't a
    completed `image_to_video` run."""


class AgentService:
    def __init__(
        self,
        repository: AgentRepository,
        run_repository: AgentRunRepository,
        company_repository: CompanyRepository,
        brand_archetype_repository: BrandArchetypeProfileRepository,
    ) -> None:
        self._repository = repository
        self._run_repository = run_repository
        self._company_repository = company_repository
        self._brand_archetype_repository = brand_archetype_repository

    async def create(self, data: AgentCreate) -> AgentORM:
        company = await self._company_repository.get(data.company_id)
        if company is None:
            raise CompanyNotFoundError
        return await self._repository.create(data)

    async def get(self, agent_id: UUID) -> AgentORM | None:
        return await self._repository.get(agent_id)

    async def get_owned_by_company(self, agent_id: UUID, company_id: UUID) -> AgentORM | None:
        return await self._repository.get_owned_by_company(agent_id, company_id)

    async def get_visible_to_company(self, agent_id: UUID, company_id: UUID) -> AgentORM | None:
        return await self._repository.get_visible_to_company(agent_id, company_id)

    async def list(self, company_id: UUID, limit: int = 100, offset: int = 0) -> Sequence[AgentORM]:
        return await self._repository.list_visible_to_company(
            company_id, limit=limit, offset=offset
        )

    async def update(self, agent_id: UUID, data: AgentUpdate) -> AgentORM | None:
        return await self._repository.update(agent_id, data)

    async def delete(self, agent_id: UUID) -> bool:
        return await self._repository.delete(agent_id)

    async def get_run_for_company(self, run_id: UUID, company_id: UUID) -> AgentRunORM | None:
        return await self._run_repository.get_for_company(run_id, company_id)

    async def list_runs(
        self,
        company_id: UUID,
        agent_id: UUID | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> Sequence[AgentRunORM]:
        return await self._run_repository.list_for_company(
            company_id, agent_id=agent_id, limit=limit, offset=offset
        )

    async def update_run_output(
        self, run_id: UUID, company_id: UUID, text: str
    ) -> AgentRunORM | None:
        """Lets the requesting company hand-edit a completed run's output —
        the LLM's answer is a draft, not a final artifact."""
        run = await self._run_repository.get_for_company(run_id, company_id)
        if run is None:
            return None
        if run.output is None:
            raise AgentRunNotEditableError
        return await self._run_repository.update_output_text(run, text)

    async def run(
        self,
        agent: AgentORM,
        requesting_company_id: UUID,
        message: str,
        variables: dict[str, Any],
        image_urls: list[str] | None = None,
    ) -> AgentRunORM:
        """`requesting_company_id` is who is *running* the agent, which for a
        global agent (`is_global=True`) differs from `agent.company_id` (the
        owner). The run — and, critically, which company's brand archetype
        gets injected — is always scoped to the requester, never the owner.
        """
        if not agent.is_active:
            raise AgentNotActiveError

        if agent.kind == "image_to_video":
            return await self._run_video(agent, requesting_company_id, message, image_urls or [])

        run = await self._run_repository.create(
            agent_id=agent.id,
            company_id=requesting_company_id,
            input_data={"message": message, "variables": variables},
        )

        system_prompt, human_content, model_kwargs = await self._build_prompt(
            agent, requesting_company_id, message, variables
        )

        try:
            llm = ChatOpenAI(
                model=agent.model or settings.OPENAI_CHAT_MODEL,
                temperature=agent.temperature,
                api_key=settings.OPENAI_API_KEY,
                model_kwargs=model_kwargs,
            )
            response = await llm.ainvoke(
                [SystemMessage(content=system_prompt), HumanMessage(content=human_content)]
            )
            output = self._parse_output(agent, str(response.content))
        except Exception as exc:
            return await self._run_repository.mark_failed(run, str(exc))

        return await self._run_repository.mark_completed(run, output)

    async def _run_video(
        self,
        agent: AgentORM,
        requesting_company_id: UUID,
        message: str,
        image_urls: list[str],
    ) -> AgentRunORM:
        """Submits a Sora job and returns immediately with `status="running"`
        — the actual render is polled by `video_worker.py`, not awaited here
        (it can take minutes, far too long for one HTTP request)."""
        if len(image_urls) != 1:
            raise AgentInvalidRunInputError(
                "Selecione exatamente uma imagem — este agente gera um vídeo por vez."
            )

        run = await self._run_repository.create(
            agent_id=agent.id,
            company_id=requesting_company_id,
            input_data={"message": message, "variables": {}, "image_urls": image_urls},
        )

        prompt_parts = [part.strip() for part in (agent.system_prompt, message) if part.strip()]
        prompt = "\n\n".join(prompt_parts)

        try:
            video_id = await video_client.submit_video_job(
                prompt=prompt,
                image_url=image_urls[0],
                model=agent.model or video_client.DEFAULT_VIDEO_MODEL,
                size=agent.video_size or video_client.DEFAULT_VIDEO_SIZE,
                seconds=agent.video_seconds or video_client.DEFAULT_VIDEO_SECONDS,
            )
        except Exception as exc:
            return await self._run_repository.mark_failed(run, str(exc))

        return await self._run_repository.mark_running(run, video_id)

    async def check_video_job(self, run: AgentRunORM) -> AgentRunORM:
        """Polls Sora for one running video job and settles the run if it's
        done — called by `video_worker.py`, never from a request handler."""
        if run.external_job_id is None:
            return run

        video = await video_client.get_video_status(run.external_job_id)

        if video.status == "completed":
            output = {
                "text": run.input.get("message") or "",
                "data": None,
                "video_url": f"/agent-runs/{run.id}/video",
            }
            return await self._run_repository.mark_completed(run, output)

        if video.status == "failed":
            error_message = getattr(video, "error", None) or "Falha na geração do vídeo"
            return await self._run_repository.mark_failed(run, str(error_message))

        return run

    async def get_video_content(self, run: AgentRunORM) -> bytes:
        if run.status != "completed" or run.external_job_id is None:
            raise AgentVideoNotAvailableError
        return await video_client.download_video_bytes(run.external_job_id)

    async def run_stream(
        self,
        agent: AgentORM,
        requesting_company_id: UUID,
        message: str,
        variables: dict[str, Any],
    ) -> AsyncIterator[dict[str, Any]]:
        """Same execution as `run`, but yields `{"type": "token", "text": ...}`
        as chunks arrive from the LLM, ending in either `{"type": "done",
        "run": AgentRunORM}` or `{"type": "error", "message": ...}` — the
        `AgentRun` row is still persisted exactly once at the end, same as
        the non-streaming path."""
        if not agent.is_active:
            raise AgentNotActiveError
        if agent.kind != "chat":
            raise AgentKindNotStreamableError

        run = await self._run_repository.create(
            agent_id=agent.id,
            company_id=requesting_company_id,
            input_data={"message": message, "variables": variables},
        )

        system_prompt, human_content, model_kwargs = await self._build_prompt(
            agent, requesting_company_id, message, variables
        )

        text = ""
        try:
            llm = ChatOpenAI(
                model=agent.model or settings.OPENAI_CHAT_MODEL,
                temperature=agent.temperature,
                api_key=settings.OPENAI_API_KEY,
                model_kwargs=model_kwargs,
            )
            async for chunk in llm.astream(
                [SystemMessage(content=system_prompt), HumanMessage(content=human_content)]
            ):
                piece = str(chunk.content)
                if piece:
                    text += piece
                    yield {"type": "token", "text": piece}
        except Exception as exc:
            await self._run_repository.mark_failed(run, str(exc))
            yield {"type": "error", "message": str(exc)}
            return

        output = self._parse_output(agent, text)
        run = await self._run_repository.mark_completed(run, output)
        yield {"type": "done", "run": run}

    async def _build_prompt(
        self,
        agent: AgentORM,
        requesting_company_id: UUID,
        message: str,
        variables: dict[str, Any],
    ) -> tuple[str, str, dict[str, Any]]:
        system_prompt = agent.system_prompt
        if agent.uses_brand_archetype:
            profile = await self._brand_archetype_repository.get_by_company_id(
                requesting_company_id
            )
            if profile is not None:
                system_prompt = (
                    f"{system_prompt}\n\nContexto de marca:\n"
                    f"{format_brand_archetype_context(profile)}"
                )

        human_content = message
        if variables:
            human_content = (
                f"{message}\n\nContexto adicional (JSON):\n"
                f"{json.dumps(variables, ensure_ascii=False)}"
            )

        model_kwargs: dict[str, Any] = {}
        if agent.response_format == "json":
            system_prompt = f"{system_prompt}\n\nResponda somente com um objeto JSON válido."
            model_kwargs["response_format"] = {"type": "json_object"}

        return system_prompt, human_content, model_kwargs

    def _parse_output(self, agent: AgentORM, text: str) -> dict[str, Any]:
        data = None
        if agent.response_format == "json":
            try:
                data = json.loads(text)
            except json.JSONDecodeError:
                data = None
        return {"text": text, "data": data}
