from pydantic import BaseModel, Field


class EncodeRequest(BaseModel):
    text: str
    session_id: str = Field(..., min_length=1)


class TokenInfo(BaseModel):
    token: str
    label: str


class EncodeResponse(BaseModel):
    session_id: str
    redacted_text: str
    tokens: list[TokenInfo]


class DecodeRequest(BaseModel):
    text: str
    session_id: str = Field(..., min_length=1)


class DecodeResponse(BaseModel):
    text: str
