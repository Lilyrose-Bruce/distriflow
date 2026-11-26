"""Administrator-only user account management."""
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import require_admin
from app.models import User
from app.schemas.user import UserCreate, UserOut, UserUpdate
from app.services.security import hash_password

# dependencies=[...] applies the admin check to EVERY endpoint in this file.
router = APIRouter(prefix="/users", tags=["Users (Administrator)"],
                   dependencies=[Depends(require_admin)])


def get_user_or_404(db: Session, user_id: int) -> User:
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail=f"User {user_id} was not found.")
    return user


def username_taken(db: Session, username: str, ignore_user_id: int = 0) -> bool:
    """True if another user already has this username."""
    other = db.query(User).filter(User.username == username, User.user_id != ignore_user_id).first()
    return other is not None


@router.get("", response_model=List[UserOut])
def list_users(db: Session = Depends(get_db)):
    return db.query(User).order_by(User.user_id).all()


@router.post("", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def create_user(data: UserCreate, db: Session = Depends(get_db)):
    if username_taken(db, data.username):
        raise HTTPException(status_code=409, detail=f"Username '{data.username}' is already taken.")
    user = User(full_name=data.full_name, username=data.username,
                password_hash=hash_password(data.password), role=data.role)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.get("/{user_id}", response_model=UserOut)
def get_user(user_id: int, db: Session = Depends(get_db)):
    return get_user_or_404(db, user_id)


@router.put("/{user_id}", response_model=UserOut)
def update_user(user_id: int, data: UserUpdate, current_admin: User = Depends(require_admin),
                db: Session = Depends(get_db)):
    user = get_user_or_404(db, user_id)
    changes = data.model_dump(exclude_unset=True)  # only the fields the client sent

    if "username" in changes and username_taken(db, changes["username"], ignore_user_id=user_id):
        raise HTTPException(status_code=409, detail=f"Username '{changes['username']}' is already taken.")

    # Stop an admin from locking themselves out.
    if user_id == current_admin.user_id:
        if changes.get("is_active") is False or changes.get("role") == "Dispatcher":
            raise HTTPException(status_code=400,
                                detail="You cannot deactivate or demote your own account.")

    # The password needs hashing; every other field is copied as it is.
    if "password" in changes:
        user.password_hash = hash_password(changes.pop("password"))
    for field_name, new_value in changes.items():
        setattr(user, field_name, new_value)

    db.commit()
    db.refresh(user)
    return user


@router.delete("/{user_id}", response_model=UserOut)
def deactivate_user(user_id: int, current_admin: User = Depends(require_admin),
                    db: Session = Depends(get_db)):
    """'Delete' = deactivate. The row stays so old plans still show who created them."""
    user = get_user_or_404(db, user_id)
    if user_id == current_admin.user_id:
        raise HTTPException(status_code=400, detail="You cannot deactivate your own account.")
    user.is_active = False
    db.commit()
    db.refresh(user)
    return user
