"""Truck records. Everyone logged in can read; only Administrators can change."""
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import require_admin, require_dispatcher
from app.models import Truck
from app.schemas.truck import TruckCreate, TruckOut

router = APIRouter(prefix="/trucks", tags=["Trucks"])


def get_truck_or_404(db: Session, truck_id: int) -> Truck:
    truck = db.get(Truck, truck_id)
    if truck is None:
        raise HTTPException(status_code=404, detail=f"Truck {truck_id} was not found.")
    return truck


@router.get("", response_model=List[TruckOut], dependencies=[Depends(require_dispatcher)])
def list_trucks(active_only: bool = False, db: Session = Depends(get_db)):
    """Dispatchers use ?active_only=true to fill the 'select truck' dropdown."""
    query = db.query(Truck)
    if active_only:
        query = query.filter(Truck.is_active == True)  # noqa: E712 (SQLAlchemy needs == here)
    return query.order_by(Truck.truck_id).all()


@router.get("/{truck_id}", response_model=TruckOut, dependencies=[Depends(require_dispatcher)])
def get_truck(truck_id: int, db: Session = Depends(get_db)):
    return get_truck_or_404(db, truck_id)


@router.post("", response_model=TruckOut, status_code=status.HTTP_201_CREATED,
             dependencies=[Depends(require_admin)])
def create_truck(data: TruckCreate, db: Session = Depends(get_db)):
    truck = Truck(**data.model_dump())
    db.add(truck)
    db.commit()
    db.refresh(truck)
    return truck


@router.put("/{truck_id}", response_model=TruckOut, dependencies=[Depends(require_admin)])
def update_truck(truck_id: int, data: TruckCreate, db: Session = Depends(get_db)):
    truck = get_truck_or_404(db, truck_id)
    for field_name, new_value in data.model_dump().items():
        setattr(truck, field_name, new_value)
    db.commit()
    db.refresh(truck)
    return truck


@router.delete("/{truck_id}", response_model=TruckOut, dependencies=[Depends(require_admin)])
def deactivate_truck(truck_id: int, db: Session = Depends(get_db)):
    """'Delete' = deactivate, because approved plans may refer to this truck."""
    truck = get_truck_or_404(db, truck_id)
    truck.is_active = False
    db.commit()
    db.refresh(truck)
    return truck
