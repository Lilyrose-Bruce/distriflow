from typing import List, Optional
from datetime import date
from pydantic import BaseModel, Field, ConfigDict

class ReorderRequest(BaseModel):
    stop_ids: List[int] 
    

class StatusUpdate(BaseModel):
    status: str
    
class DraftItemOut(BaseModel):
    product: str
    quantity: int
    unit_weight: float
    total_weight: float
    loading_sequence: int


class DraftStopOut(BaseModel):
    stop_sequence: int
    customer_id: int
    customer_name: str
    town: str
    latitude: float   
    longitude: float 
    items: List[DraftItemOut]
    stop_weight: float
    leg_distance_km: float
    leg_travel_minutes: float
    arrival_minute: int
    arrival_time: str
    window_open: int
    window_close: int
    window_ok: bool


class LoadingEntryOut(BaseModel):
    loading_sequence: int
    stop_sequence: int
    customer_name: str
    product: str
    quantity: int
    total_weight: float


class PlanMetricsOut(BaseModel):
    total_distance_km: float
    total_travel_minutes: float
    total_weight: float
    stops_count: int
    time_windows_respected: bool


class DraftPlanOut(BaseModel):
    truck_id: int
    truck_license_plate: str
    truck_capacity: float
    depot_name: str
    depot_latitude: float
    depot_longitude: float
    stops: List[DraftStopOut]
    loading_plan: List[LoadingEntryOut]
    metrics: PlanMetricsOut
    original_metrics: PlanMetricsOut
    return_leg_distance_km: float
    return_leg_travel_minutes: float
    finish_time: str
    warnings: List[str]
    generation_seconds: float
    


class DraftStopUpdate(BaseModel):
    new_sequence: int = Field(..., ge=1)


class ApprovePlanRequest(BaseModel):
    delivery_date: date 

    
# Add these new schemas at the bottom
class SavedCustomerOut(BaseModel):
    customer_id: int
    customer_name: str
    town: str
    model_config = ConfigDict(from_attributes=True)

class SavedItemOut(BaseModel):
    product: str
    quantity: int
    unit_weight: float
    total_weight: float
    loading_sequence: int
    model_config = ConfigDict(from_attributes=True)

class SavedStopOut(BaseModel):
    stop_id: int
    stop_sequence: int
    customer_id: int
    customer: SavedCustomerOut   # Nested relationship
    items: List[SavedItemOut]    # Nested relationship
    model_config = ConfigDict(from_attributes=True)

class SavedTruckOut(BaseModel):
    truck_id: int
    license_plate: str
    model_config = ConfigDict(from_attributes=True)


class DeliveryPlanOut(BaseModel):
    plan_id: int
    plan_date: date
    delivery_date: date 
    truck_id: int
    created_by: int
    status: str
    total_weight: float
    total_distance: float
    total_time: float
    stops: List[SavedStopOut]
    truck: Optional[SavedTruckOut] = None 

    model_config = ConfigDict(from_attributes=True)


