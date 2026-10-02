from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session

router = APIRouter(tags=["health"])


@router.get("/healthz")
async def liveness() -> dict:
    """Liveness: is the process up. Never touches dependencies — a slow database
    should not get the pod killed."""
    return {"status": "ok"}


@router.get("/readyz")
async def readiness(session: AsyncSession = Depends(get_session)) -> dict:
    """Readiness: can we actually serve. Checks the database."""
    await session.execute(text("SELECT 1"))
    return {"status": "ready"}
