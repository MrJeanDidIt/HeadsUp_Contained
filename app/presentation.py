from datetime import UTC, datetime
from zoneinfo import ZoneInfo

from app.rules.engine import ensure_utc

SOURCE_LABELS = {"canvas": "Canvas", "gmail": "Gmail", "graph": "Outlook"}


def source_label(source: str) -> str:
    return SOURCE_LABELS.get(source, source.title())


def open_label(source: str) -> str:
    return f"Open in {source_label(source)}"


def safe_url(url: str | None) -> str | None:
    if url and url.lower().startswith(("https://", "http://")):
        return url
    return None


def format_when(value: datetime | None, tz: str) -> str:
    value = ensure_utc(value)
    if value is None:
        return ""
    local = value.astimezone(ZoneInfo(tz))
    clock = local.strftime("%I:%M %p").lstrip("0")
    return f"{local:%a, %b} {local.day} at {clock}"


def format_relative(value: datetime | None, now: datetime | None = None) -> str:
    value = ensure_utc(value)
    if value is None:
        return ""
    now = ensure_utc(now) or datetime.now(UTC)
    seconds = (value - now).total_seconds()
    span = abs(seconds)
    if span < 7200:
        amount = f"{max(1, round(span / 60))} min"
    elif span < 172800:
        amount = f"{round(span / 3600)}h"
    else:
        amount = f"{round(span / 86400)} days"
    return f"{amount} ago" if seconds < 0 else f"in {amount}"


def urgency(value: datetime | None, now: datetime | None = None) -> str:
    value = ensure_utc(value)
    if value is None:
        return "none"
    now = ensure_utc(now) or datetime.now(UTC)
    hours = (value - now).total_seconds() / 3600
    if hours < 0:
        return "overdue"
    if hours <= 24:
        return "urgent"
    if hours <= 72:
        return "soon"
    return "later"


def score_level(score: int, threshold: int) -> str:
    if score >= threshold * 2:
        return "high"
    if score >= threshold:
        return "medium"
    return "low"
