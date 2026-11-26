"""PLAN_ITEM table: one product line inside a stop."""
from sqlalchemy import Column, Float, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from app.database import Base


class PlanItem(Base):
    __tablename__ = "plan_items"

    item_id = Column(Integer, primary_key=True, index=True)
    stop_id = Column(Integer, ForeignKey("plan_stops.stop_id"), nullable=False)
    product = Column(String(100), nullable=False)
    quantity = Column(Integer, nullable=False)
    unit_weight = Column(Float, nullable=False)   # kg per unit
    total_weight = Column(Float, nullable=False)  # quantity * unit_weight
    loading_sequence = Column(Integer, nullable=False)  # 1 = loaded first (deepest in truck)

    stop = relationship("PlanStop", back_populates="items")
