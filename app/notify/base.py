from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass(slots=True)
class NotificationAction:
    label: str
    url: str


@dataclass(slots=True)
class Notification:
    title: str
    message: str
    url: str | None = None
    priority: int = 3
    tags: list[str] | None = None
    actions: list[NotificationAction] = field(default_factory=list)


class Notifier(ABC):
    @abstractmethod
    async def send(self, notification: Notification) -> None: ...
