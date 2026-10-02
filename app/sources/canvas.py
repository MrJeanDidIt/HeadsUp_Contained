from datetime import UTC, datetime, timedelta

import httpx

from app.config import Settings
from app.sources.base import RawItem, Source


class CanvasSource(Source):
    """Pulls upcoming assignments from the Canvas planner API.

    The planner endpoint returns items across every active course in one call,
    which avoids fanning out per course and burning rate limit.
    """

    name = "canvas"

    def __init__(self, settings: Settings, client: httpx.AsyncClient | None = None) -> None:
        self._settings = settings
        self._client = client

    @property
    def configured(self) -> bool:
        return bool(self._settings.canvas_token)

    async def fetch(self) -> list[RawItem]:
        if not self.configured:
            return []

        start = datetime.now(UTC)
        end = start + timedelta(days=self._settings.canvas_lookahead_days)

        params = {
            "start_date": start.date().isoformat(),
            "end_date": end.date().isoformat(),
            "per_page": 100,
        }
        headers = {"Authorization": f"Bearer {self._settings.canvas_token}"}
        url = f"{self._settings.canvas_base_url}/api/v1/planner/items"

        client = self._client or httpx.AsyncClient(timeout=20.0)
        try:
            response = await client.get(url, params=params, headers=headers)
            response.raise_for_status()
            payload = response.json()
        finally:
            if self._client is None:
                await client.aclose()

        return [item for entry in payload if (item := self._to_item(entry)) is not None]

    def _to_item(self, entry: dict) -> RawItem | None:
        plannable = entry.get("plannable") or {}
        due_raw = plannable.get("due_at") or entry.get("plannable_date")
        if not due_raw:
            return None

        path = entry.get("html_url") or ""
        return RawItem(
            source=self.name,
            external_id=str(entry.get("plannable_id") or plannable.get("id")),
            kind="assignment",
            title=plannable.get("title") or "Untitled assignment",
            url=f"{self._settings.canvas_base_url}{path}" if path.startswith("/") else path,
            context=entry.get("context_name"),
            due_at=_parse(due_raw),
            raw=entry,
        )


def _parse(value: str) -> datetime | None:
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (ValueError, AttributeError):
        return None
