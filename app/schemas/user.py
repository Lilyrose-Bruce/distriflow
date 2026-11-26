"""Pydantic schemas for users (what the API accepts and returns)."""
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field

# Only these two roles are allowed.
RoleName = Literal["Administrator", "Dispatcher"]


class UserCreate(BaseModel):
    full_name: str = Field(min_length=1, max_length=100)
    username: str = Field(min_length=3, max_length=50)
    password: str = Field(min_length=8, max_length=72)  # bcrypt only reads 72 characters
    role: RoleName


class UserUpdate(BaseModel):
    # Every field is optional: send only what you want to change.
    full_name: Optional[str] = Field(default=None, min_length=1, max_length=100)
    username: Optional[str] = Field(default=None, min_length=3, max_length=50)
    password: Optional[str] = Field(default=None, min_length=8, max_length=72)
    role: Optional[RoleName] = None
    is_active: Optional[bool] = None


class UserOut(BaseModel):
    #What we send back.
    model_config = ConfigDict(from_attributes=True)

    user_id: int
    full_name: str
    username: str
    role: str
    is_active: bool
