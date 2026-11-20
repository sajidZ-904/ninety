import uuid
from datetime import datetime, date, timedelta
from zoneinfo import ZoneInfo
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from backend.app.database import get_db
from backend.app.models import ToDo, User, Issue
from backend.app.schemas import ToDoOut, ToDoCreate
from backend.app.auth import require_team_read, require_team_write, get_current_user, validate_owner_assignment
from backend.app.clock import get_today_local, get_app_now, get_last_closed_week, get_company_tz, as_utc
from backend.app.rules import is_todo_overdue, compute_todo_completion, is_done_by_week_end
from backend.app.socket_manager import manager

router = APIRouter(prefix="/api", tags=["To-Dos"])

def serialize_todo(t: ToDo, today: date) -> ToDoOut:
    return ToDoOut(
        id=t.id,
        team_id=t.team_id,
        title=t.title,
        owner_id=t.owner_id,
        owner_name=t.owner.name if t.owner else None,
        due_date=t.due_date,
        done_at=as_utc(t.done_at) if t.done_at else None,
        source_issue_id=t.source_issue_id,
        created_at=as_utc(t.created_at),
        is_overdue=is_todo_overdue(t.due_date, t.done_at, today)
    )

@router.get("/teams/{team_id}/todos", response_model=dict)
def get_team_todos(
    team_id: str,
    current_user: User = Depends(require_team_read),
    db: Session = Depends(get_db)
):
    """
    List To-Dos for the team, overdue ones flagged, and last closed week's completion rate.
    """
    today = get_today_local()
    todos = db.query(ToDo).filter(ToDo.team_id == team_id).order_by(ToDo.due_date.asc(), ToDo.created_at.asc()).all()

    # Calculate last closed week completion rate
    tz = get_company_tz()
    last_closed_monday_str = get_last_closed_week()
    last_closed_monday = date.fromisoformat(last_closed_monday_str)
    last_closed_sunday = last_closed_monday + timedelta(days=6)
    
    # Sunday 23:59:59 in company time converted to UTC
    w_end_local = datetime(
        last_closed_sunday.year, last_closed_sunday.month, last_closed_sunday.day,
        23, 59, 59, 999999, tzinfo=tz
    )
    w_end_utc = w_end_local.astimezone(ZoneInfo("UTC"))

    due_count = 0
    done_count = 0
    for t in todos:
        t_due_date = date.fromisoformat(t.due_date)
        t_due_monday = t_due_date - timedelta(days=t_due_date.weekday())
        if t_due_monday == last_closed_monday:
            due_count += 1
            if is_done_by_week_end(t.done_at, w_end_utc):
                done_count += 1

    completion_stat = None
    if due_count > 0:
        completion_stat = compute_todo_completion(due_count, done_count)
        completion_stat["week_start"] = last_closed_monday_str

    return {
        "todos": [serialize_todo(t, today) for t in todos],
        "last_closed_week_completion": completion_stat
    }

@router.post("/teams/{team_id}/todos", response_model=ToDoOut, status_code=status.HTTP_201_CREATED)
async def create_todo(
    team_id: str,
    payload: ToDoCreate,
    current_user: User = Depends(require_team_write),
    db: Session = Depends(get_db)
):
    """
    Create a new To-Do:
    - Title required.
    - Owner must be an Admin or Team Member of this team (validated on server).
    - Due in 7 days by default (in company calendar date).
    - Can be linked to an Issue.
    """
    validate_owner_assignment(team_id, payload.owner_id, db)

    today = get_today_local()
    due_date = payload.due_date
    if not due_date:
        due_date = (today + timedelta(days=7)).isoformat()

    now = get_app_now()
    new_id = f"t_{uuid.uuid4().hex[:8]}"

    # Verify source issue if provided
    if payload.source_issue_id:
        issue = db.query(Issue).filter(Issue.id == payload.source_issue_id, Issue.team_id == team_id).first()
        if not issue:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Source issue not found")

    todo = ToDo(
        id=new_id,
        team_id=team_id,
        title=payload.title,
        owner_id=payload.owner_id,
        due_date=due_date,
        done_at=None,
        source_issue_id=payload.source_issue_id,
        created_at=now
    )
    db.add(todo)
    db.commit()
    db.refresh(todo)

    todo_out = serialize_todo(todo, today)
    await manager.broadcast(team_id, {
        "type": "todo_created",
        "todo": todo_out.model_dump(mode="json")
    })

    return todo_out

@router.patch("/todos/{todo_id}/toggle", response_model=ToDoOut)
async def toggle_todo_done(
    todo_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Mark done, or undo."""
    todo = db.query(ToDo).filter(ToDo.id == todo_id).first()
    if not todo:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="To-Do not found")

    require_team_write(todo.team_id, current_user, db)

    now = get_app_now()
    if todo.done_at is None:
        todo.done_at = now
    else:
        todo.done_at = None

    db.commit()
    db.refresh(todo)

    today = get_today_local()
    todo_out = serialize_todo(todo, today)
    await manager.broadcast(todo.team_id, {
        "type": "todo_updated",
        "todo": todo_out.model_dump(mode="json")
    })

    return todo_out

