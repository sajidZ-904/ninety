import pytest
from datetime import date, datetime, timezone
from types import SimpleNamespace
from zoneinfo import ZoneInfo
from backend.app.rules import (
    compute_measurable_status,
    is_todo_overdue,
    compute_rock_status,
    compute_rock_progress,
    compute_meeting_rating,
    compute_todo_completion,
    is_done_by_week_end,
    sort_unsolved_issues,
    round_half_up
)

# 1. Measurable Status Rules & Boundary Tests
def test_measurable_at_least():
    goal = {"type": "at_least", "value": 10.0}
    # Exactly on boundary -> on_track
    assert compute_measurable_status(goal, 10.0, "2026-11-02", "2026-11-09") == "on_track"
    # Above boundary -> on_track
    assert compute_measurable_status(goal, 10.1, "2026-11-02", "2026-11-09") == "on_track"
    # Below boundary -> off_track
    assert compute_measurable_status(goal, 9.9, "2026-11-02", "2026-11-09") == "off_track"

def test_measurable_at_most():
    goal = {"type": "at_most", "value": 3.0}
    # Exactly on boundary -> on_track
    assert compute_measurable_status(goal, 3.0, "2026-11-02", "2026-11-09") == "on_track"
    # Below boundary -> on_track
    assert compute_measurable_status(goal, 2.9, "2026-11-02", "2026-11-09") == "on_track"
    # Above boundary -> off_track
    assert compute_measurable_status(goal, 3.1, "2026-11-02", "2026-11-09") == "off_track"

def test_measurable_between():
    goal = {"type": "between", "min": 2.0, "max": 4.0}
    # Min boundary -> on_track
    assert compute_measurable_status(goal, 2.0, "2026-11-02", "2026-11-09") == "on_track"
    # Max boundary -> on_track
    assert compute_measurable_status(goal, 4.0, "2026-11-02", "2026-11-09") == "on_track"
    # Inside -> on_track
    assert compute_measurable_status(goal, 3.0, "2026-11-02", "2026-11-09") == "on_track"
    # Below min -> off_track
    assert compute_measurable_status(goal, 1.9, "2026-11-02", "2026-11-09") == "off_track"
    # Above max -> off_track
    assert compute_measurable_status(goal, 4.1, "2026-11-02", "2026-11-09") == "off_track"

def test_measurable_exactly():
    goal = {"type": "exactly", "value": 1.0}
    assert compute_measurable_status(goal, 1.0, "2026-11-02", "2026-11-09") == "on_track"
    assert compute_measurable_status(goal, 0.0, "2026-11-02", "2026-11-09") == "off_track"
    assert compute_measurable_status(goal, 2.0, "2026-11-02", "2026-11-09") == "off_track"

def test_measurable_missing_scores():
    goal = {"type": "at_least", "value": 10.0}
    current_week = "2026-11-09"
    past_closed_week = "2026-11-02"
    # Current week with no score -> pending
    assert compute_measurable_status(goal, None, current_week, current_week) == "pending"
    # Closed week with no score -> off_track
    assert compute_measurable_status(goal, None, past_closed_week, current_week) == "off_track"


# 2. To-Do Overdue Rules & Boundaries
def test_todo_overdue():
    today = date(2026, 11, 11)
    # Due yesterday, not done -> overdue
    assert is_todo_overdue("2026-11-10", None, today) is True
    # Due today, not done -> NOT overdue
    assert is_todo_overdue("2026-11-11", None, today) is False
    # Due tomorrow, not done -> NOT overdue
    assert is_todo_overdue("2026-11-12", None, today) is False
    # Due yesterday, but done -> NOT overdue
    assert is_todo_overdue("2026-11-10", datetime(2026, 11, 10, 12, 0, tzinfo=ZoneInfo("UTC")), today) is False


# 3. Rock Status & Progress Rules & Boundaries
def test_rock_status_complete():
    # Complete if seeded status is complete
    assert compute_rock_status("complete", [], date(2026, 11, 11)) == "complete"
    # Even if milestones are unfinished, complete wins
    ms = [{"due_date": "2026-10-01", "done": False}]
    assert compute_rock_status("complete", ms, date(2026, 11, 11)) == "complete"

def test_rock_status_off_track():
    today = date(2026, 11, 11)
    # Seeded status off_track stays off_track
    assert compute_rock_status("off_track", [], today) == "off_track"
    # Seeded on_track becomes off_track if unfinished milestone is past due
    ms_past_due = [{"due_date": "2026-11-10", "done": False}]
    assert compute_rock_status("on_track", ms_past_due, today) == "off_track"
    # Milestone due today is NOT past due -> remains on_track
    ms_due_today = [{"due_date": "2026-11-11", "done": False}]
    assert compute_rock_status("on_track", ms_due_today, today) == "on_track"
    # Milestone due tomorrow -> on_track
    ms_future = [{"due_date": "2026-11-12", "done": False}]
    assert compute_rock_status("on_track", ms_future, today) == "on_track"
    # Past due milestone that is done -> on_track
    ms_done = [{"due_date": "2026-11-10", "done": True}]
    assert compute_rock_status("on_track", ms_done, today) == "on_track"

