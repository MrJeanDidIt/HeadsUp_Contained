from app.config import Settings
from app.sources.base import RawItem, Source


class GmailSource(Source):
    """Gmail adapter — implement second, after the Canvas pipeline runs end to end.

    Flow to build:
      1. OAuth consent for scope https://www.googleapis.com/auth/gmail.readonly
      2. Store the refresh token (encrypted) and exchange it for access tokens
      3. GET /gmail/v1/users/me/messages?q=is:unread newer_than:1d
      4. GET each message with format=metadata to avoid pulling full bodies
      5. Map From / Subject / internalDate onto RawItem

    Keep token refresh in its own module — Graph will need exactly the same thing,
    and that is the piece worth writing well.
    """

    name = "gmail"

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    @property
    def configured(self) -> bool:
        return False

    async def fetch(self) -> list[RawItem]:
        return []
