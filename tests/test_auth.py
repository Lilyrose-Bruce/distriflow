"""Tests for /health, /auth/login, /auth/logout, /auth/me and password hashing."""
from app.models import User
from app.services.security import create_access_token, hash_password, verify_password


def test_health_check(client):
    assert client.get("/health").json() == {"status": "ok"}


def test_password_is_hashed_not_plain():
    hashed = hash_password("Secret@123")
    assert hashed != "Secret@123"
    assert verify_password("Secret@123", hashed)
    assert not verify_password("wrong", hashed)


def test_stored_password_is_hashed(db_session, sample_users):
    admin = db_session.query(User).filter(User.username == "admin").first()
    assert admin.password_hash != "Admin@1234"
    assert admin.password_hash.startswith("$2")  # bcrypt hashes start with $2


def test_login_success(client, sample_users):
    response = client.post("/auth/login", json={"username": "admin", "password": "Admin@1234"})
    assert response.status_code == 200
    body = response.json()
    assert body["access_token"]
    assert body["user"]["role"] == "Administrator"
    assert "password_hash" not in body["user"]


def test_login_wrong_password(client, sample_users):
    response = client.post("/auth/login", json={"username": "admin", "password": "nope"})
    assert response.status_code == 401


def test_login_unknown_user(client, sample_users):
    response = client.post("/auth/login", json={"username": "ghost", "password": "whatever1"})
    assert response.status_code == 401


def test_login_deactivated_user_refused(client, db_session, sample_users):
    user = db_session.query(User).filter(User.username == "dispatcher").first()
    user.is_active = False
    db_session.commit()
    response = client.post("/auth/login", json={"username": "dispatcher", "password": "Dispatch@1234"})
    assert response.status_code == 403


def test_me_with_token(client, admin_headers):
    response = client.get("/auth/me", headers=admin_headers)
    assert response.status_code == 200
    assert response.json()["username"] == "admin"


def test_me_without_login_is_401(client, sample_users):
    assert client.get("/auth/me").status_code == 401


def test_me_with_garbage_token_is_401(client, sample_users):
    response = client.get("/auth/me", headers={"Authorization": "Bearer not-a-real-token"})
    assert response.status_code == 401


def test_expired_token_is_401(client, sample_users, db_session):
    """Simulates the inactivity timeout: a token that expired a minute ago."""
    admin = db_session.query(User).filter(User.username == "admin").first()
    old_token = create_access_token(admin.user_id, minutes=-1)
    response = client.get("/auth/me", headers={"Authorization": "Bearer " + old_token})
    assert response.status_code == 401


def test_cookie_session_and_logout(client, sample_users):
    """The browser uses the cookie: login sets it, logout removes it."""
    login = client.post("/auth/login", json={"username": "admin", "password": "Admin@1234"})
    print("LOGIN STATUS:", login.status_code)
    print("COOKIES AFTER LOGIN:", client.cookies)
    print("SET-COOKIE HEADER:", login.headers.get("set-cookie"))
    assert client.get("/auth/me").status_code == 200  # cookie sent automatically

    logout_response = client.post("/auth/logout")
    assert logout_response.status_code == 200
    assert client.get("/auth/me").status_code == 401  # cookie is gone


def test_deactivated_user_loses_access(client, db_session, dispatcher_headers):
    user = db_session.query(User).filter(User.username == "dispatcher").first()
    user.is_active = False
    db_session.commit()
    assert client.get("/auth/me", headers=dispatcher_headers).status_code == 401


def test_every_data_endpoint_requires_login(client, sample_users, sample_records):
    """Non-functional requirement: every request is authenticated."""
    assert client.get("/users").status_code == 401
    assert client.get("/trucks").status_code == 401
    assert client.get("/customers").status_code == 401
