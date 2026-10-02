from app.config import Settings
from app.sources.base import RawItem, Source


class GraphMailSource(Source):
    """Microsoft Graph mail adapter — implement third.

    Flow to build:
      1. App registration with delegated Mail.Read
      2. Auth code flow with offline_access for a refresh token
      3. GET /v1.0/me/messages?$filter=isRead eq false&$select=id,subject,from,receivedDateTime
      4. Map onto RawItem

    Note: a university tenant will likely block consent for this. Test against a
    personal Microsoft account or your own dev tenant first.
    """

    name = "graph"

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    @property
    def configured(self) -> bool:
        return False

    async def fetch(self) -> list[RawItem]:
        return []
