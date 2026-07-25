"""ERPClient implementation for Vesti.

Vesti's `GET /v1/orders/company/{company_id}` endpoint has two quirks that
shape this client:

- `start_date`/`end_date` must span at most one calendar month.
- Pagination within that range is by `page` number; `links.next` tells us
  whether there's another page in the current window.

We walk forward in fixed-size windows (`window_days`, configurable per
integration — default 28, safely under the 1-month API limit) rather than
strict calendar months, exhausting every page of a window before advancing.
Both `window_start` **and** `window_end` are stored in the opaque cursor —
`window_end` is only ever recomputed when opening a window fresh (at
page 1), then frozen for every subsequent page of that same window. This
matters for pagination correctness: if `window_end` drifted forward (e.g.
recomputed as "now" on every page call) while paging through a still-open
window, later pages would be querying a subtly different range than
earlier ones. Freezing it means all pages of one window traversal see the
exact same range; only starting a *new* window (or resuming a previously
parked still-open one) gets a fresh "now".
"""

import json
from dataclasses import dataclass
from datetime import UTC, date, datetime, time, timedelta
from uuid import UUID

import httpx

from app.features.integration.erp.base import ERPClientError, OrderPage

_DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S"


@dataclass
class _Cursor:
    window_start: date
    window_end: datetime
    page: int

    def encode(self) -> str:
        return json.dumps(
            {
                "window_start": self.window_start.isoformat(),
                "window_end": self.window_end.isoformat(),
                "page": self.page,
            }
        )

    @classmethod
    def decode(cls, raw: str) -> "_Cursor | None":
        """Returns None for a pre-`window_days` cursor (no `window_end` key)
        — the caller re-opens that `window_start` fresh under the current
        `window_days`. Safe because ingestion is idempotent: any page
        re-fetched during that just re-upserts, never duplicates."""
        data = json.loads(raw)
        if "window_end" not in data:
            return None
        return cls(
            window_start=date.fromisoformat(data["window_start"]),
            window_end=datetime.fromisoformat(data["window_end"]),
            page=data["page"],
        )


def describe_cursor(cursor: str) -> datetime | None:
    """Best-effort decode of an opaque sync cursor into a "synced up to"
    timestamp, for status displays only (e.g. the integrations dashboard).
    Returns None for a malformed or pre-`window_days` cursor rather than
    raising — a bad cursor must not break the status view, only the decoded
    "synced until" hint disappears."""
    try:
        decoded = _Cursor.decode(cursor)
    except (json.JSONDecodeError, KeyError, ValueError):
        return None
    return decoded.window_end if decoded else None


class VestiClient:
    def __init__(
        self,
        base_url: str,
        apikey: str,
        external_company_id: UUID,
        backfill_start_date: date,
        window_days: int = 28,
        http_client: httpx.AsyncClient | None = None,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._api_key = apikey
        self._external_company_id = external_company_id
        self._backfill_start_date = backfill_start_date
        self._window_days = window_days
        self._http_client = http_client or httpx.AsyncClient(timeout=30.0)

    def _open_window(self, window_start: date) -> _Cursor:
        """Start (or restart) a window at `window_start`, computing a fresh
        `window_end`: the full `window_days` span, capped at this exact
        instant if that span would otherwise reach into the future."""
        now = datetime.now(UTC)
        full_span_end = datetime.combine(
            window_start + timedelta(days=self._window_days), time.min, tzinfo=UTC
        )
        window_end = min(full_span_end, now)
        return _Cursor(window_start=window_start, window_end=window_end, page=1)

    async def fetch_orders(self, cursor: str | None, page_size: int = 100) -> OrderPage:
        if cursor is None:
            state = self._open_window(self._backfill_start_date)
        else:
            decoded = _Cursor.decode(cursor)
            if decoded is None:
                old_window_start = date.fromisoformat(json.loads(cursor)["window_start"])
                state = self._open_window(old_window_start)
            elif decoded.page == 1:
                # Fresh window, or resuming a previously parked still-open
                # one — either way, refresh window_end to "now".
                state = self._open_window(decoded.window_start)
            else:
                state = decoded

        orders, has_next_page = await self._request(
            window_start=datetime.combine(state.window_start, time.min, tzinfo=UTC),
            window_end=state.window_end,
            page=state.page,
            page_size=page_size,
        )

        if has_next_page:
            next_cursor = _Cursor(state.window_start, state.window_end, state.page + 1).encode()
            return OrderPage(orders=orders, next_cursor=next_cursor, has_more=True)

        full_span_end = datetime.combine(
            state.window_start + timedelta(days=self._window_days), time.min, tzinfo=UTC
        )
        is_current_window = state.window_end < full_span_end
        if is_current_window:
            # Capped at "now" rather than the full window_days span — this
            # window isn't closed yet. Stay parked here for the next run.
            next_cursor = _Cursor(state.window_start, state.window_end, 1).encode()
            return OrderPage(orders=orders, next_cursor=next_cursor, has_more=False)

        next_window_start = state.window_start + timedelta(days=self._window_days)
        next_state = self._open_window(next_window_start)
        next_cursor = next_state.encode()
        return OrderPage(orders=orders, next_cursor=next_cursor, has_more=True)

    async def _request(
        self, window_start: datetime, window_end: datetime, page: int, page_size: int
    ) -> tuple[list[dict], bool]:
        url = f"{self._base_url}/v1/orders/company/{self._external_company_id}"
        params = {
            "start_date": window_start.strftime(_DATETIME_FORMAT),
            "end_date": window_end.strftime(_DATETIME_FORMAT),
            "page": page,
            "perpage": page_size,
        }
        headers = {"apikey": self._api_key, "Content-Type": "application/json"}

        try:
            response = await self._http_client.get(url, params=params, headers=headers)
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise ERPClientError(f"Vesti request failed: {exc}") from exc

        body = response.json()
        if not body.get("result", {}).get("success", False):
            raise ERPClientError(f"Vesti returned an error: {body.get('result')}")

        orders = body.get("response", [])
        has_next_page = body.get("links", {}).get("next") is not None
        return orders, has_next_page
