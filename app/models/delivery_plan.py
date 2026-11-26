"""DELIVERY_PLAN table. Only APPROVED plans are ever saved here (Sprint 3)."""
from datetime import date

from sqlalchemy import Column, Date, Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class DeliveryPlan(Base):
    __tablename__ = "delivery_plans"

    plan_id = Column(Integer, primary_key=True, index=True)
    truck_id = Column(Integer, ForeignKey("trucks.truck_id"), nullable=False)
    created_by = Column(Integer, ForeignKey("users.user_id"), nullable=False)
    plan_date: Mapped[date] = mapped_column(Date, default=date.today) # When it was created
    delivery_date: Mapped[date] = mapped_column(Date, default=date.today)
    status: Mapped[str] = mapped_column(String, default="approved")
    total_weight = Column(Float, nullable=False)    # kg
    total_distance = Column(Float, nullable=False)  # km
    total_time = Column(Float, nullable=False)      # minutes
    
    

    truck = relationship("Truck", back_populates="plans")
    created_by_user = relationship("User", back_populates="plans")

    # A plan is composed of stops: deleting the plan deletes its stops.
    stops = relationship("PlanStop", back_populates="plan", cascade="all, delete-orphan")
    
