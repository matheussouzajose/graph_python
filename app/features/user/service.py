from collections.abc import Sequence
from uuid import UUID

from app.features.company.repository import CompanyRepository
from app.features.user.orm import UserORM
from app.features.user.repository import UserRepository
from app.features.user.schemas import LoginRequest, UserCreate, UserUpdate
from app.features.user.security import hash_password, verify_password


class UserAlreadyExistsError(Exception):
    """Raised when an email is already registered."""


class InvalidCredentialsError(Exception):
    """Raised when login credentials are invalid."""


class CompanyNotFoundError(Exception):
    """Raised when user creation references a missing company."""


class UserService:
    def __init__(self, repository: UserRepository, company_repository: CompanyRepository) -> None:
        self._repository = repository
        self._company_repository = company_repository

    async def create(self, data: UserCreate) -> UserORM:
        company = await self._company_repository.get(data.company_id)
        if company is None:
            raise CompanyNotFoundError

        existing = await self._repository.get_by_email(str(data.email))
        if existing is not None:
            raise UserAlreadyExistsError

        return await self._repository.create(
            company_id=data.company_id,
            email=str(data.email),
            name=data.name,
            password_hash=hash_password(data.password),
            role=data.role.value,
            is_active=data.is_active,
        )

    async def authenticate(self, data: LoginRequest) -> UserORM:
        user = await self._repository.get_by_email(str(data.email))
        if user is None or not user.is_active:
            raise InvalidCredentialsError
        if not verify_password(data.password, user.password_hash):
            raise InvalidCredentialsError
        return user

    async def get(self, user_id: UUID) -> UserORM | None:
        return await self._repository.get(user_id)

    async def list_by_company(
        self, company_id: UUID, limit: int = 100, offset: int = 0
    ) -> Sequence[UserORM]:
        return await self._repository.list_by_company(company_id, limit, offset)

    async def update(self, user_id: UUID, data: UserUpdate) -> UserORM | None:
        return await self._repository.update(user_id, data)
