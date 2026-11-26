"""TRUCK table."""
from sqlalchemy import Boolean, Column, Float, Integer, String
from sqlalchemy.orm import relationship

from app.database import Base


class Truck(Base):
    __tablename__ = "trucks"

    truck_id = Column(Integer, primary_key=True, index=True)
    license_plate = Column(String(20), nullable=False)
    max_weight_capacity = Column(Float, nullable=False)  # in kg
    is_active = Column(Boolean, default=True, nullable=False)

    plans = relationship("DeliveryPlan", back_populates="truck")
