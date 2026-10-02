from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(slots=True)
class Notification:
    title: str
    message: str
    url: str | None = None
    priority: int = 3  # 1 min .. 5 max
    tags: list[str] | None = None


class Notifier(ABC):
    @abstractmethod
    async def send(self, notification: Notification) -> None: ...
