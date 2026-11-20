from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from backend.app.database import get_db
from backend.app.models import Measurable, Score, User
from backend.app.schemas import MeasurableOut, MeasurableWeekStatus, ScoreUpdate, ScoreOut
from backend.app.auth import get_current_user, require_team_read
from backend.app.clock import get_13_weeks_ending_current, get_current_week_start, get_app_now
from backend.app.rules import compute_measurable_status
from backend.app.socket_manager import manager

router = APIRouter(prefix="/api", tags=["Measurables & Scores"])

@router.get("/teams/{team_id}/measurables", response_model=list[MeasurableOut])
def get_team_measurables(
    team_id: str,
    current_user: User = Depends(require_team_read),
    db: Session = Depends(get_db)
):
    """
    Measurables by week for the last 13 weeks, including the current one.
    Each cell has a score and a status: on_track, off_track or pending.
    """
    measurables = db.query(Measurable).filter(Measurable.team_id == team_id).order_by(Measurable.id).all()
    weeks_13 = get_13_weeks_ending_current()
    current_week = get_current_week_start()

    result = []
    for m in measurables:
        scores = {s.week_start: s for s in m.scores}
        week_statuses = []
        for w in weeks_13:
            s = scores.get(w)
            val = s.value if s else None
            stat = compute_measurable_status(m.goal, val, w, current_week)
            week_statuses.append(MeasurableWeekStatus(
                week_start=w,
                value=val,
                status=stat,
                version=s.version if s else None
            ))
        
        result.append(MeasurableOut(
            id=m.id,
            team_id=m.team_id,
            name=m.name,
            owner_id=m.owner_id,
            owner_name=m.owner.name if m.owner else None,
            unit=m.unit,
            goal=m.goal,
            weeks=week_statuses
        ))
    return result

@router.put("/measurables/{measurable_id}/scores/{week_start}", response_model=ScoreOut)
async def update_score(
    measurable_id: str,
    week_start: str,
    payload: ScoreUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Edit a score inline (last save wins).
    Observers are rejected with 403.
    """
    measurable = db.query(Measurable).filter(Measurable.id == measurable_id).first()
    if not measurable:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Measurable not found")

    allowed_weeks = get_13_weeks_ending_current()
    if week_start not in allowed_weeks:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="week_start must be a Monday within the last 13 weeks"
        )

    # Check authorization on team
    if current_user.role == "observer":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Observers cannot edit scores")
    if current_user.role != "admin":
        membership = [m for m in current_user.memberships if m.team_id == measurable.team_id]
        if not membership:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied to team")

    score = db.query(Score).filter(
        Score.measurable_id == measurable_id,
        Score.week_start == week_start
    ).first()

    now = get_app_now()
    if not score:
        score = Score(
            measurable_id=measurable_id,
            week_start=week_start,
            value=payload.value,
            updated_at=now,
            version=1
        )
        db.add(score)
    else:
        score.value = payload.value
        score.updated_at = now
        score.version += 1

    db.commit()
    db.refresh(score)

    # Broadcast real-time update
    await manager.broadcast(measurable.team_id, {
        "type": "score_updated",
        "measurable_id": measurable_id,
        "week_start": week_start,
        "value": score.value,
        "version": score.version
    })

    return ScoreOut(
        measurable_id=score.measurable_id,
        week_start=score.week_start,
        value=score.value,
        version=score.version
    )
