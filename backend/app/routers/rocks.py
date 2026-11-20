from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from backend.app.database import get_db
from backend.app.models import Rock, User
from backend.app.schemas import RockOut, MilestoneOut
from backend.app.auth import require_team_read
from backend.app.clock import get_today_local, get_current_quarter_label
from backend.app.rules import compute_rock_status, compute_rock_progress

router = APIRouter(prefix="/api/teams", tags=["Rocks"])

@router.get("/{team_id}/rocks", response_model=list[RockOut])
def get_team_rocks(
    team_id: str,
    current_user: User = Depends(require_team_read),
    db: Session = Depends(get_db)
):
    """
    Current quarter's Rocks with owner, status and progress.
    Each Rock expands to list its Milestones (due date, done or not).
    Read-only.
    """
    today = get_today_local()
    rocks = (
        db.query(Rock)
        .filter(Rock.team_id == team_id, Rock.quarter == get_current_quarter_label())
        .order_by(Rock.id)
        .all()
    )

    result = []
    for r in rocks:
        milestones = [
            MilestoneOut(
                id=ms.id,
                rock_id=ms.rock_id,
                title=ms.title,
                due_date=ms.due_date,
                done=ms.done
            )
            for ms in r.milestones
        ]
        
        ms_dicts = [{"due_date": ms.due_date, "done": ms.done} for ms in r.milestones]
        status = compute_rock_status(r.status, ms_dicts, today)
        progress = compute_rock_progress(r.status, ms_dicts)

        result.append(RockOut(
            id=r.id,
            team_id=r.team_id,
            title=r.title,
            owner_id=r.owner_id,
            owner_name=r.owner.name if r.owner else None,
            quarter=r.quarter,
            status=status,
            progress_percent=progress,
            milestones=milestones
        ))

    return result

