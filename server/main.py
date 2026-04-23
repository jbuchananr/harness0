import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException

from .detector import get_detector
from .redact import decode, encode
from .schemas import (
    DecodeRequest,
    DecodeResponse,
    EncodeRequest,
    EncodeResponse,
    TokenInfo,
)
from .store import InMemoryStore


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.detector = get_detector()
    app.state.store = InMemoryStore(
        ttl_seconds=float(os.getenv("SESSION_TTL_SECONDS", "3600"))
    )
    yield


app = FastAPI(title="PII Proxy", lifespan=lifespan)


@app.post("/encode", response_model=EncodeResponse)
def encode_endpoint(req: EncodeRequest) -> EncodeResponse:
    state = app.state.store.get_or_create(req.session_id)
    redacted, used = encode(req.text, state, app.state.detector)
    return EncodeResponse(
        session_id=req.session_id,
        redacted_text=redacted,
        tokens=[TokenInfo(token=t, label=l) for t, l in used],
    )


@app.post("/decode", response_model=DecodeResponse)
def decode_endpoint(req: DecodeRequest) -> DecodeResponse:
    state = app.state.store.get(req.session_id)
    if state is None:
        raise HTTPException(
            status_code=404, detail=f"Unknown session_id: {req.session_id}"
        )
    return DecodeResponse(text=decode(req.text, state))


@app.delete("/session/{session_id}")
def delete_session(session_id: str) -> dict:
    if not app.state.store.delete(session_id):
        raise HTTPException(
            status_code=404, detail=f"Unknown session_id: {session_id}"
        )
    return {"deleted": session_id}


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}
