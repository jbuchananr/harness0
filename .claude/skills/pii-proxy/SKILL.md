---
name: pii-proxy
description: Start and call a local PII encode/decode proxy server so you can send redacted text to third-party LLMs and decode their responses back. Use when the user wants to sanitize prompts before sending them to an external model, or restore PII placeholders in a model's reply.
allowed-tools: Bash(uv sync:*), Bash(uv run:*), Bash(curl:*), Bash(lsof:*), Bash(kill:*)
---

# PII Proxy

A local FastAPI server that detects PII in text, replaces it with stable per-session tokens (`[EMAIL_1]`, `[PERSON_1]`, …), and decodes those tokens back. Use it as a sidecar around any third-party LLM call.

The detector is pluggable. The default ships with [`openai/privacy-filter`](https://huggingface.co/openai/privacy-filter); any class implementing `detect(text) -> list[PIISpan]` can be registered via `server.detector.register_detector`.

## When to use this skill

- The user is about to send text containing names, emails, phone numbers, addresses, URLs, dates, or secrets to a remote LLM and wants it redacted first.
- The user has a response from an LLM that contains `[LABEL_N]` placeholders and wants the original values restored.
- The user asks you to set up, run, or test a "PII proxy", "redaction server", or similar.

## Setup (one time)

```bash
uv sync                                # installs fastapi, transformers, torch
```

First run also downloads the `openai/privacy-filter` weights (~1 GB) on the first `/encode` call.

## Start the server

```bash
uv run uvicorn server.main:app --port 8000
```

Wait for readiness before calling:

```bash
until curl -sf http://127.0.0.1:8000/health >/dev/null; do sleep 1; done
```

If port 8000 is taken: `PORT=8010 uv run uvicorn server.main:app --port $PORT`.

## API

All requests require a `session_id` (any opaque string — use the conversation/thread id). Mappings are scoped to that session and expire after `SESSION_TTL_SECONDS` (default 3600).

### Encode

```bash
curl -s http://127.0.0.1:8000/encode \
  -H 'content-type: application/json' \
  -d '{"text":"Email alice@example.com about the Q3 plan.","session_id":"thread-42"}'
```

Returns:
```json
{
  "session_id": "thread-42",
  "redacted_text": "Email [EMAIL_1] about the Q3 plan.",
  "tokens": [{"token": "[EMAIL_1]", "label": "private_email"}]
}
```

### Decode

```bash
curl -s http://127.0.0.1:8000/decode \
  -H 'content-type: application/json' \
  -d '{"text":"Sent a note to [EMAIL_1].","session_id":"thread-42"}'
```

Returns:
```json
{"text": "Sent a note to alice@example.com."}
```

### End session

```bash
curl -s -X DELETE http://127.0.0.1:8000/session/thread-42
```

## Typical agent flow

1. User sends a message. Call `/encode` with the message text and the conversation id as `session_id`. Keep `redacted_text`.
2. Send `redacted_text` to the remote model (OpenAI, Claude, local inference, whatever).
3. Call `/decode` with the model's reply and the same `session_id`. Return the decoded text to the user.
4. When the conversation ends, `DELETE /session/{id}` to free memory.

Important: the same PII string inside the same session always maps to the same token, so a multi-turn conversation stays coherent. Different sessions get independent namespaces.

## Using a different detector

`server/detector.py` defines a `PIIDetector` protocol and a registry. To plug in a custom model:

```python
from server.detector import register_detector, PIISpan

class MyDetector:
    def detect(self, text: str) -> list[PIISpan]: ...

register_detector("my-detector", MyDetector)
```

Then run with `PII_DETECTOR=my-detector uv run uvicorn server.main:app`.

## Tests

```bash
uv run --no-project --with fastapi --with pytest --with httpx python -m pytest tests/ -q
```

Tests use a regex-based fake detector so they run in <1s without loading the real model.

## Teardown

```bash
lsof -ti tcp:8000 | xargs -r kill
```
