"""ORM model for agent execution history.

One row per `POST /agents/{id}/run` call. For `kind="chat"` agents, `status`
goes straight to `completed`/`failed` before the request returns — for
`kind="image_to_video"`, the request only submits the job (`status="running"`,
`external_job_id` set to Sora's video id) and `video_worker.py` polls it to
completion in the background, exactly the seam this table's docstring
originally called out ("a future heavy agent... without a schema change,
just a new consumer process").
"""

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import DateTime, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.infrastructure.database.base import Base


class AgentRunORM(Base):
    __tablename__ = "agent_runs"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    agent_id: Mapped[UUID] = mapped_column(
        ForeignKey("agents.id", ondelete="CASCADE", name="fk_agent_runs_agent_id"),
        nullable=False,
    )
    company_id: Mapped[UUID] = mapped_column(
        ForeignKey("companies.id", ondelete="CASCADE", name="fk_agent_runs_company_id"),
        nullable=False,
    )
    # {"message": str, "variables": dict, "image_urls": list[str]}
    input: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    # {"text": str, "data": dict | None, "video_url": str | None} — null
    # until the run finishes.
    output: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    # "pending" | "running" | "completed" | "failed"
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    error: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    # Sora's video id (kind="image_to_video" only) — lets `video_worker.py`
    # poll `GET /v1/videos/{id}` and lets the video proxy endpoint know what
    # to download. Null for chat runs and for video runs that failed before
    # submission succeeded.
    external_job_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