def test_rock_progress_calculation():
    # No milestones: 0%, or 100% once Complete
    assert compute_rock_progress("on_track", []) == 0
    assert compute_rock_progress("complete", []) == 100

    # 1 of 8 done = 12.5% -> round half up to 13%
    ms_8 = [{"done": True}] + [{"done": False}] * 7
    assert compute_rock_progress("on_track", ms_8) == 13

    # 1 of 3 done = 33.333% -> 33%
    ms_3 = [{"done": True}, {"done": False}, {"done": False}]
    assert compute_rock_progress("on_track", ms_3) == 33

    # 2 of 3 done = 66.666% -> 67%
    ms_3_2 = [{"done": True}, {"done": True}, {"done": False}]
    assert compute_rock_progress("on_track", ms_3_2) == 67


# 4. Meeting Rating Rules & Boundaries
def test_meeting_rating():
    # Average of submitted ratings to 1 decimal, round half up
    # 8, 9, 8, 8 -> 33 / 4 = 8.25 -> 8.3
    assert compute_meeting_rating([8, 9, 8, 8]) == 8.3
    # 8, 9, 7 -> 24 / 3 = 8.0 -> 8.0
    assert compute_meeting_rating([8, 9, 7]) == 8.0
    # Empty -> None (null)
    assert compute_meeting_rating([]) is None

# 5. Round Half Up
def test_round_half_up():
    assert round_half_up(12.5, 0) == 13
    assert round_half_up(12.4, 0) == 12
    assert round_half_up(8.25, 1) == 8.3
    assert round_half_up(8.24, 1) == 8.2

# 6. To-Do Completion Rate boundaries
def test_todo_completion_rate_boundaries():
    # Zero due means no rate
    assert compute_todo_completion(0, 0) is None
    # Exactly 90% meets the target (compares the exact ratio)
    assert compute_todo_completion(10, 9) == {
        "due": 10, "done": 9, "rate_percent": 90, "meets_target": True
    }
    # 9/11 = 81.8% -> 82%, below target
    assert compute_todo_completion(11, 9) == {
        "due": 11, "done": 9, "rate_percent": 82, "meets_target": False
    }
    # 7/8 = 87.5% rounds half up to 88% but still misses 90%
    assert compute_todo_completion(8, 7)["rate_percent"] == 88
    assert compute_todo_completion(8, 7)["meets_target"] is False
    # All done
    assert compute_todo_completion(3, 3)["meets_target"] is True

def test_done_after_due_week_is_not_done():
    # Week of Nov 2 2026 ends Sunday Nov 8 23:59:59.999999 Chicago (CST, UTC-6)
    week_end = datetime(2026, 11, 9, 5, 59, 59, 999999, tzinfo=timezone.utc)
    # One minute before the boundary counts
    assert is_done_by_week_end(datetime(2026, 11, 9, 5, 59, tzinfo=timezone.utc), week_end) is True
    # One minute after the boundary does not
    assert is_done_by_week_end(datetime(2026, 11, 9, 6, 1, tzinfo=timezone.utc), week_end) is False
    assert is_done_by_week_end(None, week_end) is False

# 7. Issue order
def _issue(issue_id, priority, created_at):
    return SimpleNamespace(id=issue_id, priority=priority, created_at=created_at)

def test_issue_order_priority_then_age_then_none_last():
    issues = [
        _issue("i4", None, datetime(2026, 9, 1, 15, 0)),
        _issue("i3", 3, datetime(2026, 10, 5, 15, 0)),
        _issue("i1", 5, datetime(2026, 10, 20, 14, 0)),
        _issue("i2", 5, datetime(2026, 10, 14, 16, 0)),
        _issue("i9", 1, datetime(2026, 10, 1, 16, 0)),
    ]
    assert [i.id for i in sort_unsolved_issues(issues)] == ["i2", "i1", "i3", "i9", "i4"]

def test_closed_week_override_for_meeting_review():
    goal = {"type": "at_least", "value": 10}
    week = "2026-10-19"
    # Even if APP_NOW falls inside that week, a meeting's review treats it as closed
    assert compute_measurable_status(goal, None, week, week, closed_week=True) == "off_track"
    assert compute_measurable_status(goal, None, week, week, closed_week=False) == "pending"

