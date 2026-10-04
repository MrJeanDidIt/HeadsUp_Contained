import pytest
from fastapi.testclient import TestClient

from app import db
from app.config import get_settings
from app.routers.dashboard import templates


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("DEBUG", "true")
    monkeypatch.setenv("AUTH_DISABLED", "true")
    monkeypatch.setenv("NTFY_TOPIC", "")
    monkeypatch.setenv("DATABASE_URL", f"sqlite+aiosqlite:///{tmp_path / 'ui.db'}")
    for cached in (get_settings, db.get_engine, db.get_sessionmaker):
        cached.cache_clear()

    from app.main import app

    with TestClient(app) as test_client:
        yield test_client

    for cached in (get_settings, db.get_engine, db.get_sessionmaker):
        cached.cache_clear()


def test_root_redirects_to_dashboard(client):
    response = client.get("/", follow_redirects=False)
    assert response.headers["location"] == "/ui"


def test_empty_dashboard_invites_demo_items(client):
    response = client.get("/ui")
    assert response.status_code == 200
    assert "Add demo items" in response.text


def test_demo_items_render_with_links(client):
    response = client.post("/dev/demo-items")
    assert response.status_code == 200
    assert "Demo items added." in response.text
    assert "Lab 6 Report" in response.text
    assert "Open in Canvas" in response.text
    assert "Open in Outlook" in response.text
    assert 'id="item-' in response.text

    mail_only = client.get("/ui?view=mail")
    assert "Interview availability" in mail_only.text
    assert "Quiz 4: Subnetting" not in mail_only.text


def test_test_notification_without_topic_explains_fix(client):
    client.post("/dev/demo-items")
    response = client.post("/dev/test-notification")
    assert "Set NTFY_TOPIC" in response.text


def test_clear_demo_items(client):
    client.post("/dev/demo-items")
    response = client.post("/dev/clear-demo")
    assert "Demo items removed." in response.text
    assert "Lab 6 Report" not in response.text


def test_titles_are_escaped():
    card = {
        "id": 1, "title": "<script>alert(1)</script>", "kind": "mail", "source_key": "gmail",
        "source": "Gmail", "url": None, "open_label": "Open in Gmail", "context": None,
        "sender": "x@example.com", "due_at": None, "due_text": "", "due_relative": "",
        "urgency": "none", "received_relative": "in 1 min", "score": 0, "level": "low",
        "reasons": [],
    }
    html = templates.get_template("dashboard.html").render(
        view="all", next_up=None, counts={"all": 1, "assignments": 0, "mail": 1},
        stats={"total": 1, "due_48h": 0, "high": 0, "mail": 1}, due_soon=[], rest=[card],
        debug=False, notice=None, generated="now",
    )
    assert "<script>alert(1)</script>" not in html
    assert "&lt;script&gt;" in html
