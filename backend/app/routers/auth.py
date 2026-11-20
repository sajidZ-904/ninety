from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from backend.app.database import get_db
from backend.app.models import User
from backend.app.schemas import UserOut
from backend.app.auth import get_current_user

router = APIRouter(prefix="/api", tags=["Auth & Users"])

@router.get("/users", response_model=list[UserOut])
def list_users(db: Session = Depends(get_db)):
    """List all users for the user switcher."""
    users = db.query(User).order_by(User.id).all()
    return users

@router.get("/me", response_model=UserOut)
def get_me(current_user: User = Depends(get_current_user)):
    """Get the currently authenticated user."""
    return current_user

