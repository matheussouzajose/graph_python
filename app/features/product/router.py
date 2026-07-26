from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.infrastructure.database.session import get_session
from app.features.product.orm import ProductORM
from app.features.product.repository import ProductRepository
from app.features.product.schemas import ProductListResponse, ProductResponse
from app.features.product.service import ProductService
from app.features.user.schemas import CurrentUser
from app.features.user.security import get_current_user

router = APIRouter(prefix="/products", tags=["products"])


def get_product_service(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> ProductService:
    return ProductService(ProductRepository(session))


ServiceDep = Annotated[ProductService, Depends(get_product_service)]
CurrentUserDep = Annotated[CurrentUser, Depends(get_current_user)]


@router.get("", response_model=ProductListResponse)
async def list_products(
    service: ServiceDep,
    current_user: CurrentUserDep,
    search: str | None = None,
    integration_id: UUID | None = None,
    active: bool | None = None,
    limit: int = 100,
    offset: int = 0,
) -> ProductListResponse:
    products, total = await service.list_for_company(
        company_id=current_user.company_id,
        search=search,
        integration_id=integration_id,
        active=active,
        limit=limit,
        offset=offset,
    )
    return ProductListResponse(
        items=[_product_response(product) for product in products],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/{product_id}", response_model=ProductResponse)
async def get_product(
    product_id: UUID, service: ServiceDep, current_user: CurrentUserDep
) -> ProductResponse:
    product = await service.get_for_company(product_id, current_user.company_id)
    if product is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Product not found")
    return _product_response(product)


def _product_response(product: ProductORM) -> ProductResponse:
    image_url, image_fallback_url = _image_urls(product.media)
    payload = {
        field: getattr(product, field)
        for field in ProductResponse.model_fields
        if field not in {"image_url", "image_fallback_url"}
    }
    return ProductResponse(
        **payload,
        image_url=image_url,
        image_fallback_url=image_fallback_url,
    )


def _image_urls(media: list[dict[str, Any]]) -> tuple[str | None, str | None]:
    for item in media:
        normal = item.get("normal") or {}
        zoom = item.get("zoom") or {}
        url = normal.get("url") or zoom.get("url")
        fallback = normal.get("fallback") or zoom.get("fallback")
        if url or fallback:
            return url, fallback
    return None, None
