from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import RedirectResponse
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import current_principal
from app.config import Settings, get_settings
from app.db import get_session
from app.models import Item, Rule
from app.notify.format import new_item_notification
from app.notify.ntfy import NtfyNotifier
from app.pipeline import upsert_item
from app.rules.engine import score_item
from app.sources.base import RawItem

DEMO_PREFIX = "demo-"


def require_debug(settings: Settings = Depends(get_settings)) -> None:
    if not settings.debug:
        raise HTTPException(status.HTTP_404_NOT_FOUND)


router = APIRouter(
    prefix="/dev",
    tags=["dev"],
    dependencies=[Depends(require_debug), Depends(current_principal)],
)


def demo_items(now: datetime) -> list[RawItem]:
    canvas = "https://canvas.fiu.edu/courses/demo/assignments"
    return [
        RawItem(
            source="canvas",
            external_id=f"{DEMO_PREFIX}a1",
            kind="assignment",
            title="Project 2: Hash Tables",
            context="COP 3530 Data Structures",
            url=f"{canvas}/1",
            due_at=now + timedelta(hours=26),
        ),
        RawItem(
            source="canvas",
            external_id=f"{DEMO_PREFIX}a2",
            kind="assignment",
            title="Quiz 4: Subnetting",
            context="CNT 4403 Network Technology",
            url=f"{canvas}/2",
            due_at=now + timedelta(days=3),
        ),
        RawItem(
            source="canvas",
            external_id=f"{DEMO_PREFIX}a3",
            kind="assignment",
            title="Lab 6 Report",
            context="PHY 2048L Physics Lab",
            url=f"{canvas}/3",
            due_at=now + timedelta(minutes=90),
        ),
        RawItem(
            source="canvas",
            external_id=f"{DEMO_PREFIX}a4",
            kind="assignment",
            title="Final Exam Review Packet",
            context="MAC 2311 Calculus I",
            url=f"{canvas}/4",
            due_at=now + timedelta(days=9),
        ),
        RawItem(
            source="graph",
            external_id=f"{DEMO_PREFIX}m1",
            kind="mail",
            title="Action required: registration hold",
            sender="advisor@fiu.edu",
            url="https://outlook.office.com/mail/",
            received_at=now - timedelta(hours=2),
        ),
        RawItem(
            source="gmail",
            external_id=f"{DEMO_PREFIX}m2",
            kind="mail",
            title="Interview availability for IT Support Intern",
            sender="recruiting@contoso.com",
            url="https://mail.google.com/mail/u/0/#inbox",
            received_at=now - timedelta(minutes=30),
        ),
        RawItem(
            source="gmail",
            external_id=f"{DEMO_PREFIX}m3",
            kind="mail",
            title="This week's deals and coupons",
            sender="newsletter@example.com",
            url="https://mail.google.com/mail/u/0/#inbox",
            received_at=now - timedelta(days=1),
        ),
    ]


@router.post("/demo-items")
async def add_demo_items(session: AsyncSession = Depends(get_session)) -> RedirectResponse:
    now = datetime.now(UTC)
    rules = list(await session.scalars(select(Rule).where(Rule.active.is_(True))))
    for raw in demo_items(now):
        item, _ = await upsert_item(session, raw)
        item.score = score_item(item, rules, now=now).score
    await session.commit()
    return RedirectResponse("/ui?notice=seeded", status_code=status.HTTP_303_SEE_OTHER)


@router.post("/clear-demo")
async def clear_demo_items(session: AsyncSession = Depends(get_session)) -> RedirectResponse:
    await session.execute(delete(Item).where(Item.external_id.startswith(DEMO_PREFIX)))
    await session.commit()
    return RedirectResponse("/ui?notice=cleared", status_code=status.HTTP_303_SEE_OTHER)


@router.post("/test-notification")
async def send_test_notification(
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(get_settings),
) -> RedirectResponse:
    if not settings.ntfy_topic:
        return RedirectResponse("/ui?notice=no-topic", status_code=status.HTTP_303_SEE_OTHER)

    item = await session.scalar(select(Item).order_by(Item.score.desc()).limit(1))
    if item is None:
        return RedirectResponse("/ui?notice=empty", status_code=status.HTTP_303_SEE_OTHER)

    now = datetime.now(UTC)
    rules = list(await session.scalars(select(Rule).where(Rule.active.is_(True))))
    result = score_item(item, rules, now=now)
    await NtfyNotifier(settings).send(new_item_notification(item, result, settings, now))
    return RedirectResponse("/ui?notice=sent", status_code=status.HTTP_303_SEE_OTHER)
