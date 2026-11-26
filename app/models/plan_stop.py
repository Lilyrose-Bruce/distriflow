"""PLAN_STOP table: one customer visit inside a plan."""
from sqlalchemy import Column, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from app.database import Base


class PlanStop(Base):
    __tablename__ = "plan_stops"

    stop_id = Column(Integer, primary_key=True, index=True)
    plan_id = Column(Integer, ForeignKey("delivery_plans.plan_id"), nullable=False)
    customer_id = Column(Integer, ForeignKey("customers.customer_id"), nullable=False)
    stop_sequence = Column(Integer, nullable=False)  # 1 = first delivery
    arrival_time = Column(String, nullable=True)

    plan = relationship("DeliveryPlan", back_populates="stops")
    customer = relationship("Customer", back_populates="stops")
    items = relationship("PlanItem", back_populates="stop", cascade="all, delete-orphan")
