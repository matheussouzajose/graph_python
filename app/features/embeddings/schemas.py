from pydantic import BaseModel


class EmbeddingsRunResponse(BaseModel):
    status: str
