import re

from .detector import PIIDetector, PIISpan
from .store import SessionState

_LABEL_ALIASES = {
    "private_email": "EMAIL",
    "private_person": "PERSON",
    "private_phone": "PHONE",
    "private_address": "ADDRESS",
    "private_url": "URL",
    "private_date": "DATE",
    "account_number": "ACCOUNT",
    "secret": "SECRET",
}


def _canonical(label: str) -> str:
    return _LABEL_ALIASES.get(label.lower(), label.upper())


def _mint_token(state: SessionState, label: str) -> str:
    canon = _canonical(label)
    idx = state.counters.get(canon, 0) + 1
    state.counters[canon] = idx
    return f"[{canon}_{idx}]"


def _trim(span: PIISpan, text: str) -> PIISpan:
    start, end = span.start, span.end
    while start < end and text[start].isspace():
        start += 1
    while end > start and text[end - 1].isspace():
        end -= 1
    if start == span.start and end == span.end:
        return span
    return PIISpan(start=start, end=end, label=span.label, text=text[start:end])


def _normalize(spans: list[PIISpan], text: str) -> list[PIISpan]:
    """Trim whitespace, drop empties, merge adjacent same-label spans.

    The underlying token classifier can emit fragmented BIOES spans — e.g.
    "Alice Smith" as two PERSON spans, or an email split across punctuation.
    Adjacent (or whitespace-separated) spans of the same label are joined so
    the replacement tokens line up with human-meaningful entities.
    """
    trimmed = [_trim(s, text) for s in spans]
    trimmed = [s for s in trimmed if s.start < s.end]
    trimmed.sort(key=lambda s: s.start)

    merged: list[PIISpan] = []
    for s in trimmed:
        if merged:
            prev = merged[-1]
            gap = text[prev.end:s.start]
            if s.label == prev.label and (not gap or gap.isspace()):
                merged[-1] = PIISpan(
                    start=prev.start,
                    end=s.end,
                    label=prev.label,
                    text=text[prev.start:s.end],
                )
                continue
        merged.append(s)
    return merged


def encode(
    text: str, state: SessionState, detector: PIIDetector
) -> tuple[str, list[tuple[str, str]]]:
    spans = _normalize(detector.detect(text), text)
    out: list[str] = []
    used: list[tuple[str, str]] = []
    cursor = 0

    for span in spans:
        if span.start < cursor:
            continue
        out.append(text[cursor:span.start])
        original = text[span.start:span.end]
        token = state.forward.get(original)
        if token is None:
            token = _mint_token(state, span.label)
            state.forward[original] = token
            state.reverse[token] = original
            state.labels[token] = span.label
        out.append(token)
        used.append((token, span.label))
        cursor = span.end

    out.append(text[cursor:])
    return "".join(out), used


def decode(text: str, state: SessionState) -> str:
    if not state.reverse:
        return text
    pattern = re.compile("|".join(re.escape(t) for t in state.reverse))
    return pattern.sub(lambda m: state.reverse[m.group(0)], text)
