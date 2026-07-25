"""Data access for orders.

`upsert_many` is a bulk `INSERT ... ON CONFLICT DO UPDATE` — one statement
per page, not a query-then-insert/update loop per order. This is idempotent
*data ingestion* (re-syncing the same order overwrites its columns), not a
business validation rule, so relying on the DB's conflict resolution here
does not contradict the "never validate via the database" rule applied to
`company`/`integration` — see CLAUDE.md.
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import func, select, text
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.integration.orm import IntegrationORM
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

    async def get_for_company(self, order_id: UUID, company_id: UUID) -> OrderORM | None:
        stmt = (
            select(OrderORM)
            .join(IntegrationORM, IntegrationORM.id == OrderORM.integration_id)
            .where(OrderORM.id == order_id, IntegrationORM.company_id == company_id)
        )
        return await self._session.scalar(stmt)

    async def list(
        self, integration_id: UUID | None = None, limit: int = 100, offset: int = 0
    ) -> Sequence[OrderORM]:
        stmt = select(OrderORM).order_by(OrderORM.created_at.desc()).limit(limit).offset(offset)
        if integration_id is not None:
            stmt = stmt.where(OrderORM.integration_id == integration_id)
        return (await self._session.scalars(stmt)).all()

    async def list_for_company(
        self,
        company_id: UUID,
        integration_id: UUID | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> Sequence[OrderORM]:
        stmt = (
            select(OrderORM)
            .join(IntegrationORM, IntegrationORM.id == OrderORM.integration_id)
            .where(IntegrationORM.company_id == company_id)
            .order_by(OrderORM.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        if integration_id is not None:
            stmt = stmt.where(OrderORM.integration_id == integration_id)
        return (await self._session.scalars(stmt)).all()

    def _filter_where(
        self,
        company_id: UUID,
        filters: dict[str, list[str]],
        exclude: str | None = None,
    ) -> tuple[str, dict[str, Any]]:
        clauses = ["i.company_id = :company_id"]
        params: dict[str, Any] = {"company_id": company_id}

        def values_for(key: str) -> list[str]:
            if exclude == key:
                return []
            return [value for value in filters.get(key, []) if value]

        for key, column in {
            "integration_id": "o.integration_id::text",
            "status": "o.status",
            "origin": "o.origin",
        }.items():
            values = values_for(key)
            if values:
                param = f"{key}_values"
                clauses.append(f"{column} = ANY(:{param})")
                params[param] = values

        state_values = values_for("state")
        if state_values:
            clauses.append("o.address -> 'state' ->> 'initials' = ANY(:state_values)")
            params["state_values"] = state_values

        city_values = values_for("city")
        if city_values:
            clauses.append("o.address -> 'city' ->> 'name' = ANY(:city_values)")
            params["city_values"] = city_values

        product_values = values_for("product_id")
        if product_values:
            clauses.append(
                """
                EXISTS (
                    SELECT 1
                    FROM jsonb_array_elements(o.products) AS selected_product
                    WHERE selected_product ->> 'id' = ANY(:product_id_values)
                )
                """
            )
            params["product_id_values"] = product_values

        return " AND ".join(clauses), params

    async def list_filtered_for_company(
        self,
        company_id: UUID,
        filters: dict[str, list[str]],
        limit: int = 100,
        offset: int = 0,
    ) -> tuple[Sequence[OrderORM], int]:
        where_sql, params = self._filter_where(company_id, filters)
        total_stmt = text(
            f"""
            SELECT count(*) AS total
            FROM orders o
            JOIN integrations i ON i.id = o.integration_id
            WHERE {where_sql}
            """
        )
        total = int((await self._session.execute(total_stmt, params)).scalar_one())

        ids_stmt = text(
            f"""
            SELECT o.id
            FROM orders o
            JOIN integrations i ON i.id = o.integration_id
            WHERE {where_sql}
            ORDER BY o.external_created_at DESC NULLS LAST, o.created_at DESC
            LIMIT :limit OFFSET :offset
            """
        )
        id_params = {**params, "limit": limit, "offset": offset}
        ids = [row.id for row in (await self._session.execute(ids_stmt, id_params)).all()]
        if not ids:
            return [], total

        stmt = (
            select(OrderORM)
            .where(OrderORM.id.in_(ids))
            .order_by(OrderORM.external_created_at.desc().nulls_last(), OrderORM.created_at.desc())
        )
        return (await self._session.scalars(stmt)).all(), total

    async def filter_facets_for_company(
        self,
        company_id: UUID,
        filters: dict[str, list[str]],
        option_limit: int = 40,
    ) -> list[dict[str, Any]]:
        facet_defs = [
            ("integration_id", "Integração", "o.integration_id::text", "i.name"),
            ("status", "Status", "o.status", "o.status"),
            ("origin", "Origem", "o.origin", "o.origin"),
            ("state", "Estado", "o.address -> 'state' ->> 'initials'", "o.address -> 'state' ->> 'initials'"),
            ("city", "Cidade", "o.address -> 'city' ->> 'name'", "o.address -> 'city' ->> 'name'"),
        ]

        facets: list[dict[str, Any]] = []
        for key, label, value_expr, label_expr in facet_defs:
            where_sql, params = self._filter_where(company_id, filters, exclude=key)
            stmt = text(
                f"""
                SELECT
                    {value_expr} AS value,
                    COALESCE({label_expr}, {value_expr}) AS label,
                    count(*) AS count
                FROM orders o
                JOIN integrations i ON i.id = o.integration_id
                WHERE {where_sql}
                  AND {value_expr} IS NOT NULL
                  AND {value_expr} <> ''
                GROUP BY value, label
                ORDER BY count DESC, label ASC
                LIMIT :option_limit
                """
            )
            rows = (await self._session.execute(stmt, {**params, "option_limit": option_limit})).mappings()
            facets.append({"key": key, "label": label, "options": list(rows)})

        where_sql, params = self._filter_where(company_id, filters, exclude="product_id")
        product_stmt = text(
            f"""
            SELECT
                product ->> 'id' AS value,
                COALESCE(product ->> 'name', product ->> 'code', product ->> 'id') AS label,
                count(DISTINCT o.id) AS count
            FROM orders o
            JOIN integrations i ON i.id = o.integration_id
            CROSS JOIN LATERAL jsonb_array_elements(o.products) AS product
            WHERE {where_sql}
              AND product ->> 'id' IS NOT NULL
              AND product ->> 'id' <> ''
            GROUP BY value, label
            ORDER BY count DESC, label ASC
            LIMIT :option_limit
            """
        )
        product_rows = (
            await self._session.execute(product_stmt, {**params, "option_limit": option_limit})
        ).mappings()
        facets.append({"key": "product_id", "label": "Produto", "options": list(product_rows)})
        return facets
