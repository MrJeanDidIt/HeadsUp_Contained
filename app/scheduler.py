import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.config import Settings
from app.db import get_sessionmaker
from app.notify.ntfy import NtfyNotifier
from app.pipeline import run_due_reminders, run_pipeline
from app.sources.canvas import CanvasSource
from app.sources.gmail import GmailSource
from app.sources.graph_mail import GraphMailSource

logger = logging.getLogger(__name__)


def build_sources(settings: Settings) -> list:
    return [
        CanvasSource(settings),
        GmailSource(settings),
        GraphMailSource(settings),
    ]


async def poll_job(settings: Settings) -> None:
    async with get_sessionmaker()() as session:
        notifier = NtfyNotifier(settings)
        report = await run_pipeline(session, build_sources(settings), notifier, settings)
        logger.info(
            "poll complete: fetched=%s new=%s notified=%s",
            report.fetched,
            report.new_items,
            report.notified,
        )


async def reminder_job(settings: Settings) -> None:
    async with get_sessionmaker()() as session:
        sent = await run_due_reminders(session, NtfyNotifier(settings), settings=settings)
        logger.info("reminders sent: %s", sent)


def build_scheduler(settings: Settings) -> AsyncIOScheduler:
    scheduler = AsyncIOScheduler(timezone=settings.timezone)
    scheduler.add_job(
        poll_job,
        "interval",
        minutes=settings.poll_interval_minutes,
        args=[settings],
        id="poll",
        max_instances=1,
        coalesce=True,
    )
    scheduler.add_job(
        reminder_job,
        "interval",
        minutes=15,
        args=[settings],
        id="reminders",
        max_instances=1,
        coalesce=True,
    )
    return scheduler
