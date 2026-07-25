from typing import Literal

from pydantic import BaseModel


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
