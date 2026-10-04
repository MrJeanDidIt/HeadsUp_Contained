import httpx

from app.config import Settings
from app.notify.base import Notification, Notifier

MAX_ACTIONS = 3


class NtfyNotifier(Notifier):
    def __init__(self, settings: Settings, client: httpx.AsyncClient | None = None) -> None:
        self._settings = settings
        self._client = client

    def payload(self, notification: Notification) -> dict:
        body: dict = {
            "topic": self._settings.ntfy_topic,
            "title": notification.title,
            "message": notification.message,
            "priority": notification.priority,
        }
        if notification.tags:
            body["tags"] = notification.tags
        if notification.url:
            body["click"] = notification.url
        if notification.actions:
            body["actions"] = [
                {"action": "view", "label": action.label, "url": action.url, "clear": True}
                for action in notification.actions[:MAX_ACTIONS]
            ]
        return body

    async def send(self, notification: Notification) -> None:
        if not self._settings.ntfy_topic:
            raise RuntimeError("ntfy_topic is not configured")

        headers = {}
        if self._settings.ntfy_token:
            headers["Authorization"] = f"Bearer {self._settings.ntfy_token}"

        client = self._client or httpx.AsyncClient(timeout=10.0)
        try:
            response = await client.post(
                self._settings.ntfy_base_url.rstrip("/"),
                json=self.payload(notification),
                headers=headers,
            )
            response.raise_for_status()
        finally:
            if self._client is None:
                await client.aclose()
