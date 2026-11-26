# DistriFlow — Route Optimization and Truck Loading Planning System

Sprint 1: Foundation (authentication, database, core records).

## Setup (Windows PowerShell: use `.venv\Scripts\activate` instead of `source ...`)
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env        # optional for development
python seed.py              # creates distriflow_dev.db with dummy data
uvicorn app.main:app --reload
```
Open http://127.0.0.1:8000/docs (interactive API page).

## Test
```bash
python -m pytest -v
```

## Demo accounts (from seed.py)
| Role | Username | Password |
|---|---|---|
| Administrator | admin | Admin@1234 |
| Dispatcher | dispatcher | Dispatch@1234 |

## Using PostgreSQL
Create a database, then set `DATABASE_URL` in `.env`. If it is not set, SQLite is used.
