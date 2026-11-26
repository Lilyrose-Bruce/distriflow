"""
Authentication module: login, logout, who am I.

POST /auth/login   -> check username + password, set the login cookie
POST /auth/logout  -> remove the login cookie
GET  /auth/me      -> return the logged-in user
"""
from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.config import COOKIE_NAME, SESSION_TIMEOUT_MINUTES, COOKIE_SECURE
from app.database import get_db
from app.dependencies import get_current_user
from app.models import User
from app.schemas.auth import LoginRequest, LoginResponse
from app.schemas.user import UserOut
from app.services.security import create_access_token, verify_password
from app.services.session_store import SessionStore, get_session_store
from app.dependencies import require_dispatcher

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/login", response_model=LoginResponse)
def login(data: LoginRequest, response: Response, db: Session = Depends(get_db)):
    """Check username + password. On success return a token and set a session cookie."""
    user = db.query(User).filter(User.username == data.username).first()

    # We give the SAME message for "no such user" and "wrong password" so an attacker cannot find out which usernames exist.
    if user is None or not verify_password(data.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                            detail="Incorrect username or password.")
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                            detail="This account has been deactivated. Contact an Administrator.")

    token = create_access_token(user.user_id)
    response.set_cookie(key=COOKIE_NAME, value=token, max_age=SESSION_TIMEOUT_MINUTES * 60,
                        httponly=True, samesite="lax",secure=COOKIE_SECURE, path="/")
    return LoginResponse(access_token=token, user=user)


@router.post("/logout")
def logout(response: Response, user: User = Depends(get_current_user),
           store: SessionStore = Depends(get_session_store)):
    store.clear(user.user_id)          
    response.delete_cookie(COOKIE_NAME, path="/", httponly=True, samesite="lax")
    return {"message": "You have been logged out."}


@router.get("/me", response_model=UserOut)
def who_am_i(current_user: User = Depends(get_current_user)):
    """Return the logged-in user (the browser uses this to show the name and role)."""
    return current_user
