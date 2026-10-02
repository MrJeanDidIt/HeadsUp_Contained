from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass(slots=True)
class RawItem:
    """The contract every source must satisfy.

    Add a source by implementing Source.fetch() and returning these. Nothing
    downstream changes.
    """

    source: str
    external_id: str
    kind: str  # assignment | mail
    title: str
    body: str | None = None
    url: str | None = None
    sender: str | None = None
    context: str | None = None
    received_at: datetime | None = None
    due_at: datetime | None = None
    raw: dict[str, Any] = field(default_factory=dict)


class Source(ABC):
    name: str

    @abstractmethod
    async def fetch(self) -> list[RawItem]:
        """Return current items. Must be safe to call repeatedly — deduplication
        happens downstream on (source, external_id)."""

    @property
    def configured(self) -> bool:
        return True
