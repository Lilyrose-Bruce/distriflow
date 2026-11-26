"""Tests for /users (Administrator only)."""

NEW_USER = {"full_name": "Peter Otieno", "username": "peter", "password": "Peter@1234",
            "role": "Dispatcher"}


def test_admin_creates_user(client, admin_headers):
    response = client.post("/users", json=NEW_USER, headers=admin_headers)
    assert response.status_code == 201
    body = response.json()
    assert body["username"] == "peter"
    assert body["is_active"] is True
    assert "password" not in body and "password_hash" not in body


def test_new_user_can_log_in(client, admin_headers):
    client.post("/users", json=NEW_USER, headers=admin_headers)
    response = client.post("/auth/login", json={"username": "peter", "password": "Peter@1234"})
    assert response.status_code == 200


def test_duplicate_username_rejected(client, admin_headers):
    client.post("/users", json=NEW_USER, headers=admin_headers)
    response = client.post("/users", json=NEW_USER, headers=admin_headers)
    assert response.status_code == 409


def test_invalid_role_rejected(client, admin_headers):
    bad_user = dict(NEW_USER, role="Manager")
    assert client.post("/users", json=bad_user, headers=admin_headers).status_code == 422


def test_short_password_rejected(client, admin_headers):
    bad_user = dict(NEW_USER, password="short")
    assert client.post("/users", json=bad_user, headers=admin_headers).status_code == 422


def test_list_users(client, admin_headers):
    response = client.get("/users", headers=admin_headers)
    assert response.status_code == 200
    assert len(response.json()) == 2  # admin + dispatcher from the fixture


def test_get_user_and_404(client, admin_headers):
    assert client.get("/users/1", headers=admin_headers).status_code == 200
    assert client.get("/users/999", headers=admin_headers).status_code == 404


def test_update_user_name_and_role(client, admin_headers):
    created = client.post("/users", json=NEW_USER, headers=admin_headers).json()
    response = client.put(f"/users/{created['user_id']}", headers=admin_headers,
                          json={"full_name": "Peter O.", "role": "Administrator"})
    assert response.status_code == 200
    assert response.json()["full_name"] == "Peter O."
    assert response.json()["role"] == "Administrator"


def test_update_user_password(client, admin_headers):
    created = client.post("/users", json=NEW_USER, headers=admin_headers).json()
    client.put(f"/users/{created['user_id']}", headers=admin_headers, json={"password": "NewPass@999"})
    old = client.post("/auth/login", json={"username": "peter", "password": "Peter@1234"})
    new = client.post("/auth/login", json={"username": "peter", "password": "NewPass@999"})
    assert old.status_code == 401
    assert new.status_code == 200


def test_update_to_taken_username_rejected(client, admin_headers):
    created = client.post("/users", json=NEW_USER, headers=admin_headers).json()
    response = client.put(f"/users/{created['user_id']}", headers=admin_headers,
                          json={"username": "admin"})
    assert response.status_code == 409


def test_update_unknown_user_404(client, admin_headers):
    assert client.put("/users/999", headers=admin_headers, json={"full_name": "X"}).status_code == 404


def test_admin_cannot_demote_or_deactivate_self(client, admin_headers):
    me = client.get("/auth/me", headers=admin_headers).json()
    response = client.put(f"/users/{me['user_id']}", headers=admin_headers, json={"role": "Dispatcher"})
    assert response.status_code == 400
    response = client.delete(f"/users/{me['user_id']}", headers=admin_headers)
    assert response.status_code == 400


def test_delete_deactivates_user(client, admin_headers):
    created = client.post("/users", json=NEW_USER, headers=admin_headers).json()
    response = client.delete(f"/users/{created['user_id']}", headers=admin_headers)
    assert response.status_code == 200
    assert response.json()["is_active"] is False
    login = client.post("/auth/login", json={"username": "peter", "password": "Peter@1234"})
    assert login.status_code == 403


def test_delete_unknown_user_404(client, admin_headers):
    assert client.delete("/users/999", headers=admin_headers).status_code == 404


def test_dispatcher_cannot_use_user_endpoints(client, dispatcher_headers):
    assert client.get("/users", headers=dispatcher_headers).status_code == 403
    assert client.get("/users/1", headers=dispatcher_headers).status_code == 403
    assert client.post("/users", json=NEW_USER, headers=dispatcher_headers).status_code == 403
    assert client.put("/users/1", json={"full_name": "X"}, headers=dispatcher_headers).status_code == 403
    assert client.delete("/users/1", headers=dispatcher_headers).status_code == 403
