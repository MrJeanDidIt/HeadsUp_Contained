import json
from datetime import UTC, datetime, timedelta

import httpx

from app.config import Settings
from app.models import Item
from app.notify.base import Notification, NotificationAction
from app.notify.format import new_item_notification, reminder_notification
from app.notify.ntfy import NtfyNotifier
from app.presentation import format_relative, safe_url, score_level
from app.rules.engine import ScoreResult

NOW = datetime(2026, 10, 2, 16, 0, tzinfo=UTC)


def _settings() -> Settings:
    return Settings(ntfy_topic="test-topic", public_base_url="http://lab.example:8000")


def _assignment() -> Item:
    return Item(
        id=7,
        source="canvas",
        external_id="a1",
        kind="assignment",
        title="Project 2: Hash Tables",
        context="COP 3530 Data Structures",
        url="https://canvas.fiu.edu/courses/1/assignments/1",
        due_at=NOW + timedelta(hours=26),
    )


def test_new_item_notification_links_to_source_and_dashboard():
    result = ScoreResult(score=21, reasons=["Project (+5)", "due within 48 hours (+6)"])
    note = new_item_notification(_assignment(), result, _settings(), NOW)

    assert note.title == "Project 2: Hash Tables"
    assert "COP 3530 Data Structures" in note.message
    assert "(in 26h)" in note.message
    assert "Why: Project (+5), due within 48 hours (+6)" in note.message
    assert [a.label for a in note.actions] == ["Open in Canvas", "Dashboard"]
    assert note.actions[1].url == "http://lab.example:8000/ui#item-7"
    assert note.priority == 4
    assert "rotating_light" in note.tags


def test_mail_notification_shows_sender():
    item = Item(id=3, source="graph", external_id="m1", kind="mail",
                title="Registration hold", sender="advisor@fiu.edu",
                url="https://outlook.office.com/mail/")
    note = new_item_notification(item, ScoreResult(score=12, reasons=[]), _settings(), NOW)

    assert "From advisor@fiu.edu" in note.message
    assert note.actions[0].label == "Open in Outlook"
    assert note.tags == ["envelope"]


def test_reminder_title_counts_down():
    note = reminder_notification(_assignment(), "due_48h", _settings(), NOW)
    assert note.title == "Due in 26h: Project 2: Hash Tables"
    assert note.priority == 4


def test_unsafe_links_are_dropped():
    assert safe_url("javascript:alert(1)") is None
    assert safe_url("https://canvas.fiu.edu") == "https://canvas.fiu.edu"


def test_relative_time_and_levels():
    assert format_relative(NOW + timedelta(minutes=90), NOW) == "in 90 min"
    assert format_relative(NOW + timedelta(hours=5), NOW) == "in 5h"
    assert format_relative(NOW + timedelta(minutes=30), NOW) == "in 30 min"
    assert format_relative(NOW - timedelta(days=3), NOW) == "3 days ago"
    assert score_level(20, 10) == "high"
    assert score_level(10, 10) == "medium"
    assert score_level(4, 10) == "low"


async def test_ntfy_publishes_json_with_actions():
    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        captured["body"] = json.loads(request.content)
        return httpx.Response(200)

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    notifier = NtfyNotifier(_settings(), client=client)
    await notifier.send(
        Notification(
            title="Café hours changed",
            message="Body",
            url="https://example.com",
            tags=["envelope"],
            actions=[NotificationAction("Open in Gmail", "https://mail.google.com")],
        )
    )

    assert captured["url"] == "https://ntfy.sh"
    assert captured["body"]["topic"] == "test-topic"
    assert captured["body"]["title"] == "Café hours changed"
    assert captured["body"]["click"] == "https://example.com"
    assert captured["body"]["actions"][0]["label"] == "Open in Gmail"
