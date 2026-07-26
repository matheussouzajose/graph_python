"""Thin async wrapper over OpenAI's Videos API (Sora).

The `openai` SDK's `client.videos.*` methods are synchronous, so every call
here goes through `asyncio.to_thread` — same pattern already used for
`app/features/rag/query_router.py`'s OpenAI/Neo4j calls, to avoid blocking
the event loop.

Note: OpenAI announced the Sora 2 video models/Videos API will be shut down
2026-09-24, with no successor announced yet — this integration is built
knowingly on top of that, not a long-term bet. Generated video content also
expires ~48h after creation (`Video.expires_at`), so `download_video_bytes`
must be called reasonably soon after `status` becomes "completed" — there is
no re-hosting to our own storage (yet).
"""

from __future__ import annotations

import asyncio
import io

import httpx
from openai import OpenAI
from openai.types.video import Video
from PIL import Image

from app.core.config import settings

DEFAULT_VIDEO_MODEL = "sora-2"
DEFAULT_VIDEO_SIZE = "720x1280"
DEFAULT_VIDEO_SECONDS = "8"


def _client() -> OpenAI:
    return OpenAI(api_key=settings.OPENAI_API_KEY)


async def _download_image(image_url: str) -> bytes:
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(image_url)
        response.raise_for_status()
    return response.content


def _fit_to_size(image_bytes: bytes, size: str) -> bytes:
    """Sora rejects `input_reference` unless its pixel dimensions exactly
    match the requested `size` ("Inpaint image must match the requested
    width and height") — product photos are never pre-cropped to Sora's 4
    fixed resolutions, so this resizes-to-cover then center-crops (same
    idea as CSS `object-fit: cover`): fills the frame with no distortion,
    trimming whatever doesn't fit instead of squishing the product.
    """
    target_width, target_height = (int(part) for part in size.split("x"))
    with Image.open(io.BytesIO(image_bytes)) as source:
        fitted: Image.Image = source.convert("RGB")
        source_ratio = fitted.width / fitted.height
        target_ratio = target_width / target_height

        if source_ratio > target_ratio:
            scaled_height = target_height
            scaled_width = round(scaled_height * source_ratio)
        else:
            scaled_width = target_width
            scaled_height = round(scaled_width / source_ratio)

        fitted = fitted.resize((scaled_width, scaled_height), Image.Resampling.LANCZOS)

        left = (scaled_width - target_width) // 2
        top = (scaled_height - target_height) // 2
        image = fitted.crop((left, top, left + target_width, top + target_height))

        buffer = io.BytesIO()
        image.save(buffer, format="JPEG", quality=92)
        return buffer.getvalue()


async def submit_video_job(
    *, prompt: str, image_url: str, model: str, size: str, seconds: str
) -> str:
    """Submits a video generation job and returns Sora's video id
    immediately — this call itself is fast; the actual render is polled
    separately (see `get_video_status`).

    `input_reference` needs actual file bytes (multipart upload), not a URL
    — despite `ImageInputReferenceParam` suggesting `{"image_url": ...}`
    works, the installed SDK's `create()` only extracts real file content
    from it (`extract_files`) — so the reference image is downloaded,
    resized/cropped to exactly match `size` (see `_fit_to_size`), and
    uploaded as a `(filename, bytes, content_type)` tuple.
    """
    raw_bytes = await _download_image(image_url)
    fitted_bytes = await asyncio.to_thread(_fit_to_size, raw_bytes, size)
    video = await asyncio.to_thread(
        _client().videos.create,
        prompt=prompt,
        input_reference=("reference.jpg", fitted_bytes, "image/jpeg"),
        model=model,
        size=size,  # type: ignore[arg-type]
        seconds=seconds,  # type: ignore[arg-type]
    )
    return video.id


async def get_video_status(video_id: str) -> Video:
    return await asyncio.to_thread(_client().videos.retrieve, video_id)


async def download_video_bytes(video_id: str) -> bytes:
    response = await asyncio.to_thread(_client().videos.download_content, video_id, variant="video")
    return response.read()
