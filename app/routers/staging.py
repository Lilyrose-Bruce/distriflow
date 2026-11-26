"""
staging.py - the STAGING TABLE endpoints (Order upload and staging module).
Any logged-in user (Dispatcher or Administrator) can use them.

PUT    /staging/truck             select the truck
POST   /staging/upload            upload a .csv / .xlsx order file (replaces the rows)
GET    /staging                   see the staging table
POST   /staging/rows              add a row by hand
PUT    /staging/rows/{row_id}     change a row
DELETE /staging/rows/{row_id}     delete a row
DELETE /staging                   cancel: forget the truck, rows and draft

Everything is kept in the user's SESSION (server memory), not in the database.
Every answer is the full, updated staging table, so the screen can redraw itself.
"""
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app import config
from app.database import get_db
from app.dependencies import require_dispatcher
from app.models import Customer, Truck, User
from app.schemas.staging import RowCreate, RowUpdate, StagingOut, TruckSelect
from app.services.errors import FileReadError
from app.services.file_reader import read_order_file
from app.services.session_store import SessionStore, UserSession, get_session_store
from app.services.staging import CustomerLookup, OrderLine

router = APIRouter(prefix="/staging", tags=["Order upload and staging"])


def build_lookup(db: Session) -> CustomerLookup:
    """Load the customer records so rows can be checked against them."""
    return CustomerLookup(db.query(Customer).all())


def staging_response(session: UserSession) -> dict:
    """Turn the session's staging table into the answer sent to the browser."""
    staging = session.staging
    truck = None
    if staging.truck_id is not None:
        truck = {
            "truck_id": staging.truck_id,
            "license_plate": staging.truck_license_plate,
            "max_weight_capacity": staging.truck_capacity,
        }
    rows = [
        {
            "row_id": line.row_id,
            "source": line.source,
            "customer_id": line.customer_id,
            "customer_name": line.customer_name,
            "town": line.town,
            "product": line.product,
            "quantity": line.quantity,
            "unit_weight": line.unit_weight,
            "total_weight": line.total_weight,
            "status": "OK" if line.is_valid else "Error",
            "errors": line.errors,
        }
        for line in staging.rows
    ]
    return {
        "truck": truck,
        "rows": rows,
        "total_weight": staging.total_weight,
        "capacity": staging.truck_capacity,
        "space_left": staging.space_left,
        "percent_used": staging.percent_used,
        "within_capacity": staging.is_within_capacity,
        "error_count": staging.error_count,
        "can_generate": staging.can_generate,
        "messages": staging.messages(),
    }


@router.put("/truck", response_model=StagingOut)
def select_truck(
    data: TruckSelect,
    db: Session = Depends(get_db),
    user: User = Depends(require_dispatcher),
    store: SessionStore = Depends(get_session_store),
):
    """Select the truck for this plan. Its capacity is loaded from the database."""
    truck = db.query(Truck).filter(Truck.truck_id == data.truck_id, Truck.is_active == True).first()  # noqa: E712
    if truck is None:
        raise HTTPException(status_code=404, detail=f"Truck {data.truck_id} was not found or is not active.")
    session = store.get(user.user_id)
    session.staging.set_truck(truck)
    session.draft = None                      # an old draft no longer matches
    return staging_response(session)


@router.post("/upload", response_model=StagingOut)
def upload_order_file(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: User = Depends(require_dispatcher),
    store: SessionStore = Depends(get_session_store),
):
    """Upload a .csv or .xlsx order file. The rows are checked and put in the staging table."""
    session = store.get(user.user_id)
    if session.staging.truck_id is None:
        raise HTTPException(status_code=400, detail="Select a truck before uploading an order file.")

    max_bytes = config.MAX_UPLOAD_MB * 1024 * 1024
    content = file.file.read(max_bytes + 1)               # read one byte too many to detect "too big"
    if len(content) > max_bytes:
        raise HTTPException(status_code=413, detail=f"The file is larger than {config.MAX_UPLOAD_MB} MB.")

    try:
        raw_rows = read_order_file(file.filename, content)
    except FileReadError as error:
        raise HTTPException(status_code=400, detail=str(error))

    lines = [
        OrderLine(
            row_id=raw.row_number,
            source="file",
            customer_name=raw.customer_name,
            product=raw.product,
            raw_quantity=raw.quantity,
            raw_unit_weight=raw.unit_weight,
            raw_total_weight=raw.total_weight,
        )
        for raw in raw_rows
    ]
    session.staging.replace_rows(lines, build_lookup(db))   # also checks every row
    session.draft = None
    return staging_response(session)


@router.get("/read", response_model=StagingOut)
def read_staging(
    user: User = Depends(require_dispatcher),
    store: SessionStore = Depends(get_session_store),
):
    return staging_response(store.get(user.user_id))


@router.post("/rows", response_model=StagingOut, status_code=201)
def add_row(
    data: RowCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_dispatcher),
    store: SessionStore = Depends(get_session_store),
):
    """Add one row by hand (customer chosen from the dropdown)."""
    session = store.get(user.user_id)
    session.staging.add_row(
        customer_name = data.customer_name, 
        product=data.product, 
        quantity=data.quantity, 
        unit_weight=data.unit_weight, 
        lookup=build_lookup(db)
        )
    session.draft = None
    return staging_response(session)

@router.put("/rows/{row_id}", response_model=StagingOut)
def edit_row(
    row_id: int,
    data: RowUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(require_dispatcher),
    store: SessionStore = Depends(get_session_store),
):
    """Change a row. The row is checked again and the totals are recalculated."""
    session = store.get(user.user_id)
    
    # 1. Find the row manually to see if it actually exists
    target_row = next((r for r in session.staging.rows if r.row_id == row_id), None)
    
    if not target_row:
        # If it STILL fails, print the available IDs so we know why
        available_ids = [r.row_id for r in session.staging.rows]
        print(f"FAILED TO FIND ROW {row_id}. AVAILABLE ROWS ARE: {available_ids}")
        raise HTTPException(status_code=404, detail=f"Row {row_id} was not found in the staging table.")

    # 2. Perform the edit
    try:
        session.staging.edit_row(
            row_id, build_lookup(db),
            customer_name=data.customer_name, product=data.product,
            quantity=data.quantity, unit_weight=data.unit_weight,
        )
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Row {row_id} was not found in the staging table.")
    except TypeError as error:
        raise HTTPException(status_code=400, detail=str(error))
    
    session.draft = None
    return staging_response(session)


@router.delete("/rows/{row_id}", response_model=StagingOut)
def delete_row(
    row_id: int,
    user: User = Depends(require_dispatcher),
    store: SessionStore = Depends(get_session_store),
):
    session = store.get(user.user_id)
    if not session.staging.delete_row(row_id):
        raise HTTPException(status_code=404, detail=f"Row {row_id} was not found in the staging table.")
    session.draft = None
    return staging_response(session)


@router.delete("", response_model=StagingOut)
def cancel_staging(
    user: User = Depends(require_dispatcher),
    store: SessionStore = Depends(get_session_store),
):
    """Cancel the plan: forget the truck, the rows and any draft."""
    store.clear(user.user_id)
    return staging_response(store.get(user.user_id))
