"""Provider-agnostic contract for talking to an ERP.

The rest of the app (the sync engine) only depends on `ERPClient`, never on
a specific provider's SDK/HTTP shape. `OrderPage.next_cursor` is an opaque
string — its format is entirely up to the client implementation (e.g.
`VestiClient` encodes a month-window + page number in it because Vesti's
API can only be queried one month at a time). The engines just persist
whatever it's given and hands it back unchanged on the next call.
"""

from dataclasses import dataclass
from typing import Any, Protocol


@dataclass
class OrderPage:
    orders: list[dict[str, Any]]
    next_cursor: str | None
    has_more: bool


@dataclass
class ProductPage:
    products: list[dict[str, Any]]
    next_cursor: str | None
    has_more: bool


class ERPClient(Protocol):
    async def fetch_orders(self, cursor: str | None, page_size: int = 100) -> OrderPage: ...

    async def fetch_products(self, cursor: str | None, page_size: int = 100) -> ProductPage: ...


class ERPClientError(Exception):
    """Raised when the ERP responds with an error or an unexpected shape."""


class UnsupportedProviderError(Exception):
    """Raised when an integration's `provider` has no matching `ERPClient`."""


class IntegrationConfigError(Exception):
    """Raised when an integration's `configs`/`params` are missing a required key."""
