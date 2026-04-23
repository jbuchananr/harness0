# PII Proxy

A local FastAPI server that redacts PII in text before you send it to a third-party LLM, and restores the originals in the model's reply. Detector is pluggable (default: [`openai/privacy-filter`](https://huggingface.co/openai/privacy-filter)).

## Example
```
[~/workspace/harness0] $ uv run --no-project --with pytest --with httpx python -m pytest -s -v tests/test_demo.py                 
=========================== test session starts ============================
platform darwin -- Python 3.12.13, pytest-9.0.3, pluggy-1.6.0 -- /Users/jonathanbuchanan/workspace/harness0/.venv/bin/python3
cachedir: .pytest_cache
rootdir: /Users/jonathanbuchanan/workspace/harness0
configfile: pyproject.toml
plugins: anyio-4.13.0
collected 1 item                                                           

tests/test_demo.py::test_show_roundtrip_live 
--- RAW INPUT ---
Hi, this is Alice Smith. You can reach me at alice@example.com or call 415-555-1212. My colleague Bob Jones also emails bob@example.com sometimes.

--- ENCODED (what we send to the LLM) ---
Hi, this is [PERSON_1]. You can reach me at [EMAIL_1] or call [PHONE_1]. My colleague [PERSON_2] also emails [EMAIL_2] sometimes.

--- TOKENS ---
  [PERSON_1]           private_person
  [EMAIL_1]            private_email
  [PHONE_1]            private_phone
  [PERSON_2]           private_person
  [EMAIL_2]            private_email

--- MODEL REPLY (references tokens) ---
Got it — I'll follow up with: [PERSON_1], [EMAIL_1], [PHONE_1], [PERSON_2], [EMAIL_2].

--- DECODED (what we return to the user) ---
Got it — I'll follow up with: Alice Smith, alice@example.com, 415-555-1212, Bob Jones, bob@example.com.
```

## Quickstart

```bash
uv sync
uv run uvicorn server.main:app --port 8000
```

```bash
curl -s http://127.0.0.1:8000/encode \
  -H 'content-type: application/json' \
  -d '{"text":"Email alice@example.com","session_id":"demo"}'
```

## Tests

```bash
uv run --no-project --with fastapi --with pytest --with httpx python -m pytest tests/ -q
```

## For agents

Full install/usage instructions are in [`.claude/skills/pii-proxy/SKILL.md`](.claude/skills/pii-proxy/SKILL.md). It's a Claude Code skill — drop the `pii-proxy/` directory into `~/.claude/skills/` (user scope) or keep it here (project scope) and any Claude Code agent can install and use the service.
