from pydantic import BaseModel
from typing import List

class FleetUsage(BaseModel):
    license_plate: str
    usage_count: int

class RecentPlan(BaseModel):
    plan_id: int
    date: str
    truck: str
    stops: int
    status: str

class DashboardStatsOut(BaseModel):
    active_today: int
    total_plans: int
    plans_today: int
    active_trucks: int
    total_customers: int
    recent_plans: list[dict]
    status_breakdown: dict
    activity_labels: list[str]
    activity_data: list[int]