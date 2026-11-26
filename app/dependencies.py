"""Reusable checks that endpoints plug in with Depends(...).

- get_current_user      : "you must be logged in"
- require_dispatcher    : any logged-in user (Dispatcher OR Administrator)
- require_admin         : Administrator only
"""
from typing import Optional

from fastapi import Depends, HTTPException, Request, Response, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app import config
from app.database import get_db
from app.models import User
from app.services.security import create_access_token, read_token_user_id
from app.services.session_store import SessionStore, get_session_store

# auto_error=False so that we can also accept the browser cookie.
bearer_scheme = HTTPBearer(auto_error=False)

def set_login_cookie(response: Response, user_id: int) -> None:
    """Put a fresh login token in the browser's cookie.

    httponly=True -> JavaScript on the page cannot read the cookie (safer).
    samesite="lax" -> the browser does not send it on most cross-site requests.
    """
    response.set_cookie(
        key=config.COOKIE_NAME,
        value=create_access_token(user_id),
        httponly=True,
        samesite="lax",
        secure=config.COOKIE_SECURE,
        max_age=config.INACTIVITY_TIMEOUT_MINUTES * 60,
        path="/", 
    )


def _find_token(request: Request, credentials: Optional[HTTPAuthorizationCredentials]) -> Optional[str]:
    """Look for the token in the Authorization header first, then in the cookie."""
    if credentials is not None:
        return credentials.credentials
    return request.cookies.get(config.COOKIE_NAME)


def get_current_user(
    request: Request,
    response: Response,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
    db: Session = Depends(get_db),
    store: SessionStore = Depends(get_session_store),
) -> User:
    """Return the logged-in user, or reply 401 if there is no valid session."""
    not_logged_in = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="You are not logged in or your session has expired. Please log in again.",
    )

    token = _find_token(request, credentials)
    if token is None:
        raise not_logged_in

    user_id = read_token_user_id(token)
    if user_id is None:
        raise not_logged_in

    user = db.get(User, user_id)
    if user is None or not user.is_active:
        raise not_logged_in

    return user


def require_dispatcher(current_user: User = Depends(get_current_user)) -> User:
    """Any logged-in user. Administrators can do everything a Dispatcher can."""
    return current_user


def require_admin(current_user: User = Depends(get_current_user)) -> User:
    """Administrator only; Dispatchers get 403 Forbidden."""
    if current_user.role != config.ROLE_ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only an Administrator can do this.",
        )
    return current_user
