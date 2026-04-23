from server.redact import decode, encode
from server.store import InMemoryStore


def test_encode_replaces_pii_with_tokens(detector, store):
    state = store.get_or_create("s1")
    text = "My name is Alice Smith and my email is alice@example.com."

    redacted, used = encode(text, state, detector)

    assert "Alice Smith" not in redacted
    assert "alice@example.com" not in redacted
    assert "[PERSON_1]" in redacted
    assert "[EMAIL_1]" in redacted
    assert {label for _, label in used} == {"private_person", "private_email"}


def test_decode_roundtrips(detector, store):
    state = store.get_or_create("s1")
    original = "Call Bob Jones at 415-555-1212."

    redacted, _ = encode(original, state, detector)
    restored = decode(redacted, state)

    assert restored == original


def test_duplicate_pii_collapses_to_same_token(detector, store):
    state = store.get_or_create("s1")
    text = "Alice Smith met Alice Smith at alice@example.com."

    redacted, used = encode(text, state, detector)

    # "Alice Smith" appears twice but should map to the same token
    assert redacted.count("[PERSON_1]") == 2
    assert "[PERSON_2]" not in redacted
    assert len({tok for tok, _ in used}) == 2  # PERSON_1 + EMAIL_1


def test_tokens_are_session_scoped(detector, store):
    state_a = store.get_or_create("session-a")
    state_b = store.get_or_create("session-b")

    encode("Alice Smith", state_a, detector)
    encode("Bob Jones", state_b, detector)

    # Same token string, different meaning per session — no cross-session leak.
    assert decode("[PERSON_1]", state_a) == "Alice Smith"
    assert decode("[PERSON_1]", state_b) == "Bob Jones"
    assert "Alice Smith" not in state_b.reverse.values()
    assert "Bob Jones" not in state_a.reverse.values()


def test_encode_then_decode_agent_reply(detector, store):
    """Simulate the agent flow: encode user text, model replies using tokens, decode."""
    state = store.get_or_create("s1")
    user_text = "Hi, I'm Harry Potter, email harry@hogwarts.edu."

    redacted, _ = encode(user_text, state, detector)
    model_reply = f"Hello {[t for t in state.reverse if t.startswith('[PERSON')][0]}, I sent a note to {[t for t in state.reverse if t.startswith('[EMAIL')][0]}."

    final = decode(model_reply, state)

    assert "Harry Potter" in final
    assert "harry@hogwarts.edu" in final


def test_decode_with_empty_session_is_passthrough(store):
    state = store.get_or_create("s1")
    assert decode("no tokens here", state) == "no tokens here"


def test_fragmented_spans_are_merged(store):
    """The real privacy-filter model can split 'Alice Smith' into two PERSON
    spans separated by whitespace; encode() must merge them before tokenizing."""
    from server.detector import PIISpan

    class FragmentingDetector:
        def detect(self, text: str) -> list[PIISpan]:
            # "Hi Alice Smith!" → two PERSON spans for "Alice" and " Smith"
            return [
                PIISpan(start=3, end=8, label="private_person", text="Alice"),
                PIISpan(start=8, end=14, label="private_person", text=" Smith"),
            ]

    state = store.get_or_create("s1")
    redacted, used = encode("Hi Alice Smith!", state, FragmentingDetector())

    assert redacted == "Hi [PERSON_1]!"
    assert len(used) == 1
    assert decode(redacted, state) == "Hi Alice Smith!"
