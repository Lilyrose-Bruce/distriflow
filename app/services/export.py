# app/services/export.py
import io, csv
from app.models import DeliveryPlan

def build_plan_csv(plan: DeliveryPlan) -> io.BytesIO:
    buf = io.StringIO()
    w = csv.writer(buf)

    w.writerow([f"DISTRIFLOW PLAN #{plan.plan_id}"])
    w.writerow(["Date", plan.plan_date, "Truck", plan.truck.license_plate,
                "Status", plan.status])
    w.writerow(["Total weight (kg)", plan.total_weight,
                "Total distance (m)", plan.total_distance,
                "Total time (s)", plan.total_time])
    w.writerow([])

    # Section 1: delivery sequence
    w.writerow(["== DELIVERY SEQUENCE =="])
    w.writerow(["Stop #", "Customer", "Town", "Product", "Qty", "Weight (kg)"])
    for stop in sorted(plan.stops, key=lambda s: s.stop_sequence):
        for item in stop.items:
            w.writerow([stop.stop_sequence, stop.customer.customer_name,
                        stop.customer.town, item.product, item.quantity,
                        round(item.total_weight, 2)])
    w.writerow([])

    # Section 2: loading plan — reverse delivery order
    w.writerow(["== LOADING PLAN (LIFO — load last stop first) =="])
    w.writerow(["Load #", "Delivery Stop #", "Customer", "Product", "Qty",
                "Weight (kg)"])
    load_no = 1
    for stop in sorted(plan.stops, key=lambda s: -s.stop_sequence):
        for item in stop.items:
            w.writerow([load_no, stop.stop_sequence, stop.customer.customer_name,
                        item.product, item.quantity, round(item.total_weight, 2)])
            load_no += 1

    data = buf.getvalue().encode("utf-8-sig")   # BOM for Excel
    return io.BytesIO(data)