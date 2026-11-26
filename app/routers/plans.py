"""
plans.py - the Optimization module endpoints.

POST /plans/generate   make the delivery sequence + loading plan from the staging table
GET  /plans/draft      see the draft plan again

The draft is stored in the user's SESSION. Nothing is written to the database
until the plan is approved (Sprint 3).
"""
import time
from dataclasses import asdict
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from typing import List, Optional
import io, csv

from app.database import get_db
from app.dependencies import require_dispatcher
from app.models import Customer, User, DeliveryPlan
from app.schemas.plan import ApprovePlanRequest, DraftPlanOut, DeliveryPlanOut, DraftStopUpdate, ReorderRequest
from app.services.distance_service import DistanceService, get_distance_service
from app.services.errors import DistanceServiceError, PlanningError
from app.services.optimizer import Optimizer
from app.services.plan_persistence import approve_draft, PlanPersistenceError
from app.services.session_store import SessionStore, get_session_store

router = APIRouter(prefix="/plans", tags=["Optimization"])


@router.post("/generate", response_model=DraftPlanOut)
def generate_plan(
    db: Session = Depends(get_db),
    user: User = Depends(require_dispatcher),
    store: SessionStore = Depends(get_session_store),
    distance_service: DistanceService = Depends(get_distance_service),
):
    """Generate the delivery sequence and the loading plan (in reverse order)."""
    session = store.get(user.user_id)
    staging = session.staging

    # 1. is the staging table ready? (truck selected, rows valid, weight within capacity)
    try:
        staging.check_ready_to_generate()
    except PlanningError as error:
        raise HTTPException(status_code=400, detail=str(error))

    # 2. read the customers' locations and opening hours from the database
    customer_ids = {line.customer_id for line in staging.valid_rows}
    customers = db.query(Customer).filter(Customer.customer_id.in_(customer_ids)).all()
    customers_by_id = {customer.customer_id: customer for customer in customers}

    # 3. optimize
    started = time.perf_counter()
    try:
        draft = Optimizer(distance_service).generate(staging, customers_by_id)
    except DistanceServiceError as error:
        raise HTTPException(status_code=502, detail=f"The road distance service (OSRM) failed: {error}")
    except PlanningError as error:
        raise HTTPException(status_code=400, detail=str(error))
    draft.generation_seconds = round(time.perf_counter() - started, 2)

    # 4. keep the draft in the session and send it to the browser
    session.draft = draft
    return asdict(draft)


@router.get("/draft", response_model=DraftPlanOut)
def read_draft(
    user: User = Depends(require_dispatcher),
    store: SessionStore = Depends(get_session_store),
):
    session = store.get(user.user_id)
    if session.draft is None:
        raise HTTPException(status_code=404, detail="There is no draft plan yet. Generate a plan first.")
    return asdict(session.draft)


@router.patch("/draft/stops/{stop_id}", response_model=DraftStopUpdate)
def update_draft_stop(
    stop_id: int,
    update_data: DraftStopUpdate,
    user: User = Depends(require_dispatcher),
    store: SessionStore = Depends(get_session_store),
):
     """Manually adjust a draft stop's position before approval."""
     session = store.get(user.user_id)
     if not session or not session.draft:
         raise HTTPException(404, "No draft plan in session.")
     draft = session.draft
     ids = [s.stop_id for s in draft.stops]
     if stop_id not in ids:
         raise HTTPException(404, f"Stop {stop_id} not in draft.")
     if not (1 <= update_data.new_sequence <= len(draft.stops)):
         raise HTTPException(400, "new_sequence out of range.")
     # move and recompute loading sequence
     draft.reorder_stop(stop_id, update_data.new_sequence)
     session.touch()
     return draft.to_dict()


@router.post("/draft/reorder")
def reorder_draft(
    payload: ReorderRequest,
    user: User = Depends(require_dispatcher),
    store: SessionStore = Depends(get_session_store),
):
    session = store.get(user.user_id)
    if not session or not session.draft:
        raise HTTPException(404, "No draft plan found in session.")
    
    # Ensure the new order has the exact same number of stops
    if len(payload.stop_ids) != len(session.draft.stops):
        raise HTTPException(400, "The new route must contain exactly the same number of stops.")

    try:
        # Call the service method we created earlier to reorder and recalculate
        session.reorder_stop_sequence(payload.stop_ids)
        session.touch()
        return asdict(session.draft)
    except Exception as e:
        raise HTTPException(400, str(e))

    

@router.post("/approve", response_model=DeliveryPlanOut, status_code=201)
def approve_plan(
    payload: ApprovePlanRequest,
    db: Session = Depends(get_db),
    user: User = Depends(require_dispatcher),
    store: SessionStore = Depends(get_session_store),
):
    """Approve the draft plan and persist it in the database."""
    session = store.get(user.user_id)
    if not session or not session.draft:
        raise HTTPException(404, "No draft plan in session.")
    
    draft = session.draft
    
    # Pass the date into the persistence logic
    try:
        plan = approve_draft(db, draft, user.user_id, payload.delivery_date)
    except PlanPersistenceError as error:
        raise HTTPException(status_code=400, detail=str(error))
        
    session.draft = None
    session.touch()
    return plan


@router.get("/list", response_model=List[DeliveryPlanOut])
def list_saved_plans(
    db: Session = Depends(get_db),
    user: User = Depends(require_dispatcher),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
):
    """List previously approved plans from the database."""
    plans = db.query(DeliveryPlan).order_by(DeliveryPlan.plan_id.desc()).offset(offset).limit(limit).all()
    return plans 


@router.get("/{plan_id}", response_model=DeliveryPlanOut)
def get_saved_plan(
    plan_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_dispatcher),
):
    """Read a previously approved plan from the database."""
    plan = db.query(DeliveryPlan).filter(DeliveryPlan.plan_id == plan_id).first()
    if not plan:
        raise HTTPException(404, f"Plan {plan_id} not found.")
    return plan


from app.schemas.plan import StatusUpdate

@router.patch("/{plan_id}/status", response_model=DeliveryPlanOut)
def update_plan_status(
    plan_id: int,
    payload: StatusUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(require_dispatcher),
):
    """Update the status of a plan (e.g., from 'approved' to 'delivered')."""
    plan = db.query(DeliveryPlan).filter(DeliveryPlan.plan_id == plan_id).first()
    if not plan:
        raise HTTPException(404, "Plan not found.")
    
    if payload.status not in ["approved", "in_progress", "delivered"]:
        raise HTTPException(400, "Invalid status. Use 'approved', 'in_progress', or 'delivered'.")
        
    plan.status = payload.status
    db.commit()
    db.refresh(plan)
    return plan