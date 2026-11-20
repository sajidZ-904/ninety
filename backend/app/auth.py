from fastapi import Header, HTTPException, Depends, status
from sqlalchemy.orm import Session
from backend.app.database import get_db
from backend.app.models import User, Membership

def get_current_user(
    x_user_id: str = Header(..., description="ID of the authenticated user (e.g. u1, u2)"),
    db: Session = Depends(get_db)
) -> User:
    user = db.query(User).filter(User.id == x_user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"User '{x_user_id}' not found"
        )
    return user

def require_team_read(
    team_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> User:
    """Verifies user can read data for team_id (Admin or team member/observer of this team)."""
    if current_user.role == "admin":
        return current_user
    
    membership = db.query(Membership).filter(
        Membership.user_id == current_user.id,
        Membership.team_id == team_id
    ).first()
    
    if not membership:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Access denied: user '{current_user.id}' is not a member of team '{team_id}'"
        )
    return current_user

def require_team_write(
    team_id: str,
    current_user: User = Depends(require_team_read),
    db: Session = Depends(get_db)
) -> User:
    """Verifies user can modify data for team_id (Admin or Team Member of this team. Observers rejected)."""
    if current_user.role == "observer":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Observers have read-only access and cannot modify data"
        )
    return current_user

def require_team_facilitator(
    team_id: str,
    current_user: User = Depends(require_team_write)
) -> User:
    """Only Admins or Team Members can facilitate meetings."""
    if current_user.role not in ("admin", "team_member"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only Admins and Team Members can start or facilitate meetings"
        )
    return current_user

def validate_owner_assignment(team_id: str, owner_id: str, db: Session) -> User:
    """Validates that a To-Do or Issue owner is an Admin or Team Member of this team."""
    owner = db.query(User).filter(User.id == owner_id).first()
    if not owner:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Owner '{owner_id}' not found")
    if owner.role == "observer":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Observers cannot own To-Dos or Issues")
    if owner.role != "admin":
        membership = db.query(Membership).filter(
            Membership.user_id == owner.id,
            Membership.team_id == team_id
        ).first()
        if not membership:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"User '{owner_id}' is not a member of team '{team_id}'"
            )
    return owner

