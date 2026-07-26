from datetime import datetime
from enum import StrEnum
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class AgentResponseFormat(StrEnum):
    TEXT = "text"
    JSON = "json"


class AgentKind(StrEnum):
    """How an agent executes — see `orm.py::AgentORM.kind`. Unlike every
    other agent field, this is a real code branch in `service.py::run`, not
    just configuration."""

    CHAT = "chat"
    IMAGE_TO_VIDEO = "image_to_video"


class VideoSize(StrEnum):
    """Sora output resolutions (width x height)."""

    PORTRAIT_SMALL = "720x1280"
    LANDSCAPE_SMALL = "1280x720"
    PORTRAIT_LARGE = "1024x1792"
    LANDSCAPE_LARGE = "1792x1024"


class VideoSeconds(StrEnum):
    FOUR = "4"
    EIGHT = "8"
    TWELVE = "12"


class AgentOutputAction(StrEnum):
    """Which registered handler (see `actions.py`) a completed run's
    structured output can be applied with. "none" means display-only."""

    NONE = "none"
    APPLY_BRAND_ARCHETYPE = "apply_brand_archetype"


class AgentCreate(BaseModel):
    company_id: UUID
    name: str = Field(min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=1000)
    kind: AgentKind = AgentKind.CHAT
    usage_instructions: str | None = None
    system_prompt: str = Field(min_length=1)
    model: str | None = None
    temperature: float = 0.3
    uses_brand_archetype: bool = False
    response_format: AgentResponseFormat = AgentResponseFormat.TEXT
    output_action: AgentOutputAction = AgentOutputAction.NONE
    video_size: VideoSize | None = None
    video_seconds: VideoSeconds | None = None
    is_active: bool = True
    # Only company admins may set this true — makes the agent visible/runnable
    # (read-only) by every other company. Enforced in router.py, not here.
    is_global: bool = False


class AgentUpdate(BaseModel):
    """`company_id` and `kind` are intentionally not editable — switching
    what an agent *is* means deleting and recreating it, same reasoning as
    `company_id`.
    """

    name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=1000)
    usage_instructions: str | None = None
    system_prompt: str | None = Field(default=None, min_length=1)
    model: str | None = None
    temperature: float | None = None
    uses_brand_archetype: bool | None = None
    response_format: AgentResponseFormat | None = None
    output_action: AgentOutputAction | None = None
    video_size: VideoSize | None = None
    video_seconds: VideoSeconds | None = None
    is_active: bool | None = None
    is_global: bool | None = None


class AgentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    company_id: UUID
    name: str
    description: str | None
    kind: str
    usage_instructions: str | None
    system_prompt: str
    model: str | None
    temperature: float
    uses_brand_archetype: bool
    response_format: str
    output_action: str
    video_size: str | None
    video_seconds: str | None
    is_active: bool
    is_global: bool
    created_at: datetime
    updated_at: datetime


class AgentRunRequest(BaseModel):
    message: str = Field(min_length=1)
    variables: dict[str, Any] = Field(default_factory=dict)
    # kind="image_to_video" only — exactly one image URL is expected today
    # (Sora's `input_reference` takes a single reference image; multiple
    # images would mean multiple separate video jobs, not supported yet).
    image_urls: list[str] = Field(default_factory=list)


class AgentRunOutput(BaseModel):
    text: str
    data: dict[str, Any] | None = None
    # Set once a kind="image_to_video" run completes — path to
    # `GET /agent-runs/{id}/video`, which proxies the bytes from OpenAI
    # (never a direct OpenAI URL — that requires our server-side API key).
    video_url: str | None = None


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
