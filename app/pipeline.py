"""fetch -> normalize -> score -> notify.

The only place that knows the whole flow. Sources and notifiers stay ignorant of
each other, which is what makes adding Gmail a one-file change.
"""

import logging
from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings, get_settings
from app.models import Item, Notification as NotificationRow, Rule
from app.notify.base import Notification, Notifier
from app.notify.format import new_item_notification, reminder_notification
from app.rules.defaults import DEFAULT_RULES
from app.rules.engine import ensure_utc, score_item
from app.sources.base import RawItem, Source

logger = logging.getLogger(__name__)

# Reminder stages, checked in order. A stage fires at most once per item, ever.
DUE_STAGES: list[tuple[str, float]] = [("due_2h", 2), ("due_48h", 48)]


@dataclass(slots=True)
class PipelineReport:
    fetched: int = 0
    new_items: int = 0
    notified: int = 0


async def seed_rules(session: AsyncSession) -> int:
    existing = await session.scalar(select(Rule).limit(1))
    if existing is not None:
        return 0
    session.add_all([Rule(**definition) for definition in DEFAULT_RULES])
    await session.commit()
    return len(DEFAULT_RULES)


async def upsert_item(session: AsyncSession, raw: RawItem) -> tuple[Item, bool]:
    """Returns (item, created). Deduplication is the DB's job, not ours."""
    stmt = select(Item).where(Item.source == raw.source, Item.external_id == raw.external_id)
    item = await session.scalar(stmt)

    if item is not None:
        # Due dates get moved. Titles get edited. Keep the record current.
        item.title = raw.title
        item.due_at = raw.due_at
        item.url = raw.url
        return item, False

    item = Item(
        source=raw.source,
        external_id=raw.external_id,
        kind=raw.kind,
        title=raw.title,
        body=raw.body,
        url=raw.url,
        sender=raw.sender,
        context=raw.context,
        received_at=raw.received_at,
        due_at=raw.due_at,
        raw=raw.raw,
    )
    session.add(item)
    try:
        await session.flush()
    except IntegrityError:
        # Another replica inserted it between our select and flush.
        await session.rollback()
        return await upsert_item(session, raw)
    return item, True


async def _record_and_send(
    session: AsyncSession,
    notifier: Notifier,
    item: Item,
    stage: str,
    notification: Notification,
) -> bool:
    """Write the notification row first, then send.

    Ordering matters: if the send fails we retry next cycle and the unique
    constraint has already been claimed, so at worst you miss one — never a 2am
    duplicate storm.
    """
    session.add(NotificationRow(item_id=item.id, stage=stage))
    try:
        await session.flush()
    except IntegrityError:
        await session.rollback()
        return False

    await notifier.send(notification)
    return True


async def run_pipeline(
    session: AsyncSession,
    sources: list[Source],
    notifier: Notifier,
    settings: Settings,
    now: datetime | None = None,
) -> PipelineReport:
    now = now or datetime.now(UTC)
    report = PipelineReport()

    rules = list(await session.scalars(select(Rule).where(Rule.active.is_(True))))

    for source in sources:
        if not source.configured:
            continue
        try:
            raw_items = await source.fetch()
        except Exception:
            logger.exception("source %s failed; continuing", source.name)
            continue

        report.fetched += len(raw_items)

        for raw in raw_items:
            item, created = await upsert_item(session, raw)
            result = score_item(item, rules, now=now)
            item.score = result.score

            if created and result.score >= settings.score_threshold:
                sent = await _record_and_send(
                    session,
                    notifier,
                    item,
                    "new",
                    new_item_notification(item, result, settings, now),
                )
                report.notified += int(sent)

            report.new_items += int(created)

    await session.commit()
    return report


async def run_due_reminders(
    session: AsyncSession,
    notifier: Notifier,
    now: datetime | None = None,
    settings: Settings | None = None,
) -> int:
    """Fires T-48h and T-2h reminders for anything not yet past due."""
    now = ensure_utc(now) or datetime.now(UTC)
    settings = settings or get_settings()
    sent = 0

    items = list(await session.scalars(select(Item).where(Item.due_at.is_not(None))))

    for item in items:
        due = ensure_utc(item.due_at)
        if due is None or due <= now:
            continue
        hours = (due - now).total_seconds() / 3600

        for stage, window in DUE_STAGES:
            if hours > window:
                continue
            ok = await _record_and_send(
                session,
                notifier,
                item,
                stage,
                reminder_notification(item, stage, settings, now),
            )
            sent += int(ok)
            break  # only the tightest applicable stage

    await session.commit()
    return sent
