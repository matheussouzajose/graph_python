"""Background worker that polls Sora for every `image_to_video` run stuck
in `status="running"` — mirrors `OrderSyncWorker`'s `run()`/`stop()` shape
(`app/features/order/sync_worker.py`).

Runs as a standalone process, separate from the API:

    uv run python -m app.features.agents.video_worker

Not wired into docker-compose (same as `order/sync_worker.py` and
`order/sync_consumer.py`) — the natural next step once this is actually
needed continuously. One run failing to poll (Sora outage, expired job) is
logged and skipped, it never blocks the rest of the round.

Recommended poll interval is 10-20s per OpenAI's guidance for the Videos
API — short enough that a user watching a run in the UI doesn't wait much
longer than necessary after the render actually finishes.
"""

import asyncio
import logging

from app.core.infrastructure.database.session import AsyncSessionFactory
from app.features.agents.repository import AgentRepository
from app.features.agents.run_repository import AgentRunRepository
from app.features.agents.service import AgentService
from app.features.brand_archetype.repository import BrandArchetypeProfileRepository
from app.features.company.repository import CompanyRepository

logger = logging.getLogger(__name__)


class VideoGenerationWorker:
    def __init__(self, poll_interval: float = 15.0) -> None:
        self._poll_interval = poll_interval
        self._running = False

    async def run(self) -> None:
        self._running = True
        logger.info("Video generation worker started (poll_interval=%.0fs)", self._poll_interval)
        while self._running:
            try:
                await self._poll_once()
            except Exception:
                logger.exception("Video poll round failed; retrying next interval")
            await asyncio.sleep(self._poll_interval)

    async def _poll_once(self) -> None:
        async with AsyncSessionFactory() as session:
            run_repository = AgentRunRepository(session)
            service = AgentService(
                AgentRepository(session),
                run_repository,
                CompanyRepository(session),
                BrandArchetypeProfileRepository(session),
            )
            running_jobs = await run_repository.list_running_video_jobs()

            for run in running_jobs:
                try:
                    updated = await service.check_video_job(run)
                    if updated.status != "running":
                        logger.info(
                            "Video run %s settled: %s (job %s)",
                            updated.id,
                            updated.status,
                            run.external_job_id,
                        )
                except Exception:
                    logger.exception("Failed polling video run %s", run.id)

            await session.commit()

    def stop(self) -> None:
        self._running = False


if __name__ == "__main__":
    asyncio.run(VideoGenerationWorker().run())
