from collections.abc import Sequence
from uuid import UUID

from app.features.product.orm import ProductORM
from app.features.product.repository import ProductRepository


class ProductService:
    def __init__(self, repository: ProductRepository) -> None:
        self._repository = repository

    async def get_for_company(self, product_id: UUID, company_id: UUID) -> ProductORM | None:
        return await self._repository.get_for_company(product_id, company_id)

    async def list_for_company(
        self,
        company_id: UUID,
        search: str | None = None,
        integration_id: UUID | None = None,
        active: bool | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> tuple[Sequence[ProductORM], int]:
        return await self._repository.list_for_company(
            company_id=company_id,
            search=search,
            integration_id=integration_id,
            active=active,
            limit=limit,
            offset=offset,
        )
