from dataclasses import dataclass
from datetime import UTC, datetime

from app.models import Item, Rule


@dataclass(slots=True)
class ScoreResult:
    score: int
    reasons: list[str]


def ensure_utc(value: datetime | None) -> datetime | None:
    """Postgres returns timezone-aware datetimes; SQLite returns naive ones.
    Normalize here so comparison logic never has to care which backend it is on."""
    if value is None:
        return None
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)


def _field_value(item: Item, field: str) -> str:
    return (getattr(item, field, None) or "").lower()


def _matches(rule: Rule, item: Item) -> bool:
    value = _field_value(item, rule.field)
    target = rule.value.lower()

    match rule.match_type:
        case "contains":
            return target in value
        case "equals":
            return value == target
        case "prefix":
            return value.startswith(target)
        case "domain":
            return value.endswith(f"@{target}") or value.endswith(f".{target}")
        case _:
            return False


def urgency_points(due_at: datetime | None, now: datetime | None = None) -> tuple[int, str | None]:
    """Time pressure is scored separately from content rules — a boring assignment
    due in two hours still matters."""
    due_at = ensure_utc(due_at)
    if due_at is None:
        return 0, None

    now = ensure_utc(now) or datetime.now(UTC)
    hours = (due_at - now).total_seconds() / 3600

    if hours < 0:
        return 0, None
    if hours <= 2:
        return 15, "due within 2 hours"
    if hours <= 24:
        return 10, "due within 24 hours"
    if hours <= 48:
        return 6, "due within 48 hours"
    if hours <= 168:
        return 2, "due this week"
    return 0, None


def score_item(item: Item, rules: list[Rule], now: datetime | None = None) -> ScoreResult:
    total = 0
    reasons: list[str] = []

    for rule in rules:
        if rule.active and _matches(rule, item):
            total += rule.weight
            reasons.append(f"{rule.name} (+{rule.weight})")

    points, reason = urgency_points(item.due_at, now)
    if reason:
        total += points
        reasons.append(f"{reason} (+{points})")

    return ScoreResult(score=total, reasons=reasons)
