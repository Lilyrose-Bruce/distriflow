"""Tests for /trucks. Read = any logged-in user. Write = Administrator only."""

NEW_TRUCK = {"license_plate": "KBB 222B", "max_weight_capacity": 4000}


def test_admin_creates_truck(client, admin_headers):
    response = client.post("/trucks", json=NEW_TRUCK, headers=admin_headers)
    assert response.status_code == 201
    assert response.json()["max_weight_capacity"] == 4000
    assert response.json()["is_active"] is True


def test_zero_or_negative_capacity_rejected(client, admin_headers):
    for bad_capacity in (0, -500):
        bad = dict(NEW_TRUCK, max_weight_capacity=bad_capacity)
        assert client.post("/trucks", json=bad, headers=admin_headers).status_code == 422


def test_dispatcher_can_read_trucks(client, dispatcher_headers, sample_records):
    assert client.get("/trucks", headers=dispatcher_headers).status_code == 200
    assert client.get("/trucks/1", headers=dispatcher_headers).status_code == 200


def test_active_only_filter(client, admin_headers, sample_records):
    client.post("/trucks", json=dict(NEW_TRUCK, is_active=False), headers=admin_headers)
    all_trucks = client.get("/trucks", headers=admin_headers).json()
    active_trucks = client.get("/trucks?active_only=true", headers=admin_headers).json()
    assert len(all_trucks) == 2
    assert len(active_trucks) == 1


def test_get_unknown_truck_404(client, admin_headers):
    assert client.get("/trucks/999", headers=admin_headers).status_code == 404


def test_update_truck(client, admin_headers, sample_records):
    response = client.put("/trucks/1", json={"license_plate": "KAA 111A", "max_weight_capacity": 3500,
                                             "is_active": True}, headers=admin_headers)
    assert response.status_code == 200
    assert response.json()["max_weight_capacity"] == 3500


def test_update_unknown_truck_404(client, admin_headers):
    assert client.put("/trucks/999", json=NEW_TRUCK, headers=admin_headers).status_code == 404


def test_delete_deactivates_truck(client, admin_headers, sample_records):
    response = client.delete("/trucks/1", headers=admin_headers)
    assert response.status_code == 200
    assert response.json()["is_active"] is False


def test_delete_unknown_truck_404(client, admin_headers):
    assert client.delete("/trucks/999", headers=admin_headers).status_code == 404


def test_dispatcher_cannot_change_trucks(client, dispatcher_headers, sample_records):
    assert client.post("/trucks", json=NEW_TRUCK, headers=dispatcher_headers).status_code == 403
    assert client.put("/trucks/1", json=NEW_TRUCK, headers=dispatcher_headers).status_code == 403
    assert client.delete("/trucks/1", headers=dispatcher_headers).status_code == 403
