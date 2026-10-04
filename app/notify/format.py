from datetime import datetime

from app.config import Settings
from app.models import Item
from app.notify.base import Notification, NotificationAction
from app.presentation import format_relative, format_when, open_label, safe_url, source_label
from app.rules.engine import ScoreResult

KIND_TAGS = {"mail": "envelope", "assignment": "books"}


def dashboard_link(item: Item, settings: Settings) -> str:
    return f"{settings.public_base_url.rstrip('/')}/ui#item-{item.id}"


def _actions(item: Item, settings: Settings) -> list[NotificationAction]:
    actions = []
    url = safe_url(item.url)
    if url:
        actions.append(NotificationAction(open_label(item.source), url))
    actions.append(NotificationAction("Dashboard", dashboard_link(item, settings)))
    return actions


def _details(
    item: Item, settings: Settings, now: datetime | None, with_relative: bool
) -> list[str]:
    lines = []
    if item.kind == "mail":
        if item.sender:
            lines.append(f"From {item.sender}")
        if item.received_at:
            lines.append(f"Received {format_when(item.received_at, settings.timezone)}")
    elif item.context:
        lines.append(item.context)
    if item.due_at:
        due = f"Due {format_when(item.due_at, settings.timezone)}"
        if with_relative:
            due += f" ({format_relative(item.due_at, now)})"
        lines.append(due)
    return lines


def new_item_notification(
    item: Item, result: ScoreResult, settings: Settings, now: datetime | None = None
) -> Notification:
    lines = _details(item, settings, now, with_relative=True)
    if result.reasons:
        lines.append("Why: " + ", ".join(result.reasons))
    high = result.score >= settings.score_threshold * 2
    tags = [KIND_TAGS.get(item.kind, "bell")]
    if high:
        tags.append("rotating_light")
    return Notification(
        title=item.title,
        message="\n".join(lines) or source_label(item.source),
        url=safe_url(item.url),
        priority=4 if high else 3,
        tags=tags,
        actions=_actions(item, settings),
    )


def reminder_notification(
    item: Item, stage: str, settings: Settings, now: datetime | None = None
) -> Notification:
    lines = _details(item, settings, now, with_relative=False)
    return Notification(
        title=f"Due {format_relative(item.due_at, now)}: {item.title}",
        message="\n".join(lines) or source_label(item.source),
        url=safe_url(item.url),
        priority=5 if stage == "due_2h" else 4,
        tags=["alarm_clock"],
        actions=_actions(item, settings),
    )
