from datetime import UTC, datetime, timedelta

from app.models import Item, Rule
from app.notify.console import ConsoleNotifier
from app.pipeline import run_due_reminders, run_pipeline, seed_rules
from app.sources.base import RawItem, Source


class FakeSource(Source):
    name = "canvas"

    def __init__(self, items: list[RawItem]) -> None:
        self._items = items
        self.calls = 0

    async def fetch(self) -> list[RawItem]:
        self.calls += 1
        return self._items


class BrokenSource(Source):
    name = "broken"

    async def fetch(self) -> list[RawItem]:
        raise RuntimeError("upstream is down")


def _raw(external_id: str = "a1", **kwargs) -> RawItem:
    defaults = dict(
        source="canvas", external_id=external_id, kind="assignment", title="Final Exam"
    )
    return RawItem(**{**defaults, **kwargs})


async def test_seed_rules_is_idempotent(session):
    assert await seed_rules(session) > 0
    assert await seed_rules(session) == 0


async def test_new_high_score_item_notifies_once(session, settings):
    session.add(Rule(name="Exam", field="title", match_type="contains", value="exam", weight=12, active=True))
    await session.commit()

    source = FakeSource([_raw()])
    notifier = ConsoleNotifier()

    first = await run_pipeline(session, [source], notifier, settings)
    assert first.new_items == 1
    assert first.notified == 1

    # Second poll returns the same item — must not notify again.
    second = await run_pipeline(session, [source], notifier, settings)
    assert second.new_items == 0
    assert second.notified == 0
    assert len(notifier.sent) == 1


async def test_low_score_item_is_stored_but_silent(session, settings):
    source = FakeSource([_raw(title="Weekly reading")])
    notifier = ConsoleNotifier()

    report = await run_pipeline(session, [source], notifier, settings)
    assert report.new_items == 1
    assert report.notified == 0


async def test_failing_source_does_not_stop_the_others(session, settings):
    session.add(Rule(name="Exam", field="title", match_type="contains", value="exam", weight=12, active=True))
    await session.commit()

    notifier = ConsoleNotifier()
    report = await run_pipeline(session, [BrokenSource(), FakeSource([_raw()])], notifier, settings)
    assert report.notified == 1


async def test_due_reminder_fires_once_per_stage(session):
    now = datetime.now(UTC)
    session.add(Item(source="canvas", external_id="x", kind="assignment", title="Lab 4",
                     due_at=now + timedelta(hours=1)))
    await session.commit()

    notifier = ConsoleNotifier()
    assert await run_due_reminders(session, notifier, now=now) == 1
    assert await run_due_reminders(session, notifier, now=now) == 0


async def test_past_due_item_does_not_remind(session):
    now = datetime.now(UTC)
    session.add(Item(source="canvas", external_id="y", kind="assignment", title="Old lab",
                     due_at=now - timedelta(hours=3)))
    await session.commit()

    assert await run_due_reminders(session, ConsoleNotifier(), now=now) == 0
