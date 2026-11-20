from datetime import date, datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
from typing import Optional, Any

def round_half_up(val: Optional[float | Decimal], decimals: int = 0) -> Optional[int | float]:
    """
    Rounds half up (e.g. 12.5% -> 13%, 8.25 -> 8.3).
    """
    if val is None:
        return None
    d = Decimal(str(val))
    if decimals == 0:
        return int(d.quantize(Decimal("1"), rounding=ROUND_HALF_UP))
    else:
        fmt = "0." + "0" * decimals
        return float(d.quantize(Decimal(fmt), rounding=ROUND_HALF_UP))

def compute_measurable_status(
    goal: dict[str, Any],
    score_value: Optional[float],
    week_start: str,
    current_week_start: str,
    closed_week: Optional[bool] = None,
) -> str:
    """
    Rules:
    - Compare week's score with goal: at_least, at_most, between, exactly
    - Boundaries are on track.
    - A closed week with no score is off_track.
    - The current week with no score is pending.
    - closed_week overrides the calendar test when a past meeting's reviewed
      week happens to equal APP_NOW's week: such a week was already closed.
    """
    if score_value is None:
        if closed_week is True:
            return "off_track"
        if closed_week is False:
            return "pending"
        return "pending" if week_start == current_week_start else "off_track"

    gtype = goal.get("type")
    if gtype == "at_least":
        target = float(goal["value"])
        return "on_track" if score_value >= target else "off_track"
    elif gtype == "at_most":
        target = float(goal["value"])
        return "on_track" if score_value <= target else "off_track"
    elif gtype == "between":
        min_val = float(goal["min"])
        max_val = float(goal["max"])
        return "on_track" if (min_val <= score_value <= max_val) else "off_track"
    elif gtype == "exactly":
        target = float(goal["value"])
        return "on_track" if score_value == target else "off_track"
    return "off_track"

def is_todo_overdue(due_date_str: str, done_at: Optional[datetime], today: date) -> bool:
    """
    A To-Do is overdue when it is not done and its due date is before today.
    (Due date equal to today is NOT overdue).
    """
    if done_at is not None:
        return False
    due_d = date.fromisoformat(due_date_str)
    return due_d < today

def compute_rock_status(
    seeded_status: str,
    milestones: list[dict[str, Any]],
    today: date
) -> str:
    """
    Rules:
    - Complete if seeded status is complete.
    - Off-track if seeded status is off_track, or if an unfinished Milestone is past due.
    - Otherwise On-track.
    - A Milestone due today is not past due.
    - No Milestones means the seeded status alone.
    """
    if seeded_status == "complete":
        return "complete"
    if seeded_status == "off_track":
        return "off_track"

    for ms in milestones:
        is_done = ms.get("done", False)
        if not is_done:
            ms_due = date.fromisoformat(ms["due_date"])
            if ms_due < today:
                return "off_track"

    return "on_track"

def compute_rock_progress(
    seeded_status: str,
    milestones: list[dict[str, Any]]
) -> int:
    """
    Completed Milestones / total Milestones, as a whole percent rounded half up.
    No Milestones: 0%, or 100% once Complete.
    """
    if not milestones:
        return 100 if seeded_status == "complete" else 0

    total = len(milestones)
    done_count = sum(1 for ms in milestones if ms.get("done", False))
    ratio = done_count / total
    return round_half_up(ratio * 100, decimals=0)

def compute_meeting_rating(ratings: list[int]) -> Optional[float]:
    """
    Average of submitted ratings, to one decimal, rounded half up.
    Attendees who didn't rate are excluded.
    No ratings means null.
    """
    if not ratings:
        return None
    avg = sum(ratings) / len(ratings)
    return round_half_up(avg, decimals=1)

def compute_todo_completion(due_count: int, done_count: int) -> Optional[dict[str, Any]]:
    """
    To-Dos done by the end of a week / To-Dos due that week.
    Target is 90%; the exact ratio (not the rounded percent) decides.
    Zero due means no rate.
    """
    if due_count == 0:
        return None
    ratio_percent = done_count * 100 / due_count
    return {
        "due": due_count,
        "done": done_count,
        "rate_percent": round_half_up(ratio_percent),
        "meets_target": done_count * 10 >= due_count * 9,
    }

def issue_order_key(issue: Any) -> tuple:
    """
    Priority 5 first, down to 1. Within a priority, oldest first.
    No priority comes last. id is a deterministic tie-breaker.
    """
    priority_rank = -issue.priority if issue.priority is not None else 999
    return (priority_rank, issue.created_at, issue.id)

def sort_unsolved_issues(issues: list[Any]) -> list[Any]:
    return sorted(issues, key=issue_order_key)

def is_done_by_week_end(done_at: Optional[datetime], week_end_utc: datetime) -> bool:
    """Done after its due week counts as not done; exactly at the boundary counts."""
    if done_at is None:
        return False
    if done_at.tzinfo is None:
        done_at = done_at.replace(tzinfo=timezone.utc)
    if week_end_utc.tzinfo is None:
        week_end_utc = week_end_utc.replace(tzinfo=timezone.utc)
    return done_at <= week_end_utc

