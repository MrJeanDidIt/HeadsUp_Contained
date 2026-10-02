from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # --- core ---------------------------------------------------------------
    app_name: str = "heads-up"
    debug: bool = False
    database_url: str = "postgresql+asyncpg://headsup:headsup@localhost:5432/headsup"
    redis_url: str = "redis://localhost:6379/0"

    # --- auth ---------------------------------------------------------------
    # Set auth_disabled=true only for local development. main.py refuses to start
    # with auth disabled unless debug is also true.
    auth_disabled: bool = False
    entra_tenant_id: str = ""
    entra_audience: str = ""

    # --- sources ------------------------------------------------------------
    canvas_base_url: str = "https://canvas.fiu.edu"
    canvas_token: str = ""
    canvas_lookahead_days: int = 14

    # --- notifications ------------------------------------------------------
    ntfy_base_url: str = "https://ntfy.sh"
    ntfy_topic: str = ""
    ntfy_token: str = ""

    # --- rules --------------------------------------------------------------
    # An item notifies when its score reaches this threshold.
    score_threshold: int = 10
    poll_interval_minutes: int = 10

    @property
    def entra_issuer(self) -> str:
        return f"https://login.microsoftonline.com/{self.entra_tenant_id}/v2.0"

    @property
    def entra_jwks_uri(self) -> str:
        return f"https://login.microsoftonline.com/{self.entra_tenant_id}/discovery/v2.0/keys"


@lru_cache
def get_settings() -> Settings:
    return Settings()
