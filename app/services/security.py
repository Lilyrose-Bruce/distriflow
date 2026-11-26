"""Password hashing and login tokens. Nothing here touches the database."""
from datetime import datetime, timedelta, timezone
from typing import Optional

import jwt
from passlib.context import CryptContext

from app.config import ALGORITHM, SECRET_KEY, SESSION_TIMEOUT_MINUTES

# bcrypt is a slow, salted hash designed for passwords.
password_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(plain_password: str) -> str:
    """Turn a plain password into a hash that is safe to store."""
    return password_context.hash(plain_password)


def verify_password(plain_password: str, password_hash: str) -> bool:
    """Check a typed password against the stored hash."""
    return password_context.verify(plain_password, password_hash)


def create_access_token(user_id: int, minutes: Optional[int] = None) -> str:
    """Make a signed token that proves who the user is and expires after `minutes`."""
    if minutes is None:
        minutes = SESSION_TIMEOUT_MINUTES
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=minutes)
    payload = {"sub": str(user_id), "exp": expires_at}
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def read_token_user_id(token: str) -> Optional[int]:
    """Return the user_id inside the token, or None if it is invalid or expired."""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return int(payload["sub"])
    except (jwt.PyJWTError, KeyError, ValueError):
        return None
