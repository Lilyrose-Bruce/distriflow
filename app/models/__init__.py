"""Importing every model here makes sure SQLAlchemy knows about all 6 tables."""
from app.models.customer import Customer
from app.models.delivery_plan import DeliveryPlan
from app.models.plan_item import PlanItem
from app.models.plan_stop import PlanStop
from app.models.truck import Truck
from app.models.user import User

__all__ = ["Customer", "DeliveryPlan", "PlanItem", "PlanStop", "Truck", "User"]
