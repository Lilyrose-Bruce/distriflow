"""
Converts a in-memory DraftPlan into delivery_plans / plan_stops / plan_items rows inside one transaction.
"""

from datetime import date
from sqlalchemy.orm import Session
from app.models import DeliveryPlan, PlanStop, PlanItem
from app.services.optimizer import DraftPlan

class PlanPersistenceError(Exception):
    pass

# app/services/plan_persistence.py
from datetime import date
from sqlalchemy.orm import Session
from app.models import DeliveryPlan, PlanStop, PlanItem


class PlanPersistenceError(Exception):
    pass


def approve_draft(db: Session, draft, user_id: int, delivery_date: date) -> DeliveryPlan:
    """Copy an in-memory draft into delivery_plans / plan_stops / plan_items."""
    if not draft or not getattr(draft, "stops", None):
        raise PlanPersistenceError("Cannot approve an empty plan.")

    try:
        # 1. Create the main plan
        plan = DeliveryPlan(
            truck_id=draft.truck_id,
            created_by=user_id,
            plan_date=date.today(),
            delivery_date=delivery_date,
            status="approved",
            total_weight=draft.metrics.total_weight,
            total_distance=draft.metrics.total_distance_km,
            total_time=draft.metrics.total_travel_minutes,
        )
        db.add(plan)
        db.flush()  # Get the plan_id immediately

        # 2. Create the stops and items
        for seq, stop in enumerate(draft.stops, start=1):
            db_stop = PlanStop(
                plan_id=plan.plan_id,
                customer_id=stop.customer_id,
                stop_sequence=seq,
                arrival_time=stop.arrival_time,
            )
            db.add(db_stop)
            db.flush()  # Get the stop_id immediately

            for load_idx, item in enumerate(stop.items, start=1):
                db_item = PlanItem(
                    stop_id=db_stop.stop_id,
                    product=item.product,
                    quantity=item.quantity,
                    unit_weight=item.unit_weight,
                    total_weight=item.total_weight,
                    loading_sequence=load_idx,
                )
                db.add(db_item)

        # 3. Commit everything at once
        db.commit()
        db.refresh(plan) # Ensure all relationships are loaded
        
        return plan
        
    except Exception as e:
        db.rollback()
        raise PlanPersistenceError(f"Failed to save plan to database: {str(e)}")