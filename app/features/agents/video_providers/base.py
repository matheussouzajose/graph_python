"""Provider-agnostic contract for image-to-video generation.

Mirrors `app/features/integration/erp/base.py`'s `ERPClient` shape on
purpose: the rest of the app (`AgentService`) only depends on
`VideoProvider`, never on a specific vendor's SDK/HTTP shape. Onboarding a
new provider (direct Veo, direct Kling, ...) means adding one new client
module + one branch in `factory.py` — nothing in `AgentService` changes.

Every provider interprets `model`/`size`/`seconds` in its own vocabulary
(e.g. OpenAI's `size="720x1280"` vs OpenRouter's `resolution="1080p"`) —
these are deliberately untyped strings at this boundary (see
`Agent.video_size`/`video_seconds` in schemas.py) rather than one shared
enum, because forcing every future provider into the same value space is
exactly the kind of coupling that would make switching providers hard
again. A provider that gets an invalid value for itself raises
`VideoProviderError` (or lets the vendor API's own error propagate) —
that's the vendor's validation to own, not ours to duplicate.
"""

from dataclasses import dataclass
from typing import Protocol


@dataclass
class VideoJobStatus:
    # Only "completed" and "failed" are ever branched on by
    # `AgentService.check_video_job` — everything else (each provider's own
    # "queued"/"pending"/"in_progress" vocabulary) is treated uniformly as
    # "still running", so adapters don't need to agree on it.
    status: str
    error: str | None = None


class VideoProvider(Protocol):
    async def submit_video_job(
        self,
        *,
        prompt: str,
        image_urls: list[str],
        model: str | None,
        size: str | None,
        seconds: str | None,
    ) -> str:
        """Submits a generation job and returns the provider's job id
        immediately — must not block until the video is ready."""
        ...

    async def get_video_status(self, job_id: str) -> VideoJobStatus: ...

    async def download_video_bytes(self, job_id: str) -> bytes: ...


class VideoProviderError(Exception):
    """Raised for a provider-specific input problem (e.g. wrong image
    count) caught before ever calling the vendor API."""


class UnsupportedVideoProviderError(Exception):
    """Raised when `Agent.video_provider` has no matching `VideoProvider`."""
