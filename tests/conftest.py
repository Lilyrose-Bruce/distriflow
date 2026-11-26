"""Shared test setup. Every test gets a brand-new, empty in-memory database."""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app
from app.models import Customer, Truck, User
from app.services.security import hash_password
from datetime import time


@pytest.fixture()
def db_session():
    """A fresh in-memory SQLite database for ONE test."""
    # StaticPool = every connection shares the same in-memory database.
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False},
                           poolclass=StaticPool)
    Base.metadata.create_all(bind=engine)
    session = sessionmaker(bind=engine, autoflush=False)()
    yield session
    session.close()


@pytest.fixture()
def client(db_session):
    """A test browser whose requests use the test database instead of the real one."""
    def use_test_db():
        yield db_session

    app.dependency_overrides[get_db] = use_test_db
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture()
def sample_users(db_session):
    """One Administrator and one Dispatcher."""
    db_session.add(User(full_name="Test Admin", username="admin",
                        password_hash=hash_password("Admin@1234"), role="Administrator"))
    db_session.add(User(full_name="Test Dispatcher", username="dispatcher",
                        password_hash=hash_password("Dispatch@1234"), role="Dispatcher"))
    db_session.commit()


@pytest.fixture()
def sample_records(db_session):
    """One truck and one customer to read/update/delete."""
    db_session.add(Truck(license_plate="KAA 111A", max_weight_capacity=3000))
    db_session.add(Customer(customer_name="Test Shop", phone="0700000000", town="Nairobi",
                            latitude=-1.28, longitude=36.82,
                            open_time=time(8, 0), close_time=time(17, 0)))
    db_session.commit()


def login_headers(client, username, password):
    """Log in and return the Authorization header to use on later requests."""
    response = client.post("/auth/login", json={"username": username, "password": password})
    assert response.status_code == 200, response.text
    return {"Authorization": "Bearer " + response.json()["access_token"]}


@pytest.fixture()
def admin_headers(client, sample_users):
    return login_headers(client, "admin", "Admin@1234")


@pytest.fixture()
def dispatcher_headers(client, sample_users):
    return login_headers(client, "dispatcher", "Dispatch@1234")
