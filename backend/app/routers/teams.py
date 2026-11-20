from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from backend.app.database import get_db
from backend.app.models import Team, User, Membership
from backend.app.schemas import TeamOut, UserOut
from backend.app.auth import get_current_user, require_team_read

router = APIRouter(prefix="/api/teams", tags=["Teams"])

@router.get("", response_model=list[TeamOut])
def list_teams(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    List teams the user can access:
    - Admins see every team in the company.
    - Team Members and Observers see only teams they are members of.
    """
    if current_user.role == "admin":
        teams = db.query(Team).order_by(Team.name).all()
    else:
        teams = (
            db.query(Team)
            .join(Membership, Membership.team_id == Team.id)
            .filter(Membership.user_id == current_user.id)
            .order_by(Team.name)
            .all()
        )
    return teams

@router.get("/{team_id}", response_model=TeamOut)
def get_team(
    team_id: str,
    current_user: User = Depends(require_team_read),
    db: Session = Depends(get_db)
):
    """
    Get team details. Returns 403 if user cannot access this team.
    """
    team = db.query(Team).filter(Team.id == team_id).first()
    if not team:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Team not found")
    return team

@router.get("/{team_id}/members", response_model=list[UserOut])
def get_team_members(
    team_id: str,
    current_user: User = Depends(require_team_read),
    db: Session = Depends(get_db)
):
    """
    List members of this team (plus any admins who can act on the team).
    """
    members = (
        db.query(User)
        .join(Membership, Membership.user_id == User.id)
        .filter(Membership.team_id == team_id)
        .all()
    )
    # Also include admins
    admins = db.query(User).filter(User.role == "admin").all()
    all_eligible = {u.id: u for u in (members + admins)}
    return sorted(list(all_eligible.values()), key=lambda u: u.name)

