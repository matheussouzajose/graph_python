"""`VideoProvider` implementation over OpenRouter's video generation API.

Unlike Sora (`openai_sora.py`), OpenRouter's `/videos` endpoint is plain
JSON — reference images are passed as URLs directly (`input_references`),
no download/resize/multipart-upload dance needed. It also fronts several
underlying vendors (Veo, Kling, Wan, ...) behind one contract, which is the
whole point of offering it alongside Sora: switching the *model* later is a
config change (`Agent.model`), not a new integration.

`unsigned_urls` in a completed job's status response, despite the name,
still require our OpenRouter Authorization header to fetch (confirmed live
— omitting it gets a 401 "No cookie auth credentials found"; "unsigned"
apparently just means "no signature/token embedded in the URL itself").
"""

from __future__ import annotations

from typing import Any

import httpx

from app.core.config import settings
from app.core.logger import logger
from app.features.agents.video_providers.base import VideoJobStatus, VideoProviderError

BASE_URL = "https://openrouter.ai/api/v1/videos"
DEFAULT_MODEL = "google/veo-3.1-lite"
# Deliberately the cheapest valid combo, not the best-looking one: Veo 3.1
# bills per second and per resolution tier (confirmed live — 1080p/8s cost
# ~US$3.20 for one test run), so an accidental click shouldn't be
# expensive. 4s is the shortest duration this model accepts (confirmed
# live via the API's own 400: "Supported durations: 4, 6, 8s") — 1080p is
# available but priced higher, so it's opt-in via `Agent.video_size`, not
# the default.
DEFAULT_RESOLUTION = "1080p"
DEFAULT_SECONDS = "8"


class OpenRouterVideoProvider:
    def __init__(self) -> None:
        self._headers = {"Authorization": f"Bearer {settings.OPENROUTER_API_KEY}"}

    async def submit_video_job(
        self,
        *,
        prompt: str,
        image_urls: list[str],
        model: str | None,
        size: str | None,
        seconds: str | None,
    ) -> str:
        payload = {
            "model": model or DEFAULT_MODEL,
            "prompt": prompt,
            "resolution": size or DEFAULT_RESOLUTION,
            "duration": int(seconds or DEFAULT_SECONDS),
        }
        if image_urls:
            payload["input_references"] = [
                {"type": "image_url", "image_url": {"url": url}} for url in image_urls
            ]

        logger.info("OpenRouterProvider", payload)
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(BASE_URL, json=payload, headers=self._headers)
            _raise_for_status(response)
        return response.json()["id"]

    async def get_video_status(self, job_id: str) -> VideoJobStatus:
        data = await self._fetch_status(job_id)
        return VideoJobStatus(status=data["status"], error=data.get("error"))

    async def download_video_bytes(self, job_id: str) -> bytes:
        data = await self._fetch_status(job_id)
        urls = data.get("unsigned_urls") or []
        if not urls:
            raise VideoProviderError("Vídeo ainda não tem uma URL disponível.")
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(urls[0], headers=self._headers)
            _raise_for_status(response)
        return response.content

    async def _fetch_status(self, job_id: str) -> dict[str, Any]:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(f"{BASE_URL}/{job_id}", headers=self._headers)
            _raise_for_status(response)
        return response.json()


def _raise_for_status(response: httpx.Response) -> None:
    """`response.raise_for_status()` alone drops the response body — for a
    4xx this is almost always where the vendor's actual validation message
    lives (e.g. "resolution not supported by this model"), and that message
    is exactly what ends up in `AgentRun.error` for the user to see, so it
    must not be lost."""
    if response.is_success:
        return
    try:
        detail = response.json()
    except ValueError:
        detail = response.text
    raise VideoProviderError(f"OpenRouter {response.status_code}: {detail}")
