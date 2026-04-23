import os
from dataclasses import dataclass
from typing import Callable, Protocol


@dataclass(frozen=True)
class PIISpan:
    start: int
    end: int
    label: str
    text: str


class PIIDetector(Protocol):
    def detect(self, text: str) -> list[PIISpan]: ...


class PrivacyFilterDetector:
    def __init__(self, model_name: str = "openai/privacy-filter") -> None:
        from transformers import pipeline

        self._pipeline = pipeline(
            task="token-classification",
            model=model_name,
            aggregation_strategy="simple",
        )

    def detect(self, text: str) -> list[PIISpan]:
        if not text:
            return []
        results = self._pipeline(text)
        spans: list[PIISpan] = []
        for r in results:
            start = int(r["start"])
            end = int(r["end"])
            spans.append(
                PIISpan(
                    start=start,
                    end=end,
                    label=str(r["entity_group"]),
                    text=text[start:end],
                )
            )
        return spans


_REGISTRY: dict[str, Callable[[], PIIDetector]] = {
    "privacy-filter": PrivacyFilterDetector,
}


def register_detector(name: str, factory: Callable[[], PIIDetector]) -> None:
    _REGISTRY[name] = factory


def get_detector() -> PIIDetector:
    name = os.getenv("PII_DETECTOR", "privacy-filter")
    if name not in _REGISTRY:
        raise ValueError(
            f"Unknown detector {name!r}. Registered: {sorted(_REGISTRY)}"
        )
    return _REGISTRY[name]()
