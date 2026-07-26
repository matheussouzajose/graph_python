"""Builds the right `VideoProvider` for `Agent.video_provider`.

The only place in the codebase that knows the mapping from provider name ->
concrete client. Adding a new provider means adding one branch here and one
new client module — nothing in `AgentService` changes. Mirrors
`app/features/integration/erp/factory.py::get_erp_client`.
"""

from app.features.agents.video_providers.base import UnsupportedVideoProviderError, VideoProvider
from app.features.agents.video_providers.openai_sora import SoraVideoProvider
from app.features.agents.video_providers.openrouter import OpenRouterVideoProvider


def get_video_provider(name: str) -> VideoProvider:
    if name == "openai":
        return SoraVideoProvider()
    if name == "openrouter":
        return OpenRouterVideoProvider()
    raise UnsupportedVideoProviderError(name)
