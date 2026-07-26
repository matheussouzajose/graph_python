"""ORM model for company-owned agent definitions.

An `Agent` is entirely data-defined — its behavior is `system_prompt` +
model params, not code — so a company can create as many as it wants without
a deploy. This is unlike `IntegrationProvider` (where a new provider needs a
new `ERPClient` implementation): there is no per-agent code, no
kind/factory registry here.

`company_id` is always the owner (never null, same as every other feature
slice) — ownership decides who can edit/delete. `is_global`, when true,
additionally makes the agent visible/runnable by every other company
(read-only to them), without giving up ownership. See `repository.py` for
the "owned" vs "visible" query split.
"""

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import ARRAY, Boolean, DateTime, Float, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.infrastructure.database.base import Base


class AgentORM(Base):
    __tablename__ = "agents"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    company_id: Mapped[UUID] = mapped_column(
        ForeignKey("companies.id", ondelete="CASCADE", name="fk_agents_company_id"),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    category: Mapped[str | None] = mapped_column(String(100), nullable=True)
    # Lightweight metadata for discovery/filtering in the agent library.
    # `category` is the broad shelf ("Marketing", "Vídeo", ...), while tags
    # and skills describe domain/context ("ecommerce", "fashion") and
    # capability ("storyboard", "campanhas").
    tags: Mapped[list[str]] = mapped_column(ARRAY(String), nullable=False, default=list)
    skills: Mapped[list[str]] = mapped_column(ARRAY(String), nullable=False, default=list)
    description: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    # "chat" | "image_to_video" — see `AgentKind` in schemas.py. Unlike
    # `system_prompt` (data), this genuinely changes *how* the agent
    # executes — a chat completion vs. submitting a job to OpenAI's Sora
    # video API — so it's the one place agent behavior is a real code
    # branch (see `service.py::run`), not just config.
    kind: Mapped[str] = mapped_column(String(20), nullable=False, default="chat")
    # Free-text guidance shown to whoever *runs* the agent (what to type, what
    # to expect back) — distinct from `system_prompt`, which is the model's
    # instructions and isn't meant to be read by an end user.
    usage_instructions: Mapped[str | None] = mapped_column(Text, nullable=True)
    # For "chat": the LLM system prompt. For "image_to_video": the base
    # creative direction, prepended to the per-run message before being sent
    # to Sora as the video prompt.
    system_prompt: Mapped[str] = mapped_column(Text, nullable=False)
    # Falls back to `settings.OPENAI_CHAT_MODEL` at run time when null and
    # kind="chat". For kind="image_to_video", the model name in whatever
    # vocabulary `video_provider` uses (Sora: "sora-2"/"sora-2-pro";
    # OpenRouter: "google/veo-3.1", "kwaivgi/kling-v3.0", ...).
    model: Mapped[str | None] = mapped_column(String(100), nullable=True)
    temperature: Mapped[float] = mapped_column(Float, nullable=False, default=0.3)
    # kind="image_to_video" only. "openai" (Sora, one reference image, no
    # deploy needed elsewhere in the codebase) or "openrouter" (fronts
    # several vendors — Veo, Kling, Wan — supports multiple reference
    # images depending on the chosen `model`). See
    # `video_providers/factory.py`. Immutable after creation, same
    # reasoning as `kind`: the rest of this agent's config
    # (`model`/`video_size`/`video_seconds`) is in that provider's
    # vocabulary and wouldn't carry over to a different one.
    video_provider: Mapped[str] = mapped_column(String(20), nullable=False, default="openai")
    # kind="image_to_video" only, in whatever vocabulary `video_provider`
    # uses (Sora: exact pixel size e.g. "720x1280"; OpenRouter: a
    # resolution label e.g. "1080p"). Null falls back to the provider's own
    # default at run time — see `video_providers/*.py`.
    video_size: Mapped[str | None] = mapped_column(String(20), nullable=True)
    video_seconds: Mapped[str | None] = mapped_column(String(5), nullable=True)
    # When true, the company's brand_archetype_profile (if any) is rendered
    # into a context block and prepended to `system_prompt` at run time —
    # see `app.features.brand_archetype.formatting.format_brand_archetype_context`.
    uses_brand_archetype: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    # "text" | "json" — see `AgentResponseFormat` in schemas.py. "json" asks
    # the model for a JSON object (OpenAI JSON mode) and best-effort parses
    # it into `AgentRunORM.output["data"]`; no schema enforcement (yet).
    response_format: Mapped[str] = mapped_column(String(20), nullable=False, default="text")
    # "none" | "apply_brand_archetype" — see `AgentOutputAction` in schemas.py
    # and `actions.py`. Declares which registered handler (real code, keyed
    # by this string) a completed run's structured output can be applied
    # with via `POST /agent-runs/{id}/apply` — e.g. writing it into the
    # company's `brand_archetype_profile`. "none" means the run's output is
    # display-only. New actions are added by registering a new handler in
    # `actions.py`, never by changing how agents execute.
    output_action: Mapped[str] = mapped_column(String(50), nullable=False, default="none")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_global: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
