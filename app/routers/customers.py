"""
Customer records. Everyone logged in can read; only Administrators can change.

GET/customers          list / search customers  (any logged-in user)
GET/customers/{id}     one customer             (any logged-in user)
POST/customers         add a customer           (Administrator only)
PUT/customers/{id}     change a customer        (Administrator only)
DELETE/customers/{id}  delete a customer        (Administrator only)
"""
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import require_admin, require_dispatcher
from app.models import Customer, PlanStop
from app.schemas.customer import CustomerCreate, CustomerOut

router = APIRouter(prefix="/customers", tags=["Customers"])


def get_customer_or_404(db: Session, customer_id: int) -> Customer:
    customer = db.query(Customer).filter(Customer.customer_id == customer_id).first()
    if customer is None:
        raise HTTPException(status_code=404, detail=f"Customer {customer_id} was not found.")
    return customer


@router.get("", response_model=List[CustomerOut], dependencies=[Depends(require_dispatcher)])
def list_customers(db: Session = Depends(get_db)):
    """Used for the customer dropdown when adding a row to the staging table."""
    return db.query(Customer).order_by(Customer.customer_name).all()


@router.get("/{customer_id}", response_model=CustomerOut, dependencies=[Depends(require_dispatcher)])
def get_customer(customer_id: int, db: Session = Depends(get_db)):
    return get_customer_or_404(db, customer_id)


@router.post("", response_model=CustomerOut, status_code=status.HTTP_201_CREATED,
             dependencies=[Depends(require_admin)])
def create_customer(data: CustomerCreate, db: Session = Depends(get_db)):
    customer = Customer(**data.model_dump())
    db.add(customer)
    db.commit()
    db.refresh(customer)
    return customer


@router.put("/{customer_id}", response_model=CustomerOut, dependencies=[Depends(require_admin)])
def update_customer(customer_id: int, data: CustomerCreate, db: Session = Depends(get_db)):
    customer = get_customer_or_404(db, customer_id)
    for field_name, new_value in data.model_dump().items():
        setattr(customer, field_name, new_value)
    db.commit()
    db.refresh(customer)
    return customer


@router.delete("/{customer_id}", status_code=status.HTTP_204_NO_CONTENT,
               dependencies=[Depends(require_admin)])
def delete_customer(customer_id: int, db: Session = Depends(get_db)):
    """Really deletes the row, unless an approved plan already visits this customer."""
    customer = get_customer_or_404(db, customer_id)
    used_in_plan = db.query(PlanStop).filter(PlanStop.customer_id == customer_id).first()
    if used_in_plan is not None:
        raise HTTPException(status_code=409,
                            detail="This customer is used in a saved delivery plan and cannot be deleted.")
    db.delete(customer)
    db.commit()
