import time

from server.store import InMemoryStore


def test_get_missing_session_returns_none():
    store = InMemoryStore()
    assert store.get("nope") is None


def test_get_or_create_is_idempotent():
    store = InMemoryStore()
    a = store.get_or_create("s1")
    b = store.get_or_create("s1")
    assert a is b


def test_delete_returns_true_only_when_present():
    store = InMemoryStore()
    store.get_or_create("s1")
    assert store.delete("s1") is True
    assert store.delete("s1") is False


def test_session_expires_after_ttl():
    store = InMemoryStore(ttl_seconds=0.05)
    state = store.get_or_create("s1")
    state.forward["x"] = "[X_1]"
    time.sleep(0.1)
    assert store.get("s1") is None
