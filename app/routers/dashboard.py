from datetime import UTC, datetime, timedelta
from pathlib import Path

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import current_principal
from app.config import Settings, get_settings
from app.db import get_session
from app.models import Item, Rule
from app.presentation import (
    format_relative,
    format_when,
    open_label,
    safe_url,
    score_level,
    source_label,
    urgency,
)
from app.rules.engine import ensure_utc, score_item

templates = Jinja2Templates(directory=Path(__file__).resolve().parent.parent / "templates")

router = APIRouter(include_in_schema=False)

VIEWS = {"all": None, "assignments": "assignment", "mail": "mail"}
NOTICES = {
    "sent": "Test notification sent. Check your phone.",
    "no-topic": "Set NTFY_TOPIC in .env to send notifications.",
    "empty": "Add demo items first, then send a test notification.",
    "seeded": "Demo items added.",
    "cleared": "Demo items removed.",
}


def build_card(item: Item, rules: list[Rule], settings: Settings, now: datetime) -> dict:
    result = score_item(item, rules, now=now)
    due = ensure_utc(item.due_at)
    received = ensure_utc(item.received_at)
    return {
        "id": item.id,
        "title": item.title,
        "kind": item.kind,
        "source_key": item.source,
        "source": source_label(item.source),
        "url": safe_url(item.url),
        "open_label": open_label(item.source),
        "context": item.context,
        "sender": item.sender,
        "due_at": due,
        "due_text": format_when(due, settings.timezone),
        "due_relative": format_relative(due, now),
        "urgency": urgency(due, now),
        "received_relative": format_relative(received, now),
        "score": result.score,
        "level": score_level(result.score, settings.score_threshold),
        "reasons": result.reasons,
    }


@router.get("/")
async def root() -> RedirectResponse:
    return RedirectResponse("/ui")


@router.get("/ui", response_class=HTMLResponse, dependencies=[Depends(current_principal)])
async def dashboard(
    request: Request,
    view: str = "all",
    notice: str | None = None,
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(get_settings),
) -> HTMLResponse:
    now = datetime.now(UTC)
    view = view if view in VIEWS else "all"
    rules = list(await session.scalars(select(Rule).where(Rule.active.is_(True))))
    items = list(await session.scalars(select(Item).order_by(Item.id.desc()).limit(200)))
    cards = [build_card(item, rules, settings, now) for item in items]

    kind = VIEWS[view]
    shown = [card for card in cards if kind is None or card["kind"] == kind]
    week = now + timedelta(days=7)
    due_soon = sorted(
        (card for card in shown if card["due_at"] and now <= card["due_at"] <= week),
        key=lambda card: card["due_at"],
    )
    due_ids = {card["id"] for card in due_soon}
    rest = sorted(
        (card for card in shown if card["id"] not in due_ids),
        key=lambda card: card["score"],
        reverse=True,
    )

    upcoming = sorted(
        (card for card in cards if card["due_at"] and card["due_at"] >= now),
        key=lambda card: card["due_at"],
    )
    next_up = upcoming[0] if upcoming else None

    stats = {
        "total": len(cards),
        "due_48h": sum(
            1 for card in cards if card["due_at"] and now <= card["due_at"] <= now + timedelta(hours=48)
        ),
        "high": sum(1 for card in cards if card["level"] == "high"),
        "mail": sum(1 for card in cards if card["kind"] == "mail"),
    }
    counts = {
        "all": len(cards),
        "assignments": sum(1 for card in cards if card["kind"] == "assignment"),
        "mail": stats["mail"],
    }

    return templates.TemplateResponse(
        request,
        "dashboard.html",
        {
            "view": view,
            "next_up": next_up,
            "counts": counts,
            "stats": stats,
            "due_soon": due_soon,
            "rest": rest,
            "debug": settings.debug,
            "notice": NOTICES.get(notice or ""),
            "generated": format_when(now, settings.timezone),
        },
    )
