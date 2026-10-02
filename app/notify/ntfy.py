import httpx

from app.config import Settings
from app.notify.base import Notification, Notifier


class NtfyNotifier(Notifier):
    """Publishes to an ntfy topic.

    Start with a public ntfy.sh topic using a long random name — treat the topic
    name as the secret. Move to a self-hosted instance on the cluster once the
    pipeline is stable; only the base URL changes.
    """

    def __init__(self, settings: Settings, client: httpx.AsyncClient | None = None) -> None:
        self._settings = settings
        self._client = client

    async def send(self, notification: Notification) -> None:
        if not self._settings.ntfy_topic:
            raise RuntimeError("ntfy_topic is not configured")

        headers = {
            "Title": notification.title,
            "Priority": str(notification.priority),
        }
        if notification.tags:
            headers["Tags"] = ",".join(notification.tags)
        if notification.url:
            headers["Click"] = notification.url
        if self._settings.ntfy_token:
            headers["Authorization"] = f"Bearer {self._settings.ntfy_token}"

        url = f"{self._settings.ntfy_base_url}/{self._settings.ntfy_topic}"

        client = self._client or httpx.AsyncClient(timeout=10.0)
        try:
            response = await client.post(
                url, content=notification.message.encode("utf-8"), headers=headers
            )
            response.raise_for_status()
        finally:
            if self._client is None:
                await client.aclose()
