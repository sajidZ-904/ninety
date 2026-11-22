import uuid
from datetime import datetime, date, timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from backend.app.database import get_db
from backend.app.models import Issue, Measurable, Score, User
from backend.app.schemas import (
    IssueOut, IssueCreate, MakeIssueRequest, IssuePriorityUpdate,
    IssueSolveRequest, IssueSource
)
from backend.app.auth import require_team_read, require_team_write, get_current_user
from backend.app.clock import (
    get_app_now, as_utc, get_13_weeks_ending_current, get_current_week_start,
)
from backend.app.rules import compute_measurable_status, sort_unsolved_issues
from backend.app.socket_manager import manager

router = APIRouter(prefix="/api", tags=["Issues"])

def format_week_title(measurable_name: str, week_start_str: str) -> str:
    """Matches seed format: e.g. 'New deals closed, week of Nov 2'"""
    d = date.fromisoformat(week_start_str)
    # month short name and day without leading zero
    month_name = d.strftime("%b")
    day_num = d.day
    return f"{measurable_name}, week of {month_name} {day_num}"

def serialize_issue(i: Issue) -> IssueOut:
    src = None
    if i.source_measurable_id and i.source_week_start:
        src = IssueSource(
            measurable_id=i.source_measurable_id,
            week_start=i.source_week_start
        )
    return IssueOut(
        id=i.id,
        team_id=i.team_id,
        title=i.title,
        owner_id=i.owner_id,
        owner_name=i.owner.name if i.owner else None,
        priority=i.priority,
        created_at=as_utc(i.created_at),
        solved_at=as_utc(i.solved_at) if i.solved_at else None,
        resolution_note=i.resolution_note,
        source=src
    )

@router.get("/teams/{team_id}/issues", response_model=dict[str, list[IssueOut]])
def get_team_issues(
    team_id: str,
    current_user: User = Depends(require_team_read),
    db: Session = Depends(get_db)
):
    """
    Returns unsolved issues in exact Issue order, and solved issues separately.
    Issue order:
    - Priority 5 first, down to 1.
    - Within a priority, oldest first (created_at asc).
    - No priority comes last (oldest first).
    """
    all_issues = db.query(Issue).filter(Issue.team_id == team_id).all()
    
    unsolved = [i for i in all_issues if i.solved_at is None]
    solved = [i for i in all_issues if i.solved_at is not None]

    unsolved = sort_unsolved_issues(unsolved)
    solved.sort(key=lambda i: i.solved_at, reverse=True)

    return {
        "unsolved": [serialize_issue(i) for i in unsolved],
        "solved": [serialize_issue(i) for i in solved]
    }

@router.post("/teams/{team_id}/issues", response_model=IssueOut, status_code=status.HTTP_201_CREATED)
async def create_issue(
    team_id: str,
    payload: IssueCreate,
    current_user: User = Depends(require_team_write),
    db: Session = Depends(get_db)
):
    """Create a new manual issue. Owner is the creator."""
    now = get_app_now()
    new_id = f"i_{uuid.uuid4().hex[:8]}"

    issue = Issue(
        id=new_id,
        team_id=team_id,
        title=payload.title,
        owner_id=current_user.id,
        priority=payload.priority,
        created_at=now,
        solved_at=None,
        resolution_note=None,
        source_measurable_id=None,
        source_week_start=None
    )
    db.add(issue)
    db.commit()
    db.refresh(issue)

    await manager.broadcast(team_id, {
        "type": "issue_created",
        "issue": serialize_issue(issue).model_dump(mode="json")
    })

    return serialize_issue(issue)

@router.post("/teams/{team_id}/issues/make-from-measurable", response_model=IssueOut)
async def make_issue_from_measurable(
    team_id: str,
    payload: MakeIssueRequest,
    current_user: User = Depends(require_team_write),
    db: Session = Depends(get_db)
):
    """
    Make it an Issue on an off-track cell:
    Creates an Issue titled with the Measurable and week, owned by the user who clicked,
    or returns the existing unsolved one.
    Guaranteed duplicate-free under concurrent requests!
    """
    measurable = db.query(Measurable).filter(
        Measurable.id == payload.measurable_id,
        Measurable.team_id == team_id
    ).first()
    if not measurable:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Measurable not found on this team")

    if payload.week_start not in get_13_weeks_ending_current():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="week_start must be a Monday within the last 13 weeks"
        )

    score = db.query(Score).filter(
        Score.measurable_id == payload.measurable_id,
        Score.week_start == payload.week_start
    ).first()
    cell_status = compute_measurable_status(
        measurable.goal,
        score.value if score else None,
        payload.week_start,
        get_current_week_start(),
    )
    if cell_status != "off_track":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only an off-track score can be made into an Issue"
        )

    # Fast path check for existing unsolved issue
    existing = db.query(Issue).filter(
        Issue.source_measurable_id == payload.measurable_id,
        Issue.source_week_start == payload.week_start,
        Issue.solved_at.is_(None)
    ).first()
    if existing:
        return serialize_issue(existing)

    title = format_week_title(measurable.name, payload.week_start)
    now = get_app_now()
    new_id = f"i_{uuid.uuid4().hex[:8]}"

    issue = Issue(
        id=new_id,
        team_id=team_id,
        title=title,
        owner_id=current_user.id,
        priority=None, # default no priority
        created_at=now,
        solved_at=None,
        resolution_note=None,
        source_measurable_id=payload.measurable_id,
        source_week_start=payload.week_start
    )
    db.add(issue)

    try:
        db.commit()
        db.refresh(issue)
        await manager.broadcast(team_id, {
            "type": "issue_created",
            "issue": serialize_issue(issue).model_dump(mode="json")
        })
        return serialize_issue(issue)
    except IntegrityError:
        # Concurrent request inserted an issue for this same measurable and week!
        db.rollback()
        existing = db.query(Issue).filter(
            Issue.source_measurable_id == payload.measurable_id,
            Issue.source_week_start == payload.week_start,
            Issue.solved_at.is_(None)
        ).first()
        if existing:
            return serialize_issue(existing)
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Could not create or retrieve issue")

@router.patch("/issues/{issue_id}/priority", response_model=IssueOut)
async def update_issue_priority(
    issue_id: str,
    payload: IssuePriorityUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    issue = db.query(Issue).filter(Issue.id == issue_id).first()
    if not issue:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Issue not found")

    require_team_write(issue.team_id, current_user, db)

    issue.priority = payload.priority
    db.commit()
    db.refresh(issue)

    await manager.broadcast(issue.team_id, {
        "type": "issue_priority_updated",
        "issue_id": issue.id,
        "priority": issue.priority
    })

    return serialize_issue(issue)

@router.post("/issues/{issue_id}/solve", response_model=IssueOut)
async def solve_issue(
    issue_id: str,
    payload: IssueSolveRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Solve an Issue with a required note.
    Observers cannot solve issues.
    """
    if not payload.resolution_note or not payload.resolution_note.strip():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Resolution note is required")

    issue = db.query(Issue).filter(Issue.id == issue_id).first()
    if not issue:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Issue not found")

    require_team_write(issue.team_id, current_user, db)

    issue.solved_at = get_app_now()
    issue.resolution_note = payload.resolution_note.strip()
    db.commit()
    db.refresh(issue)

    await manager.broadcast(issue.team_id, {
        "type": "issue_solved",
        "issue": serialize_issue(issue).model_dump(mode="json")
    })

    return serialize_issue(issue)

