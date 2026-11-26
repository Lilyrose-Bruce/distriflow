from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import date, timedelta
from app.database import get_db
from app.dependencies import require_dispatcher
from app.models import User, DeliveryPlan, Truck, Customer
from app.schemas.dashboard import DashboardStatsOut

router = APIRouter(tags=["Dashboard"])

@router.get("/dashboard/stats", response_model=DashboardStatsOut)
def get_dashboard_stats(
    days: int = Query(7, description="Number of days for the activity chart"),
    db: Session = Depends(get_db),
    user: User = Depends(require_dispatcher)
):
    today = date.today()

    # 1. KPI Counts
    active_deliveries_today = db.query(DeliveryPlan).filter(
        DeliveryPlan.delivery_date == today,
        DeliveryPlan.status.in_(["approved", "in_progress"])
    ).count()

    total_plans = db.query(DeliveryPlan).count()
    active_trucks = db.query(Truck).filter(Truck.is_active == True).count() # noqa: E712
    total_customers = db.query(Customer).count()
    plans_today = db.query(DeliveryPlan).filter(DeliveryPlan.plan_date == today).count()

    # 2. Fleet Utilization (Status Breakdown for Donut)
    approved_count = db.query(DeliveryPlan).filter(DeliveryPlan.status == "approved").count()
    in_progress_count = db.query(DeliveryPlan).filter(DeliveryPlan.status == "in_progress").count()
    delivered_count = db.query(DeliveryPlan).filter(DeliveryPlan.status == "delivered").count()

    status_breakdown = {
        "approved": approved_count,
        "in_progress": in_progress_count,
        "delivered": delivered_count
    }

    # 3. Recent Plans (Last 5)
    recent_plans = db.query(DeliveryPlan).order_by(DeliveryPlan.plan_id.desc()).limit(5).all()
    recent_list = [
        {
            "plan_id": p.plan_id,
            "date": p.plan_date.isoformat(),
            "truck": p.truck.license_plate if p.truck else "Unknown",
            "stops": len(p.stops),
            "status": p.status
        } for p in recent_plans
    ]

    # 4. Activity Chart Data (Real Data)
    # Build a list of the last X days
    start_date = today - timedelta(days=days-1)
    date_labels = []
    activity_data = []
    
    for i in range(days):
        current_date = start_date + timedelta(days=i)
        date_labels.append(current_date.strftime("%b %d")) # e.g., "Nov 20"
        
        # Count how many plans were created on this day
        count = db.query(DeliveryPlan).filter(DeliveryPlan.plan_date == current_date).count()
        activity_data.append(count)

    return {
        "active_today": active_deliveries_today,
        "total_plans": total_plans,
        "plans_today": plans_today,
        "active_trucks": active_trucks,
        "total_customers": total_customers,
        "recent_plans": recent_list,
        "status_breakdown": status_breakdown,
        "activity_labels": date_labels,
        "activity_data": activity_data
    }