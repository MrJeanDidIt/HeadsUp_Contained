import logging

from app.notify.base import Notification, Notifier

logger = logging.getLogger(__name__)


class ConsoleNotifier(Notifier):
    """Used in tests and local development so you can watch the pipeline work
    without wiring up a phone."""

    def __init__(self) -> None:
        self.sent: list[Notification] = []

    async def send(self, notification: Notification) -> None:
        self.sent.append(notification)
        logger.info("NOTIFY [%s] %s", notification.title, notification.message)
