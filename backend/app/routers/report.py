from datetime import datetime, date, timedelta
from zoneinfo import ZoneInfo
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from backend.app.database import get_db
from backend.app.models import (
    Team, Measurable, Score, ToDo, Rock, Milestone, Issue, Meeting
)
from backend.app.clock import (
    get_app_now, get_company_tz, get_today_local,
    get_current_week_start, get_13_weeks_ending_current, get_last_closed_week
)
from backend.app.rules import (
    compute_measurable_status, compute_todo_completion, is_done_by_week_end,
    compute_rock_status, compute_rock_progress, compute_meeting_rating,
    sort_unsolved_issues
)

router = APIRouter(prefix="/api", tags=["Rules Report"])

def generate_rules_report(db: Session, custom_now_str: str | None = None) -> dict:
    tz = get_company_tz()
    if custom_now_str:
        now_dt = datetime.fromisoformat(custom_now_str.replace("Z", "+00:00"))
        if now_dt.tzinfo is None:
            now_dt = now_dt.replace(tzinfo=ZoneInfo("UTC"))
        now_utc = now_dt.astimezone(ZoneInfo("UTC"))
        now_local = now_utc.astimezone(tz)
        today = now_local.date()
        current_monday = today - timedelta(days=today.weekday())
        current_w_start = current_monday.isoformat()
        weeks_13 = [(current_monday - timedelta(weeks=12 - i)).isoformat() for i in range(13)]
        app_now_str = custom_now_str
    else:
        now_utc = get_app_now()
        app_now_str = now_utc.strftime("%Y-%m-%dT%H:%M:%SZ")
        today = get_today_local()
        current_w_start = get_current_week_start()
        weeks_13 = get_13_weeks_ending_current()

    all_teams = db.query(Team).order_by(Team.id).all()
    all_measurables = db.query(Measurable).all()
    all_scores = db.query(Score).all()
    all_todos = db.query(ToDo).all()
    all_rocks = db.query(Rock).all()
    all_milestones = db.query(Milestone).all()
    all_issues = db.query(Issue).all()
    all_meetings = db.query(Meeting).all()

    scores_by_mw = {(s.measurable_id, s.week_start): s.value for s in all_scores}
    ms_by_rock = {}
    for ms in all_milestones:
        ms_by_rock.setdefault(ms.rock_id, []).append(ms)

    teams_data = {}
    for team in all_teams:
        t_id = team.id
        t_measurables = [m for m in all_measurables if m.team_id == t_id]
        t_todos = [t for t in all_todos if t.team_id == t_id]
        t_rocks = [r for r in all_rocks if r.team_id == t_id]
        t_issues = [i for i in all_issues if i.team_id == t_id]
        t_meetings = [mt for mt in all_meetings if mt.team_id == t_id and mt.ended_at is not None]

        # 1. measurable_status
        m_status = {}
        for m in t_measurables:
            m_status[m.id] = {
                w: compute_measurable_status(m.goal, scores_by_mw.get((m.id, w)), w, current_w_start)
                for w in weeks_13
            }

        # 2. todo_completion
        todo_comp = {}
        for w in weeks_13:
            w_date = date.fromisoformat(w)
            w_end_date = w_date + timedelta(days=6)
            w_end_local = datetime(
                w_end_date.year, w_end_date.month, w_end_date.day,
                23, 59, 59, 999999, tzinfo=tz
            )
            w_end_utc = w_end_local.astimezone(ZoneInfo("UTC"))

            due_todos = []
            for t in t_todos:
                t_due = date.fromisoformat(t.due_date)
                t_mon = t_due - timedelta(days=t_due.weekday())
                if t_mon == w_date:
                    due_todos.append(t)

            if not due_todos:
                todo_comp[w] = None
            else:
                done_count = sum(1 for t in due_todos if is_done_by_week_end(t.done_at, w_end_utc))
                todo_comp[w] = compute_todo_completion(len(due_todos), done_count)

        # 3. overdue_todos
        overdue = []
        for t in t_todos:
            if t.done_at is None and date.fromisoformat(t.due_date) < today:
                overdue.append(t.id)
        overdue.sort()

        # 4. rocks
        r_dict = {}
        for r in t_rocks:
            ms_list = ms_by_rock.get(r.id, [])
            ms_dicts = [{"due_date": ms.due_date, "done": ms.done} for ms in ms_list]
            r_dict[r.id] = {
                "status": compute_rock_status(r.status, ms_dicts, today),
                "progress_percent": compute_rock_progress(r.status, ms_dicts)
            }

        # 5. issue_order: unsolved issues
        unsolved_issues = [i for i in t_issues if i.solved_at is None]
        issue_order = [i.id for i in sort_unsolved_issues(unsolved_issues)]

        # 6. meetings
        meetings_rep = {}
        for mt in t_meetings:
            st = mt.started_at
            if st.tzinfo is None:
                st = st.replace(tzinfo=ZoneInfo("UTC"))
            sc_week = get_last_closed_week(st)

            # Measurable statuses for sc_week. The week was closed when the
            # meeting ran, even if APP_NOW is later moved inside that week.
            mt_m_status = {
                m.id: compute_measurable_status(
                    m.goal, scores_by_mw.get((m.id, sc_week)), sc_week, current_w_start, closed_week=True
                )
                for m in t_measurables
            }

            # Issues solved during meeting
            st_cmp = mt.started_at.replace(tzinfo=None)
            end_cmp = mt.ended_at.replace(tzinfo=None) if mt.ended_at else get_app_now().replace(tzinfo=None)
            
            i_solved = [
                i.id for i in t_issues
                if i.solved_at and (st_cmp <= i.solved_at.replace(tzinfo=None) <= end_cmp)
            ]
            i_solved.sort()

            # Todos created during meeting
            t_created = [
                t.id for t in t_todos
                if st_cmp <= t.created_at.replace(tzinfo=None) <= end_cmp
            ]
            t_created.sort()

            # Attendees
            attendees = sorted([a.user_id for a in mt.attendees])

            # Rating
            ratings = [r.rating for r in mt.ratings]
            avg_rating = compute_meeting_rating(ratings)

            meetings_rep[mt.id] = {
                "scorecard_week": sc_week,
                "measurable_status": mt_m_status,
                "issues_solved": i_solved,
                "todos_created": t_created,
                "attendee_ids": attendees,
                "rating": avg_rating
            }

        teams_data[t_id] = {
            "measurable_status": m_status,
            "todo_completion": todo_comp,
            "overdue_todos": overdue,
            "rocks": r_dict,
            "issue_order": issue_order,
            "meetings": meetings_rep
        }

    return {
        "now": app_now_str,
        "teams": teams_data
    }

@router.get("/rules-report")
def get_rules_report(db: Session = Depends(get_db)):
    return generate_rules_report(db)

