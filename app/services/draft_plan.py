"""
draft_plan.py - the shapes of data the Optimizer produces.

A DRAFT plan lives in the user's session. Only an APPROVED plan (Sprint 3) is copied
into the database tables DELIVERY_PLAN / PLAN_STOP / PLAN_ITEM.
"""
from dataclasses import dataclass, field
from typing import List


def minutes_to_hhmm(minutes: float) -> str:
    """450 -> '07:30'. Past midnight wraps around (1500 -> '01:00')."""
    total = int(round(minutes)) % 1440
    return f"{total // 60:02d}:{total % 60:02d}"


@dataclass
class DraftItem:
    product: str
    quantity: int
    unit_weight: float
    total_weight: float
    loading_sequence: int = 0        # 1 = loaded first (deepest in the truck)


@dataclass
class DraftStop:
    stop_id: int
    stop_sequence: int               # 1 = first customer visited
    customer_id: int
    customer_name: str
    town: str
    latitude: float     
    longitude: float 
    items: List[DraftItem]
    stop_weight: float
    leg_distance_km: float = 0.0     # driving from the previous stop (or the depot)
    leg_travel_minutes: float = 0.0
    arrival_minute: int = 0          # minutes after midnight
    arrival_time: str = ""           # same, as HH:MM
    window_open: int = 0
    window_close: int = 0
    window_ok: bool = True           # False if service would start after the customer closes


@dataclass
class LoadingEntry:
    loading_sequence: int            # 1 = load this first
    stop_sequence: int               # which delivery stop it belongs to
    customer_name: str
    product: str
    quantity: int
    total_weight: float


@dataclass
class PlanMetrics:
    total_distance_km: float         # whole round trip: depot -> stops -> depot
    total_travel_minutes: float      # driving time only (no offloading time)
    total_weight: float
    stops_count: int
    time_windows_respected: bool


@dataclass
class DraftPlan:
    truck_id: int
    truck_license_plate: str
    truck_capacity: float
    depot_name: str
    depot_latitude: float      
    depot_longitude: float 
    stops: List[DraftStop]
    loading_plan: List[LoadingEntry]
    metrics: PlanMetrics
    original_metrics: PlanMetrics    # a copy of the first metrics. Sprint 3 compares against it.
    return_leg_distance_km: float = 0.0
    return_leg_travel_minutes: float = 0.0
    finish_time: str = ""            # time back at the depot (HH:MM)
    warnings: List[str] = field(default_factory=list)
    generation_seconds: float = 0.0

    # Kept for Sprint 3 (re-ordering needs them, so OSRM is not called again).
    # They are NOT sent to the browser.
    node_customer_ids: List[int] = field(default_factory=list)       # index 0 = depot
    distance_matrix_m: List[List[float]] = field(default_factory=list)
    duration_matrix_s: List[List[float]] = field(default_factory=list)
