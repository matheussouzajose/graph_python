"""Data access for orders.

`upsert_many` is a bulk `INSERT ... ON CONFLICT DO UPDATE` — one statement
per page, not a query-then-insert/update loop per order. This is idempotent
*data ingestion* (re-syncing the same order overwrites its columns), not a
business validation rule, so relying on the DB's conflict resolution here
does not contradict the "never validate via the database" rule applied to
`company`/`integration` — see CLAUDE.md.
"""

from collections.abc import Sequence
from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.order.orm import OrderORM

_DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S"


def _parse_dt(value: Any) -> datetime | None:
    if not value:
        return None
    return datetime.strptime(value, _DATETIME_FORMAT)


class OrderRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def upsert_many(self, integration_id: UUID, orders: list[dict[str, Any]]) -> int:
        if not orders:
            return 0

        rows = [
            {
                "id": uuid4(),
                "integration_id": integration_id,
                "external_order_id": str(order["id"]),
                "external_company_id": order.get("company_id"),
                "code": order.get("code"),
                "origin": order.get("origin"),
                "status": order.get("status"),
                "observations": order.get("observations"),
                "is_unified": bool((order.get("unification") or {}).get("is_unified", False)),
                "survey_note": (order.get("survey_answer") or {}).get("note"),
                "survey_comment": (order.get("survey_answer") or {}).get("comment"),
                "external_created_at": _parse_dt(order.get("created_at")),
                "external_updated_at": _parse_dt(order.get("updated_at")),
                "expires_at": _parse_dt(order.get("expires_at")),
                "customer": order.get("customer") or {},
                "products": order.get("products") or [],
                "address": order.get("address") or {},
                "freight": order.get("freight") or {},
                "seller": order.get("seller") or {},
                "payment": order.get("payment") or {},
                "summary": order.get("summary") or {},
            }
            for order in orders
        ]
        stmt = pg_insert(OrderORM).values(rows)
        stmt = stmt.on_conflict_do_update(
            constraint="uq_orders_integration_external_id",
            set_={
                "external_company_id": stmt.excluded.external_company_id,
                "code": stmt.excluded.code,
                "origin": stmt.excluded.origin,
                "status": stmt.excluded.status,
                "observations": stmt.excluded.observations,
                "is_unified": stmt.excluded.is_unified,
                "survey_note": stmt.excluded.survey_note,
                "survey_comment": stmt.excluded.survey_comment,
                "external_created_at": stmt.excluded.external_created_at,
                "external_updated_at": stmt.excluded.external_updated_at,
                "expires_at": stmt.excluded.expires_at,
                "customer": stmt.excluded.customer,
                "products": stmt.excluded.products,
                "address": stmt.excluded.address,
                "freight": stmt.excluded.freight,
                "seller": stmt.excluded.seller,
                "payment": stmt.excluded.payment,
                "summary": stmt.excluded.summary,
                "updated_at": func.now(),
            },
        )
        await self._session.execute(stmt)
        await self._session.flush()
        return len(rows)

    async def get(self, order_id: UUID) -> OrderORM | None:
        return await self._session.get(OrderORM, order_id)

    async def list(
        self, integration_id: UUID | None = None, limit: int = 100, offset: int = 0
    ) -> Sequence[OrderORM]:
        stmt = select(OrderORM).order_by(OrderORM.created_at.desc()).limit(limit).offset(offset)
        if integration_id is not None:
            stmt = stmt.where(OrderORM.integration_id == integration_id)
        return (await self._session.scalars(stmt)).all()
