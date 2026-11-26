"""Checks that all 6 tables exist and that the seed script works."""
from sqlalchemy import inspect

import seed as seed_module
from app.database import Base
from app.models import Customer, Truck, User


def test_all_six_tables_exist(db_session):
    table_names = set(inspect(db_session.get_bind()).get_table_names())
    assert table_names == {"users", "trucks", "customers", "delivery_plans",
                           "plan_stops", "plan_items"}


def test_seed_creates_data_and_is_repeatable(db_session, monkeypatch):
    # Point the seed script at the test database instead of the real one.
    monkeypatch.setattr(seed_module, "SessionLocal", lambda: db_session)
    monkeypatch.setattr(seed_module, "engine", db_session.get_bind())
    monkeypatch.setattr(db_session, "close", lambda: None)  # keep the session open for checks

    seed_module.seed()
    seed_module.seed()  # running twice must NOT create duplicates

    assert db_session.query(User).count() == 2
    assert db_session.query(Truck).count() == 3
    assert db_session.query(Customer).count() == 8
    roles = {user.role for user in db_session.query(User).all()}
    assert roles == {"Administrator", "Dispatcher"}
