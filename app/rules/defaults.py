"""Starter rules. Seeded on first run; edit them through the API afterwards.

Tune the weights against your own inbox for a week before adding anything clever.
"""

DEFAULT_RULES: list[dict] = [
    {"name": "From FIU", "field": "sender", "match_type": "domain", "value": "fiu.edu", "weight": 8},
    {"name": "Professor keyword", "field": "body", "match_type": "contains", "value": "professor", "weight": 3},
    {"name": "Exam", "field": "title", "match_type": "contains", "value": "exam", "weight": 8},
    {"name": "Quiz", "field": "title", "match_type": "contains", "value": "quiz", "weight": 6},
    {"name": "Project", "field": "title", "match_type": "contains", "value": "project", "weight": 5},
    {"name": "Final", "field": "title", "match_type": "contains", "value": "final", "weight": 8},
    {"name": "Deadline language", "field": "body", "match_type": "contains", "value": "deadline", "weight": 5},
    {"name": "Urgent language", "field": "title", "match_type": "contains", "value": "urgent", "weight": 6},
    {"name": "Action required", "field": "title", "match_type": "contains", "value": "action required", "weight": 6},
    {"name": "Interview", "field": "title", "match_type": "contains", "value": "interview", "weight": 10},
    {"name": "Offer", "field": "title", "match_type": "contains", "value": "offer", "weight": 8},
    {"name": "Financial aid", "field": "title", "match_type": "contains", "value": "financial aid", "weight": 8},
    {"name": "Assignment kind", "field": "kind", "match_type": "equals", "value": "assignment", "weight": 4},
]
