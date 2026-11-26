"""staging.py - the data going in and out of the /staging endpoints."""
from typing import List, Optional

from pydantic import BaseModel


class TruckSelect(BaseModel):
    truck_id: int


class RowCreate(BaseModel):
    """A row added by hand. The customer is chosen from the dropdown, so we get its id.

    Quantity and weight are NOT limited here on purpose: a bad value (for example -5)
    creates a row that is flagged with an error, the same as for rows from a file.
    """
    customer_name: str
    product: str
    quantity: float
    unit_weight: float


class RowUpdate(BaseModel):
    """Send only what you want to change."""
    customer_name: Optional[str] = None
    product: Optional[str] = None
    quantity: Optional[float] = None
    unit_weight: Optional[float] = None


class StagingTruckOut(BaseModel):
    truck_id: int
    license_plate: str
    max_weight_capacity: float


class StagingRowOut(BaseModel):
    row_id: int                       # matches the row number in the uploaded file
    source: str                       # "file" or "manual"
    customer_id: Optional[int]
    customer_name: str
    town: str
    product: str
    quantity: Optional[int]
    unit_weight: Optional[float]
    total_weight: Optional[float]
    status: str                       # "OK" or "Error"
    errors: List[str]


class StagingOut(BaseModel):
    truck: Optional[StagingTruckOut]
    rows: List[StagingRowOut]
    total_weight: float               # valid rows only
    capacity: float
    space_left: float
    percent_used: float               # for the progress bar
    within_capacity: bool
    error_count: int
    can_generate: bool
    messages: List[str]               # every problem, ready to show to the user
