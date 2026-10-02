from datetime import UTC, datetime, timedelta

from app.models import Item, Rule
from app.rules.engine import score_item, urgency_points


def _item(**kwargs) -> Item:
    defaults = dict(source="canvas", external_id="1", kind="assignment", title="Homework 3")
    return Item(**{**defaults, **kwargs})


def test_contains_rule_adds_weight():
    rules = [Rule(name="Exam", field="title", match_type="contains", value="exam", weight=8, active=True)]
    result = score_item(_item(title="Midterm Exam Review"), rules)
    assert result.score == 8
    assert "Exam (+8)" in result.reasons


def test_inactive_rule_is_skipped():
    rules = [Rule(name="Exam", field="title", match_type="contains", value="exam", weight=8, active=False)]
    assert score_item(_item(title="Final Exam"), rules).score == 0


def test_domain_rule_matches_sender():
    rules = [Rule(name="FIU", field="sender", match_type="domain", value="fiu.edu", weight=8, active=True)]
    assert score_item(_item(kind="mail", sender="advisor@fiu.edu"), rules).score == 8
    assert score_item(_item(kind="mail", sender="spam@example.com"), rules).score == 0


def test_urgency_escalates_as_deadline_approaches():
    now = datetime.now(UTC)
    assert urgency_points(now + timedelta(hours=1), now)[0] == 15
    assert urgency_points(now + timedelta(hours=12), now)[0] == 10
    assert urgency_points(now + timedelta(hours=36), now)[0] == 6
    assert urgency_points(now + timedelta(days=5), now)[0] == 2


def test_past_due_scores_zero_urgency():
    now = datetime.now(UTC)
    assert urgency_points(now - timedelta(hours=1), now) == (0, None)


def test_score_combines_rules_and_urgency():
    now = datetime.now(UTC)
    rules = [Rule(name="Exam", field="title", match_type="contains", value="exam", weight=8, active=True)]
    result = score_item(_item(title="Exam 2", due_at=now + timedelta(hours=1)), rules, now=now)
    assert result.score == 23
    assert len(result.reasons) == 2
