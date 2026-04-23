def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


def test_encode_then_decode_roundtrip(client):
    original = "My name is Alice Smith, email alice@example.com."

    r = client.post("/encode", json={"text": original, "session_id": "demo"})
    assert r.status_code == 200
    body = r.json()

    assert body["session_id"] == "demo"
    assert "Alice Smith" not in body["redacted_text"]
    assert "alice@example.com" not in body["redacted_text"]
    labels = {t["label"] for t in body["tokens"]}
    assert labels == {"private_person", "private_email"}

    # Agent replies using the redacted tokens; we decode back to originals.
    email_token = next(t["token"] for t in body["tokens"] if t["label"] == "private_email")
    agent_reply = f"Noted, I'll contact {email_token}."

    r = client.post("/decode", json={"text": agent_reply, "session_id": "demo"})
    assert r.status_code == 200
    assert "alice@example.com" in r.json()["text"]


def test_decode_unknown_session_returns_404(client):
    r = client.post("/decode", json={"text": "hi", "session_id": "never-seen"})
    assert r.status_code == 404


def test_delete_session(client):
    client.post("/encode", json={"text": "Alice Smith", "session_id": "ephemeral"})
    r = client.delete("/session/ephemeral")
    assert r.status_code == 200

    r = client.post("/decode", json={"text": "[PERSON_1]", "session_id": "ephemeral"})
    assert r.status_code == 404


def test_sessions_are_isolated(client):
    client.post("/encode", json={"text": "Alice Smith", "session_id": "a"})
    client.post("/encode", json={"text": "Bob Jones", "session_id": "b"})

    # Decoding a's token in b's session should NOT resolve to "Alice Smith"
    r = client.post("/decode", json={"text": "[PERSON_1]", "session_id": "b"})
    assert r.status_code == 200
    assert r.json()["text"] == "Bob Jones"
