"""Fill the database with dummy data.  Run with:  python seed.py
Safe to run more than once: it skips records that already exist."""

from sqlalchemy.orm import Session
from app.database import Base, SessionLocal, engine
from app.models import Customer, Truck, User
from app.services.security import hash_password

USERS = [
    ("System Administrator", "Lily", "Lily@1234", "Administrator"),
    ("Jane Wanjiru", "dispatcher", "Dispatch@1234", "Dispatcher"),
]

TRUCKS = [("KDA 123A", 3000.0), ("KCB 456B", 5000.0), ("KDG 789C", 1500.0)]

# name, phone, town, latitude, longitude, open_minutes, close_minutes
# 480 = 08:00, 1020 = 17:00, etc.
CUSTOMERS = [
    ("Naivas Westlands", "0711000001", "Nairobi", -1.2676, 36.8108, 480, 1020),
    ("Quickmart Kilimani", "0711000002", "Nairobi", -1.2921, 36.7870, 480, 1080),
    ("Carrefour Junction", "0711000003", "Nairobi", -1.2972, 36.7638, 540, 1020),
    ("Chandarana Parklands", "0711000004", "Nairobi", -1.2630, 36.8170, 510, 990),
    ("Tuskys Thika Road", "0711000005", "Nairobi", -1.2190, 36.8870, 480, 1050),
    ("Mama Mboga Kasarani", "0711000006", "Nairobi", -1.2210, 36.8980, 450, 900),
    ("Eastleigh Wholesalers", "0711000007", "Nairobi", -1.2750, 36.8450, 480, 1020),
    ("Ruiru Mini Mart", "0711000008", "Ruiru", -1.1460, 36.9610, 480, 960),
]


def seed():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        for full_name, username, password, role in USERS:
            if not db.query(User).filter(User.username == username).first():
                db.add(User(full_name=full_name, username=username,
                            password_hash=hash_password(password), role=role))
        for plate, capacity in TRUCKS:
            if not db.query(Truck).filter(Truck.license_plate == plate).first():
                db.add(Truck(license_plate=plate, max_weight_capacity=capacity))
        for name, phone, town, lat, lng, opens, closes in CUSTOMERS:
            if not db.query(Customer).filter(Customer.customer_name == name).first():
                db.add(Customer(customer_name=name, phone=phone, town=town, latitude=lat,
                                longitude=lng, open_time=opens, close_time=closes))
        db.commit()
        print("Seed complete.")
        print("  Administrator -> username: admin       password: Admin@1234")
        print("  Dispatcher    -> username: dispatcher  password: Dispatch@1234")
    finally:
        db.close()


if __name__ == "__main__":
    seed()