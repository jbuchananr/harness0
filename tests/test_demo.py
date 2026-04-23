"""End-to-end demo against a running server.

Start the server in another terminal first:

    uv run uvicorn server.main:app --port 8000

Then run:

    uv run --no-project --with httpx --with pytest python -m pytest -s tests/test_demo.py
"""

import os

import httpx
import pytest

BASE_URL = os.getenv("PII_PROXY_URL", "http://127.0.0.1:8000")


@pytest.fixture(scope="module")
def live_server() -> str:
    try:
        httpx.get(f"{BASE_URL}/health", timeout=2.0).raise_for_status()
    except httpx.HTTPError as e:
        pytest.skip(
            f"server not reachable at {BASE_URL} — start it with "
            f"`uv run uvicorn server.main:app --port 8000`. ({e})"
        )
    return BASE_URL


def test_show_roundtrip_live(live_server: str) -> None:
    session_id = "demo-session"
    raw = (
        "Hi, this is Alice Smith. You can reach me at alice@example.com "
        "or call 415-555-1212. My colleague Bob Jones also emails "
        "bob@example.com sometimes."
    )

    with httpx.Client(base_url=live_server, timeout=60.0) as client:
        enc = client.post(
            "/encode", json={"text": raw, "session_id": session_id}
        ).raise_for_status().json()

        encoded = enc["redacted_text"]
        tokens = enc["tokens"]

        # Simulate an LLM reply that references some of the tokens we got back.
        refs = ", ".join(t["token"] for t in tokens) or "(no PII detected)"
        model_reply = f"Got it — I'll follow up with: {refs}."

        dec = client.post(
            "/decode", json={"text": model_reply, "session_id": session_id}
        ).raise_for_status().json()

        decoded_reply = dec["text"]

        client.delete(f"/session/{session_id}")

    print("\n--- RAW INPUT ---")
    print(raw)
    print("\n--- ENCODED (what we send to the LLM) ---")
    print(encoded)
    print("\n--- TOKENS ---")
    for t in tokens:
        print(f"  {t['token']:20s} {t['label']}")
    print("\n--- MODEL REPLY (references tokens) ---")
    print(model_reply)
    print("\n--- DECODED (what we return to the user) ---")
    print(decoded_reply)
