"""CUSTOMER table."""
from sqlalchemy import Column, Float, Integer, String, Time
from sqlalchemy.orm import relationship

from app.database import Base



class Customer(Base):
    __tablename__ = "customers"

    customer_id = Column(Integer, primary_key=True, index=True)
    customer_name = Column(String(100), nullable=False)
    phone = Column(String(20), nullable=False)
    town = Column(String(50), nullable=False)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    open_time = Column(Integer, nullable=False)   # delivery time window starts
    close_time = Column(Integer, nullable=False)  # delivery time window ends

    stops = relationship("PlanStop", back_populates="customer")
