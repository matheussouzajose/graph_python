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

import asyncio
import base64
import json
from collections.abc import AsyncIterator, Sequence
from typing import Any
from uuid import UUID

import httpx
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from openai import OpenAI

from app.core.config import settings
from app.features.agents.default_agents import load_moda_b2b_global_agent_payloads
from app.features.agents.orm import AgentORM
from app.features.agents.repository import AgentRepository
from app.features.agents.run_orm import AgentRunORM
from app.features.agents.run_repository import AgentRunRepository
from app.features.agents.schemas import AgentCreate, AgentUpdate
from app.features.agents.video_providers.factory import get_video_provider
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


class AgentImageNotAvailableError(Exception):
    """Raised when trying to download an image for a run that didn't produce one."""


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

    async def list(
        self,
        company_id: UUID,
        limit: int = 100,
        offset: int = 0,
        category: str | None = None,
    ) -> Sequence[AgentORM]:
        return await self._repository.list_visible_to_company(
            company_id, limit=limit, offset=offset, category=category
        )

    async def update(self, agent_id: UUID, data: AgentUpdate) -> AgentORM | None:
        return await self._repository.update(agent_id, data)

    async def delete(self, agent_id: UUID) -> bool:
        return await self._repository.delete(agent_id)

    async def seed_moda_b2b_global_agents(
        self, owner_company_id: UUID
    ) -> tuple[list[AgentORM], list[AgentORM]]:
        created: list[AgentORM] = []
        skipped: list[AgentORM] = []
        for payload in load_moda_b2b_global_agent_payloads(owner_company_id):
            existing = await self._repository.get_global_by_name(payload.name)
            if existing is not None:
                skipped.append(existing)
                continue
            created.append(await self.create(payload))
        return created, skipped

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

        if agent.kind in {"text_to_video", "image_to_video"}:
            return await self._run_video(agent, requesting_company_id, message, image_urls or [])

        if agent.kind == "image_to_text":
            return await self._run_image_to_text(
                agent, requesting_company_id, message, variables, image_urls or []
            )

        if agent.kind in {"text_to_image", "image_to_image"}:
            return await self._run_image(agent, requesting_company_id, message, image_urls or [])

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
        """Submits a job to `agent.video_provider` and returns immediately
        with `status="running"` — the actual render is polled by
        `video_worker.py`, not awaited here (it can take minutes, far too
        long for one HTTP request). How many images are actually allowed is
        the provider's call (Sora wants exactly one; OpenRouter varies by
        model) — see `video_providers/*.py`, not validated here."""
        if agent.kind == "image_to_video" and not image_urls:
            raise AgentInvalidRunInputError("Selecione ao menos uma imagem.")

        run = await self._run_repository.create(
            agent_id=agent.id,
            company_id=requesting_company_id,
            input_data={"message": message, "variables": {}, "image_urls": image_urls},
        )

        prompt_parts = [part.strip() for part in (agent.system_prompt, message) if part.strip()]
        if agent.uses_brand_archetype:
            profile = await self._brand_archetype_repository.get_by_company_id(
                requesting_company_id
            )
            if profile is not None:
                context = format_brand_archetype_context(profile)
                prompt_parts.append(f"Contexto de marca:\n{context}")
        prompt = "\n\n".join(prompt_parts)

        try:
            provider = get_video_provider(agent.video_provider)
            video_id = await provider.submit_video_job(
                prompt=prompt,
                image_urls=image_urls,
                model=agent.model,
                size=agent.video_size,
                seconds=agent.video_seconds,
            )
        except Exception as exc:
            return await self._run_repository.mark_failed(run, str(exc))

        return await self._run_repository.mark_running(run, video_id)

    async def _run_image_to_text(
        self,
        agent: AgentORM,
        requesting_company_id: UUID,
        message: str,
        variables: dict[str, Any],
        image_urls: list[str],
    ) -> AgentRunORM:
        if not image_urls:
            raise AgentInvalidRunInputError("Selecione ao menos uma imagem para analisar.")

        run = await self._run_repository.create(
            agent_id=agent.id,
            company_id=requesting_company_id,
            input_data={"message": message, "variables": variables, "image_urls": image_urls},
        )

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

        content: list[dict[str, Any]] = [{"type": "text", "text": message}]
        if variables:
            content.append(
                {
                    "type": "text",
                    "text": (
                        "Contexto adicional (JSON):\n"
                        f"{json.dumps(variables, ensure_ascii=False)}"
                    ),
                }
            )
        content.extend(
            {"type": "image_url", "image_url": {"url": image_url}} for image_url in image_urls
        )

        try:
            llm = ChatOpenAI(
                model=agent.model or settings.OPENAI_CHAT_MODEL,
                temperature=agent.temperature,
                api_key=settings.OPENAI_API_KEY,
            )
            response = await llm.ainvoke(
                [SystemMessage(content=system_prompt), HumanMessage(content=content)]
            )
            output = {"text": str(response.content), "data": None}
        except Exception as exc:
            return await self._run_repository.mark_failed(run, str(exc))

        return await self._run_repository.mark_completed(run, output)

    async def _run_image(
        self,
        agent: AgentORM,
        requesting_company_id: UUID,
        message: str,
        image_urls: list[str],
    ) -> AgentRunORM:
        if agent.kind == "image_to_image" and not image_urls:
            raise AgentInvalidRunInputError("Selecione ao menos uma imagem de referência.")

        run = await self._run_repository.create(
            agent_id=agent.id,
            company_id=requesting_company_id,
            input_data={"message": message, "variables": {}, "image_urls": image_urls},
        )

        prompt_parts = [part.strip() for part in (agent.system_prompt, message) if part.strip()]
        if agent.uses_brand_archetype:
            profile = await self._brand_archetype_repository.get_by_company_id(
                requesting_company_id
            )
            if profile is not None:
                prompt_parts.append(
                    f"Contexto de marca:\n{format_brand_archetype_context(profile)}"
                )
        prompt = "\n\n".join(prompt_parts)

        try:
            image = await self._generate_image(agent, prompt, image_urls)
        except Exception as exc:
            return await self._run_repository.mark_failed(run, str(exc))

        output = {
            "text": message,
            "data": None,
            "video_url": None,
            "image_url": f"/agent-runs/{run.id}/image",
            "image_b64": image["b64_json"],
            "image_format": image["format"],
        }
        return await self._run_repository.mark_completed(run, output)

    async def _generate_image(
        self, agent: AgentORM, prompt: str, image_urls: list[str]
    ) -> dict[str, str]:
        client = OpenAI(api_key=settings.OPENAI_API_KEY)
        model = agent.model or settings.OPENAI_IMAGE_MODEL
        output_format = agent.image_format or "png"
        kwargs: dict[str, Any] = {
            "model": model,
            "prompt": prompt,
            "size": agent.image_size or "1024x1536",
            "quality": agent.image_quality or "medium",
            "output_format": output_format,
            "response_format": "b64_json",
        }

        if image_urls:
            images = []
            for index, image_url in enumerate(image_urls, start=1):
                image_bytes = await _download_image(image_url)
                images.append((f"reference-{index}.png", image_bytes, "image/png"))
            result = await asyncio.to_thread(client.images.edit, image=images, **kwargs)
        else:
            result = await asyncio.to_thread(client.images.generate, **kwargs)

        if not result.data or not result.data[0].b64_json:
            raise AgentInvalidRunInputError("A geração de imagem não retornou conteúdo.")

        return {"b64_json": result.data[0].b64_json, "format": output_format}

    async def check_video_job(self, run: AgentRunORM) -> AgentRunORM:
        """Polls one running video job and settles the run if it's done —
        called by `video_worker.py`, never from a request handler."""
        if run.external_job_id is None:
            return run

        agent = await self._repository.get(run.agent_id)
        if agent is None:
            return run

        provider = get_video_provider(agent.video_provider)
        job_status = await provider.get_video_status(run.external_job_id)

        if job_status.status == "completed":
            output = {
                "text": run.input.get("message") or "",
                "data": None,
                "video_url": f"/agent-runs/{run.id}/video",
            }
            return await self._run_repository.mark_completed(run, output)

        if job_status.status == "failed":
            return await self._run_repository.mark_failed(
                run, job_status.error or "Falha na geração do vídeo"
            )

        return run

    async def get_video_content(self, run: AgentRunORM) -> bytes:
        if run.status != "completed" or run.external_job_id is None:
            raise AgentVideoNotAvailableError

        agent = await self._repository.get(run.agent_id)
        if agent is None:
            raise AgentVideoNotAvailableError

        provider = get_video_provider(agent.video_provider)
        return await provider.download_video_bytes(run.external_job_id)

    async def get_image_content(self, run: AgentRunORM) -> tuple[bytes, str]:
        if run.status != "completed" or run.output is None:
            raise AgentImageNotAvailableError

        image_b64 = run.output.get("image_b64")
        if not isinstance(image_b64, str):
            raise AgentImageNotAvailableError

        image_format = run.output.get("image_format")
        if image_format not in {"png", "jpeg", "webp"}:
            image_format = "png"

        return base64.b64decode(image_b64), f"image/{image_format}"

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


async def _download_image(image_url: str) -> bytes:
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(image_url)
        response.raise_for_status()
    return response.content
