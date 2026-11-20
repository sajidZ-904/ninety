import os
from datetime import datetime, date, timedelta, timezone
from zoneinfo import ZoneInfo
from backend.app.config import settings

def get_real_now_naive() -> datetime:
    """Real UTC wall clock (stored naive, like all timestamps). Used only for
    the live meeting section timer, never for business rules."""
    return datetime.now(timezone.utc).replace(tzinfo=None)

def get_company_tz() -> ZoneInfo:
    return ZoneInfo(settings.COMPANY_TIMEZONE)

def as_utc(value: datetime) -> datetime:
    """Attach UTC to naive database datetimes (stored naive in UTC) for API output."""
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)

def get_app_now() -> datetime:
    """Returns current simulated application time in UTC."""
    raw_now = os.getenv("APP_NOW", settings.APP_NOW)
    # Ensure timezone aware UTC
    dt = datetime.fromisoformat(raw_now.replace("Z", "+00:00"))
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=ZoneInfo("UTC"))
    return dt.astimezone(ZoneInfo("UTC"))

def get_now_local() -> datetime:
    """Returns current application time in company timezone."""
    return get_app_now().astimezone(get_company_tz())

def get_today_local() -> date:
    """Returns 'Today' as the calendar date of APP_NOW in company time."""
    return get_now_local().date()

def get_current_week_start() -> str:
    """Returns the Monday date string (YYYY-MM-DD) of the current week in company time."""
    today = get_today_local()
    monday = today - timedelta(days=today.weekday())
    return monday.isoformat()

def get_current_quarter_label() -> str:
    """Returns the calendar quarter of APP_NOW in company time, e.g. '2026-Q4'."""
    today = get_today_local()
    return f"{today.year}-Q{(today.month - 1) // 3 + 1}"

def get_13_weeks_ending_current() -> list[str]:
    """Returns the list of 13 Monday date strings (YYYY-MM-DD) ending with current week."""
    today = get_today_local()
    current_monday = today - timedelta(days=today.weekday())
    return [(current_monday - timedelta(weeks=12 - i)).isoformat() for i in range(13)]

def get_last_closed_week(ref_time: datetime | None = None) -> str:
    """
    Returns the Monday of the last closed week.
    'The last closed week means the full week before the current one.'
    """
    if ref_time is None:
        ref_time = get_app_now()
    ref_local = ref_time.astimezone(get_company_tz())
    ref_date = ref_local.date()
    current_monday = ref_date - timedelta(days=ref_date.weekday())
    last_closed_monday = current_monday - timedelta(weeks=1)
    return last_closed_monday.isoformat()

