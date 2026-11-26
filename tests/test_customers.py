"""Tests for /customers. Read = any logged-in user. Write = Administrator only."""
from app.models import DeliveryPlan, PlanStop

NEW_CUSTOMER = {"customer_name": "Duka Moja", "phone": "0722000000", "town": "Thika",
                "latitude": -1.03, "longitude": 37.07,
                "open_time": "08:00:00", "close_time": "17:00:00"}


def test_admin_creates_customer(client, admin_headers):
    response = client.post("/customers", json=NEW_CUSTOMER, headers=admin_headers)
    assert response.status_code == 201
    assert response.json()["customer_name"] == "Duka Moja"
    assert response.json()["open_time"] == "08:00:00"


def test_close_time_before_open_time_rejected(client, admin_headers):
    bad = dict(NEW_CUSTOMER, open_time="17:00:00", close_time="08:00:00")
    assert client.post("/customers", json=bad, headers=admin_headers).status_code == 422


def test_invalid_coordinates_rejected(client, admin_headers):
    bad = dict(NEW_CUSTOMER, latitude=123.0)
    assert client.post("/customers", json=bad, headers=admin_headers).status_code == 422


def test_dispatcher_can_read_customers(client, dispatcher_headers, sample_records):
    listing = client.get("/customers", headers=dispatcher_headers)
    assert listing.status_code == 200
    assert listing.json()[0]["customer_name"] == "Test Shop"
    assert client.get("/customers/1", headers=dispatcher_headers).status_code == 200


def test_get_unknown_customer_404(client, admin_headers):
    assert client.get("/customers/999", headers=admin_headers).status_code == 404


def test_update_customer(client, admin_headers, sample_records):
    changed = dict(NEW_CUSTOMER, customer_name="Renamed Shop")
    response = client.put("/customers/1", json=changed, headers=admin_headers)
    assert response.status_code == 200
    assert response.json()["customer_name"] == "Renamed Shop"


def test_update_unknown_customer_404(client, admin_headers):
    assert client.put("/customers/999", json=NEW_CUSTOMER, headers=admin_headers).status_code == 404


def test_delete_customer(client, admin_headers, sample_records):
    assert client.delete("/customers/1", headers=admin_headers).status_code == 204
    assert client.get("/customers/1", headers=admin_headers).status_code == 404


def test_delete_unknown_customer_404(client, admin_headers):
    assert client.delete("/customers/999", headers=admin_headers).status_code == 404


def test_cannot_delete_customer_used_in_a_plan(client, admin_headers, sample_records, db_session):
    plan = DeliveryPlan(truck_id=1, created_by=1, total_weight=10, total_distance=5, total_time=20)
    plan.stops.append(PlanStop(customer_id=1, stop_sequence=1))
    db_session.add(plan)
    db_session.commit()
    assert client.delete("/customers/1", headers=admin_headers).status_code == 409


def test_dispatcher_cannot_change_customers(client, dispatcher_headers, sample_records):
    assert client.post("/customers", json=NEW_CUSTOMER, headers=dispatcher_headers).status_code == 403
    assert client.put("/customers/1", json=NEW_CUSTOMER, headers=dispatcher_headers).status_code == 403
    assert client.delete("/customers/1", headers=dispatcher_headers).status_code == 403
