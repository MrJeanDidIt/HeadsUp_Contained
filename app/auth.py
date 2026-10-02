import logging

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt import PyJWKClient

from app.config import Settings, get_settings

logger = logging.getLogger(__name__)
_bearer = HTTPBearer(auto_error=False)
_jwk_clients: dict[str, PyJWKClient] = {}


def _jwk_client(settings: Settings) -> PyJWKClient:
    """Cached per tenant — PyJWKClient caches signing keys internally, so
    rebuilding it per request would refetch the JWKS every time."""
    if settings.entra_tenant_id not in _jwk_clients:
        _jwk_clients[settings.entra_tenant_id] = PyJWKClient(
            settings.entra_jwks_uri, cache_keys=True
        )
    return _jwk_clients[settings.entra_tenant_id]


async def current_principal(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
    settings: Settings = Depends(get_settings),
) -> dict:
    if settings.auth_disabled:
        return {"sub": "local-dev", "roles": ["admin"]}

    if credentials is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Missing bearer token")

    try:
        signing_key = _jwk_client(settings).get_signing_key_from_jwt(credentials.credentials)
        claims = jwt.decode(
            credentials.credentials,
            signing_key.key,
            algorithms=["RS256"],
            audience=settings.entra_audience,
            issuer=settings.entra_issuer,
        )
    except jwt.PyJWTError as exc:
        logger.warning("token rejected: %s", exc)
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid token") from exc

    return claims


def require_role(role: str):
    async def dependency(principal: dict = Depends(current_principal)) -> dict:
        if role not in principal.get("roles", []):
            raise HTTPException(status.HTTP_403_FORBIDDEN, f"Requires role: {role}")
        return principal

    return dependency
