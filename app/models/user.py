"""USER table."""
from sqlalchemy import Boolean, Column, Integer, String
from sqlalchemy.orm import relationship

from app.database import Base


class User(Base):
    __tablename__ = "users"  # "user" is a reserved word in PostgreSQL, so we use "users"

    user_id = Column(Integer, primary_key=True, index=True)
    full_name = Column(String(100), nullable=False)
    username = Column(String(50), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)  # never the plain password
    role = Column(String(20), nullable=False)  # "Administrator" or "Dispatcher"
    is_active = Column(Boolean, default=True, nullable=False)

    plans = relationship("DeliveryPlan", back_populates="created_by_user")
