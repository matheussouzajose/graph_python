"""Builds the right `ERPClient` for an integration.

The only place in the codebase that knows the mapping from
`IntegrationProvider` -> concrete client class. Adding a new ERP means
adding one branch here and one new client module — nothing else in the
sync engine changes.
"""

from datetime import date, datetime

from app.features.company.orm import CompanyORM
from app.features.integration.erp.base import (
    ERPClient,
    IntegrationConfigError,
    UnsupportedProviderError,
)
from app.features.integration.erp.vesti import VestiClient
from app.features.integration.erp.vesti import describe_cursor as _describe_vesti_cursor
from app.features.integration.orm import IntegrationORM
from app.features.integration.schemas import IntegrationProvider


def get_erp_client(integration: IntegrationORM, company: CompanyORM) -> ERPClient:
    provider = IntegrationProvider(integration.provider)
    if provider == IntegrationProvider.VESTI:
        return _build_vesti_client(integration, company)
    raise UnsupportedProviderError(integration.provider)


def describe_sync_progress(provider: str, cursor: str | None) -> datetime | None:
    """Provider-specific, best-effort decode of an opaque sync cursor into a
    "synced up to" timestamp for status displays (dashboard sync-status
    view). Mirrors `get_erp_client`'s role as the only place mapping
    provider -> concrete client: onboarding a new ERP that wants this same
    UI hint means adding one branch here, same as `get_erp_client`. Returns
    None for no cursor or an unrecognized provider — this must never raise,
    it only feeds an optional UI hint."""
    if cursor is None:
        return None
    if provider == IntegrationProvider.VESTI.value:
        return _describe_vesti_cursor(cursor)
    return None


def _build_vesti_client(integration: IntegrationORM, company: CompanyORM) -> VestiClient:
    apikey = integration.configs.get("apikey")
    if not apikey:
        raise IntegrationConfigError("Vesti integration is missing 'apikey' in configs")

    backfill_start_date_raw = integration.params.get("backfill_start_date")
    if not backfill_start_date_raw:
        raise IntegrationConfigError("Vesti integration is missing 'backfill_start_date' in params")

    window_days = _parse_window_days(integration.params.get("window_days"))

    return VestiClient(
        base_url=integration.base_url,
        apikey=apikey,
        external_company_id=company.external_company_id,
        backfill_start_date=_parse_date(backfill_start_date_raw),
        window_days=window_days,
    )


def _parse_date(value: str) -> date:
    """Accepts a plain date ("2026-05-01") or a full timestamp
    ("2026-05-01 00:00:00" / "2026-05-01T00:00:00") — only the date part is
    used, `backfill_start_date` doesn't carry a time-of-day."""
    try:
        return date.fromisoformat(value)
    except ValueError:
        return datetime.fromisoformat(value).date()


_DEFAULT_WINDOW_DAYS = 28
_MAX_WINDOW_DAYS = 31  # Vesti rejects a start_date/end_date span over ~1 month


def _parse_window_days(value: object) -> int:
    """`params["window_days"]` is optional — defaults to 28 (safely under
    Vesti's 1-month span limit). Smaller windows mean smaller responses per
    page and finer-grained resumability; e.g. `5` for a 5-day step."""
    if value is None:
        return _DEFAULT_WINDOW_DAYS
    window_days = int(value)
    if not (0 < window_days <= _MAX_WINDOW_DAYS):
        raise IntegrationConfigError(
            f"Vesti integration's 'window_days' must be between 1 and {_MAX_WINDOW_DAYS}, "
            f"got {window_days}"
        )
    return window_days
