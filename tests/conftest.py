import re
from dataclasses import dataclass

import pytest
from fastapi.testclient import TestClient

from server.detector import PIISpan
from server.main import app
from server.store import InMemoryStore


@dataclass
class FakeDetector:
    """Regex-driven detector used in tests so we don't need the real model."""

    patterns: dict[str, str]  # label -> regex

    def detect(self, text: str) -> list[PIISpan]:
        spans: list[PIISpan] = []
        for label, pattern in self.patterns.items():
            for m in re.finditer(pattern, text):
                spans.append(
                    PIISpan(
                        start=m.start(),
                        end=m.end(),
                        label=label,
                        text=m.group(0),
                    )
                )
        spans.sort(key=lambda s: s.start)
        return spans


DEFAULT_PATTERNS = {
    "private_email": r"[\w.+-]+@[\w-]+\.[\w.-]+",
    "private_person": r"\b(?:Alice Smith|Bob Jones|Harry Potter)\b",
    "private_phone": r"\b\d{3}-\d{3}-\d{4}\b",
}


@pytest.fixture
def detector() -> FakeDetector:
    return FakeDetector(patterns=DEFAULT_PATTERNS)


@pytest.fixture
def store() -> InMemoryStore:
    return InMemoryStore(ttl_seconds=60.0)


@pytest.fixture
def client(detector: FakeDetector, store: InMemoryStore) -> TestClient:
    app.state.detector = detector
    app.state.store = store
    return TestClient(app)
