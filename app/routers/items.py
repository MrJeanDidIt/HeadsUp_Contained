from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import current_principal
from app.db import get_session
from app.models import Item
from app.schemas import ItemOut

router = APIRouter(prefix="/items", tags=["items"], dependencies=[Depends(current_principal)])


@router.get("", response_model=list[ItemOut])
async def list_items(
    session: AsyncSession = Depends(get_session),
    source: str | None = None,
    kind: str | None = None,
    min_score: int = 0,
    limit: int = Query(50, le=200),
) -> list[Item]:
    stmt = select(Item).where(Item.score >= min_score)
    if source:
        stmt = stmt.where(Item.source == source)
    if kind:
        stmt = stmt.where(Item.kind == kind)
    stmt = stmt.order_by(Item.due_at.is_(None), Item.due_at, Item.score.desc()).limit(limit)
    return list(await session.scalars(stmt))


@router.get("/due", response_model=list[ItemOut])
async def due_soon(
    session: AsyncSession = Depends(get_session),
    days: int = Query(7, ge=1, le=60),
) -> list[Item]:
    """What's due and when — the 'tell me when things are due' endpoint."""
    now = datetime.now(UTC)
    stmt = (
        select(Item)
        .where(Item.due_at.is_not(None), Item.due_at >= now, Item.due_at <= now + timedelta(days=days))
        .order_by(Item.due_at)
    )
    return list(await session.scalars(stmt))
