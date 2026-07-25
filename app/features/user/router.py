from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.infrastructure.database.session import get_session
from app.features.company.repository import CompanyRepository
from app.features.user.repository import UserRepository
from app.features.user.schemas import (
    CurrentUser,
    LoginRequest,
    TokenResponse,
    UserCreate,
    UserResponse,
    UserUpdate,
)
from app.features.user.security import create_access_token, get_current_user
from app.features.user.service import (
    CompanyNotFoundError,
    InvalidCredentialsError,
    UserAlreadyExistsError,
    UserService,
)

router = APIRouter(tags=["users"])


def get_user_service(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> UserService:
    return UserService(UserRepository(session), CompanyRepository(session))


ServiceDep = Annotated[UserService, Depends(get_user_service)]
CurrentUserDep = Annotated[CurrentUser, Depends(get_current_user)]


@router.post("/auth/login", response_model=TokenResponse)
async def login(data: LoginRequest, service: ServiceDep) -> TokenResponse:
    try:
        user = await service.authenticate(data)
    except InvalidCredentialsError as exc:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid email or password") from exc

    token = create_access_token(user_id=user.id, company_id=user.company_id, role=user.role)
    return TokenResponse(access_token=token, user=UserResponse.model_validate(user))


@router.get("/auth/me", response_model=CurrentUser)
async def me(current_user: CurrentUserDep) -> CurrentUser:
    return current_user


@router.post("/users", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(data: UserCreate, service: ServiceDep) -> UserResponse:
    try:
        user = await service.create(data)
    except UserAlreadyExistsError as exc:
        raise HTTPException(
            status.HTTP_409_CONFLICT, "A user with this email already exists"
        ) from exc
    except CompanyNotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Company not found") from exc
    return UserResponse.model_validate(user)


@router.get("/users", response_model=list[UserResponse])
async def list_users(
    service: ServiceDep,
    current_user: CurrentUserDep,
    limit: int = 100,
    offset: int = 0,
) -> list[UserResponse]:
    users = await service.list_by_company(current_user.company_id, limit, offset)
    return [UserResponse.model_validate(user) for user in users]


@router.patch("/users/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: UUID,
    data: UserUpdate,
    service: ServiceDep,
    current_user: CurrentUserDep,
) -> UserResponse:
    user = await service.get(user_id)
    if user is None or user.company_id != current_user.company_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found")

    updated = await service.update(user_id, data)
    if updated is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found")
    return UserResponse.model_validate(updated)
