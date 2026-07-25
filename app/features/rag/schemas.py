from typing import Literal
from uuid import UUID
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class AskRequest(BaseModel):
    question: str
    top_k: int = 5


class AskSource(BaseModel):
    order_code: int | None = None
    product_code: int | str | None = None
    customer_name: str | None = None
    score: float | None = None


class AskResponse(BaseModel):
    route: Literal["LOCAL", "GLOBAL"]
    answer: str | None
    generated_query: str | None = None
    sources: list[AskSource] | None = None


class ChatSessionCreateRequest(BaseModel):
    title: str | None = None


class ChatSessionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    title: str
    created_at: datetime
    updated_at: datetime


class ChatMessageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    session_id: UUID
    role: Literal["user", "assistant"]
    content: str
    route: Literal["LOCAL", "GLOBAL"] | None = None
    generated_query: str | None = None
    sources: list[AskSource] | None = None
    created_at: datetime


class ChatHistoryResponse(BaseModel):
    session: ChatSessionResponse
    messages: list[ChatMessageResponse]


class ChatRequest(BaseModel):
    message: str
    top_k: int = 5


class ChatResponse(BaseModel):
    message: ChatMessageResponse
    standalone_question: str
