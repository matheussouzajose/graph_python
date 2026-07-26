from datetime import datetime
from enum import StrEnum
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


class AgentResponseFormat(StrEnum):
    TEXT = "text"
    JSON = "json"


class AgentKind(StrEnum):
    """How an agent executes — see `orm.py::AgentORM.kind`. Unlike every
    other agent field, this is a real code branch in `service.py::run`, not
    just configuration."""

    CHAT = "chat"
    IMAGE_TO_TEXT = "image_to_text"
    TEXT_TO_VIDEO = "text_to_video"
    IMAGE_TO_VIDEO = "image_to_video"
    TEXT_TO_IMAGE = "text_to_image"
    IMAGE_TO_IMAGE = "image_to_image"


class AgentVideoProvider(StrEnum):
    """kind="image_to_video" only — which `VideoProvider` (see
    video_providers/factory.py) executes the job. "openai" (Sora) accepts
    exactly one reference image; "openrouter" fronts several vendors (Veo,
    Kling, Wan, ...) and accepts more, depending on the chosen `model`.
    Immutable after creation — see `AgentUpdate`."""

    OPENAI = "openai"
    OPENROUTER = "openrouter"


class AgentOutputAction(StrEnum):
    """Which registered handler (see `actions.py`) a completed run's
    structured output can be applied with. "none" means display-only."""

    NONE = "none"
    APPLY_BRAND_ARCHETYPE = "apply_brand_archetype"


class AgentCreate(BaseModel):
    company_id: UUID
    name: str = Field(min_length=1, max_length=255)
    category: str | None = Field(default=None, max_length=100)
    tags: list[str] = Field(default_factory=list)
    skills: list[str] = Field(default_factory=list)
    description: str | None = Field(default=None, max_length=1000)
    kind: AgentKind = AgentKind.CHAT
    usage_instructions: str | None = None
    system_prompt: str = Field(min_length=1)
    model: str | None = None
    temperature: float = 0.3
    uses_brand_archetype: bool = False
    response_format: AgentResponseFormat = AgentResponseFormat.TEXT
    output_action: AgentOutputAction = AgentOutputAction.NONE
    video_provider: AgentVideoProvider = AgentVideoProvider.OPENAI
    video_size: str | None = Field(default=None, max_length=20)
    video_seconds: str | None = Field(default=None, max_length=5)
    image_size: str | None = Field(default=None, max_length=20)
    image_quality: str | None = Field(default=None, max_length=20)
    image_format: str | None = Field(default=None, max_length=10)
    is_active: bool = True
    # Only company admins may set this true — makes the agent visible/runnable
    # (read-only) by every other company. Enforced in router.py, not here.
    is_global: bool = False

    @field_validator("tags", "skills")
    @classmethod
    def normalize_metadata_list(cls, values: list[str]) -> list[str]:
        normalized: list[str] = []
        seen: set[str] = set()
        for value in values:
            item = value.strip()
            if not item or item in seen:
                continue
            normalized.append(item)
            seen.add(item)
        return normalized


class AgentUpdate(BaseModel):
    """`company_id` and `kind` are intentionally not editable — switching
    what an agent *fundamentally is* means deleting and recreating it.
    `video_provider` IS editable (unlike an earlier version of this
    comment claimed): `model`/`video_size`/`video_seconds` are in that
    provider's own vocabulary and won't automatically carry over when you
    switch, but that's exactly the kind of mistake (e.g. an OpenRouter
    model string left behind after switching back to `openai`) this field
    needs to stay editable to let someone fix, rather than forcing a
    delete-and-recreate.
    """

    name: str | None = Field(default=None, min_length=1, max_length=255)
    category: str | None = Field(default=None, max_length=100)
    tags: list[str] | None = None
    skills: list[str] | None = None
    description: str | None = Field(default=None, max_length=1000)
    usage_instructions: str | None = None
    system_prompt: str | None = Field(default=None, min_length=1)
    model: str | None = None
    temperature: float | None = None
    uses_brand_archetype: bool | None = None
    response_format: AgentResponseFormat | None = None
    output_action: AgentOutputAction | None = None
    video_provider: AgentVideoProvider | None = None
    video_size: str | None = Field(default=None, max_length=20)
    video_seconds: str | None = Field(default=None, max_length=5)
    image_size: str | None = Field(default=None, max_length=20)
    image_quality: str | None = Field(default=None, max_length=20)
    image_format: str | None = Field(default=None, max_length=10)
    is_active: bool | None = None
    is_global: bool | None = None

    @field_validator("tags", "skills")
    @classmethod
    def normalize_metadata_list(cls, values: list[str] | None) -> list[str] | None:
        if values is None:
            return None
        normalized: list[str] = []
        seen: set[str] = set()
        for value in values:
            item = value.strip()
            if not item or item in seen:
                continue
            normalized.append(item)
            seen.add(item)
        return normalized


class AgentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    company_id: UUID
    name: str
    category: str | None
    tags: list[str]
    skills: list[str]
    description: str | None
    kind: str
    usage_instructions: str | None
    system_prompt: str
    model: str | None
    temperature: float
    uses_brand_archetype: bool
    response_format: str
    output_action: str
    video_provider: str
    video_size: str | None
    video_seconds: str | None
    image_size: str | None
    image_quality: str | None
    image_format: str | None
    is_active: bool
    is_global: bool
    created_at: datetime
    updated_at: datetime


class AgentGlobalSeedResponse(BaseModel):
    created: list[AgentResponse]
    skipped: list[AgentResponse]


class AgentRunRequest(BaseModel):
    message: str = Field(min_length=1)
    variables: dict[str, Any] = Field(default_factory=dict)
    # Media agents use selected catalog image URLs:
    # - image_to_video: one or more depending on `video_provider`
    # - image_to_text: one or more images to analyze
    # - image_to_image: one or more reference images
    # - text_to_image/text_to_video/chat: ignored
    image_urls: list[str] = Field(default_factory=list)


class AgentRunOutput(BaseModel):
    text: str
    data: dict[str, Any] | None = None
    # Set once a kind="image_to_video" run completes — path to
    # `GET /agent-runs/{id}/video`, which proxies the bytes from whichever
    # `video_provider` generated it (never a direct vendor URL — that may
    # require our server-side API key, e.g. Sora's).
    video_url: str | None = None
    image_url: str | None = None


class AgentRunResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    agent_id: UUID
    company_id: UUID
    input: dict[str, Any]
    output: AgentRunOutput | None
    status: str
    error: str | None
    created_at: datetime
    updated_at: datetime


class AgentRunUpdate(BaseModel):
    """Lets the user hand-edit a run's output text after the fact — the
    LLM's answer is a draft, not a final artifact."""

    text: str = Field(min_length=1)


class AgentRunApplyResponse(BaseModel):
    """Result of `POST /agent-runs/{id}/apply` — `result` shape depends on
    which action ran (e.g. a `BrandArchetypeProfileResponse` dict for
    `apply_brand_archetype`)."""

    action: str
    result: dict[str, Any]
