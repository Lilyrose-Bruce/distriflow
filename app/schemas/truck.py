"""Pydantic schemas for trucks."""
from pydantic import BaseModel, ConfigDict, Field


class TruckCreate(BaseModel):
    """Used for both creating and updating (PUT replaces all fields)."""
    license_plate: str = Field(min_length=1, max_length=20)
    max_weight_capacity: float = Field(gt=0, description="Capacity in kg")
    is_active: bool = True


class TruckOut(TruckCreate):
    model_config = ConfigDict(from_attributes=True)

    truck_id: int
